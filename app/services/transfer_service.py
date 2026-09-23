"""
transfer_service.py
-------------------
Orchestrates the full lifecycle of a transfer between two accounts.

Why this service exists
    A transfer is not just an INSERT — it must atomically:
      1. Validate both accounts exist and are usable.
      2. Confirm the sender has enough balance.
      3. Record the intent (Transfer row).
      4. Record two ledger entries (Transaction rows: one debit, one credit).
      5. Update both account balances.
      6. Commit everything in a single DB transaction.

    If any step fails, the DB transaction is rolled back and no money moves.

Idempotency
    The client must include a unique `idempotency_key` with every request.
    Before doing any work, the service checks whether a Transfer with that key
    already exists. If it does, the existing Transfer is returned immediately —
    the transfer is NOT executed again. This makes the endpoint safe to retry
    on network failures or timeouts without risking a double charge.

    Idempotency is enforced at two levels:
      - Application level: we query by key before proceeding (fast path).
      - Database level:    a UNIQUE constraint on `transfers.idempotency_key`
                          is the final safety net if two requests race.

Amount sign convention
    Amounts are stored as POSITIVE numbers in both the Transfer and Transaction
    tables. The *direction* is implicit:
      - The service SUBTRACTS from the sender's balance.
      - The service ADDS to the receiver's balance.
    This keeps queries simple (no need to negate amounts in SUM aggregations).
"""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccountNotFoundException,
    AccountBlockedException,
    InsufficientFundsException,
    InvalidRequestException,
    DuplicateRequestException,
    TransferNotFoundException,
)
from app.models.account import Account
from app.models.transfer import Transfer
from app.models.transaction import Transaction, Type, Status
from app.repositories.transfer_repository import TransferRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transfer import TransferCreate, TransferResponse


