"""
transaction_service.py
----------------------
Read-only service for querying transaction history.

Why separate from TransferService?
    TransferService owns writes — it creates transactions as a side effect of a transfer.
    This service owns reads — it answers "show me the ledger for account X".
    Separating them keeps each class small and focused on a single responsibility.
"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AccountNotFoundException, InvalidRequestException
from app.models.account import Account
from app.models.transaction import Transaction
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionHistoryResponse


class TransactionService:
    def __init__(self, db: Session, logger: logging.Logger):
        self.db = db
        self.logger = logger
        self.transaction_repo = TransactionRepository(db)

    def get_transactions_by_account(
        self,
        account_id: UUID,
        requesting_user_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> TransactionHistoryResponse:
        """
        Return paginated transaction history for an account.

        Ownership is enforced here — a user can only view history for their
        own account. Admins / staff would bypass this check in a real system,
        but that's out of scope for now.
        """
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise AccountNotFoundException(f"Account {account_id} not found")

        if str(account.user_id) != str(requesting_user_id):
            raise InvalidRequestException("You can only view transactions for your own account")

        transactions = self.transaction_repo.get_by_account(account_id, skip=skip, limit=limit)
        total = self.transaction_repo.count_by_account(account_id)

        return TransactionHistoryResponse(transactions=transactions, total_count=total)

    def get_transaction(self, transaction_id: UUID) -> Transaction:
        """Return a single transaction by ID, or raise if not found."""
        txn = self.transaction_repo.get_by_id(transaction_id)
        if not txn:
            raise InvalidRequestException(f"Transaction {transaction_id} not found")
        return txn