class TransferService:
    def __init__(self, db: Session, logger: logging.Logger):
        self.db = db
        self.logger = logger
        # Repositories are thin wrappers around the DB session;
        # they do not commit — that responsibility stays here.
        self.transfer_repo = TransferRepository(db)
        self.transaction_repo = TransactionRepository(db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_transfer(self, data: TransferCreate, user_id: UUID) -> Transfer:
        """
        Execute a transfer and return the resulting Transfer record.

        Steps
        -----
        1. Idempotency check  — short-circuit if this key was already used.
        2. Load accounts      — both must exist.
        3. Ownership check    — sender must belong to the calling user.
        4. Status check       — both accounts must be ACTIVE.
        5. Currency check     — both accounts must share the same currency.
        6. Balance check      — sender must have sufficient funds.
        7. Create Transfer row.
        8. Create debit Transaction (sender side).
        9. Create credit Transaction (receiver side).
        10. Update balances.
        11. Commit atomically.
        """
        self.logger.info(
            f"Transfer requested by user={user_id} "
            f"from={data.from_account_number} to={data.to_account_number} "
            f"amount={data.amount} key={data.idempotency_key}"
        )

        # ── Step 1: Idempotency ──────────────────────────────────────────
        # If we've seen this key before, return the existing transfer.
        # The client gets the same response whether it's the first call or a retry.
        existing = self.transfer_repo.get_by_idempotency_key(data.idempotency_key)
        if existing:
            self.logger.info(f"Idempotent replay for key={data.idempotency_key}")
            return existing

        # ── Step 2: Resolve account numbers to Account rows ────────────────────────────
        # Users know their account number, not the internal UUID.
        # We resolve here and use the UUID (account.id) for all subsequent DB writes.
        from_account = self.db.query(Account).filter(Account.account_number == data.from_account_number).first()
        if not from_account:
            raise AccountNotFoundException(f"Source account {data.from_account_number} not found")

        to_account = self.db.query(Account).filter(Account.account_number == data.to_account_number).first()
        if not to_account:
            raise AccountNotFoundException(f"Destination account {data.to_account_number} not found")

        # ── Step 3: Ownership ────────────────────────────────────────────
        # Only the account's owner can initiate a transfer from it.
        if str(from_account.user_id) != str(user_id):
            raise InvalidRequestException("You can only transfer from your own account")

        # ── Step 4: Account status ───────────────────────────────────────
        if from_account.status.upper() != "ACTIVE":
            raise AccountBlockedException("Source account is not active")
        if to_account.status.upper() != "ACTIVE":
            raise AccountBlockedException("Destination account is not active")

        # ── Step 5: Currency match ───────────────────────────────────────
        # Cross-currency transfers would require an FX rate — not in scope here.
        if from_account.currency != to_account.currency:
            raise InvalidRequestException(
                f"Currency mismatch: source is {from_account.currency}, "
                f"destination is {to_account.currency}"
            )
        if from_account.currency != data.currency:
            raise InvalidRequestException(
                f"Requested currency {data.currency} does not match account currency {from_account.currency}"
            )

        # ── Step 6: Sufficient funds ─────────────────────────────────────
        if Decimal(str(from_account.balance)) < data.amount:
            raise InsufficientFundsException(
                f"Insufficient funds: available {from_account.balance}, requested {data.amount}"
            )

        # ── Steps 7-10: DB writes (all flushed before commit) ───────────
        try:
            # 7. Create the parent Transfer record.
            transfer = Transfer(
                from_account_id=from_account.id,   # internal UUID resolved from account number
                to_account_id=to_account.id,
                amount=data.amount,
                currency=data.currency,
                description=data.description,
                idempotency_key=data.idempotency_key,
            )
            self.transfer_repo.create(transfer)
            # flush so transfer.id is generated and available for the FK below
            self.db.flush()

            # 8. Debit transaction — records money leaving the sender's account.
            debit = Transaction(
                account_id=from_account.id,
                transfer_id=transfer.id,   # links back to the parent transfer
                type=Type.TRANSFER,
                amount=data.amount,        # positive; service logic handles subtraction
                currency=data.currency,
                status=Status.COMPLETED,
                description=data.description or f"Transfer to {data.to_account_number}",
            )
            self.transaction_repo.create(debit)

            # 9. Credit transaction — records money arriving in the receiver's account.
            credit = Transaction(
                account_id=to_account.id,
                transfer_id=transfer.id,   # same transfer_id — pairs the two rows
                type=Type.TRANSFER,
                amount=data.amount,
                currency=data.currency,
                status=Status.COMPLETED,
                description=data.description or f"Transfer from {data.from_account_number}",
            )
            self.transaction_repo.create(credit)

            # 10. Update balances in memory; the DB is updated on commit.
            from_account.balance = Decimal(str(from_account.balance)) - data.amount
            to_account.balance = Decimal(str(to_account.balance)) + data.amount

            # 11. Single commit — all writes succeed or all are rolled back.
            self.db.commit()
            self.db.refresh(transfer)

            self.logger.info(
                f"Transfer {transfer.id} completed: "
                f"{data.from_account_number} → {data.to_account_number} {data.amount} {data.currency}"
            )
            return transfer

        except IntegrityError:
            # This catches a race condition where two requests with the same
            # idempotency_key slip past the application-level check simultaneously.
            # The UNIQUE constraint on the DB column prevents both from succeeding.
            self.db.rollback()
            self.logger.warning(f"Duplicate transfer attempt for key={data.idempotency_key}")
            raise DuplicateRequestException(
                "A transfer with this idempotency key already exists"
            )
        except Exception:
            self.db.rollback()
            self.logger.exception("Unexpected error during transfer")
            raise

    def get_transfer(self, transfer_id: UUID) -> Transfer:
        """Retrieve a transfer by ID. Raises TransferNotFoundException if missing."""
        transfer = self.transfer_repo.get_by_id(transfer_id)
        if not transfer:
            raise TransferNotFoundException(f"Transfer {transfer_id} not found")
        return transfer
