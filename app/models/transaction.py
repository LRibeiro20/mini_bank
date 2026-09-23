"""
transaction.py (model)
----------------------
Records every individual money movement against a single account.

Each row answers: "what happened to account X at time T?"

For transfers, TWO transaction rows are created — one debit and one credit —
both pointing to the same `transfer_id`. This design lets you:
  - Query a single account's full ledger with no joins.
  - Reconstruct a complete transfer by filtering on `transfer_id`.

Type enum
    DEPOSIT    — money flowing into an account from an external source.
    WITHDRAWAL — money flowing out to an external destination.
    TRANSFER   — internal movement between two accounts (always paired).
    PAYMENT    — outbound payment to a merchant/biller (linked to a Payment row).

Status enum
    PENDING   — not yet settled (e.g. waiting for external confirmation).
    COMPLETED — successfully settled.
    FAILED    — attempted but did not succeed.
    REVERSED  — originally completed, then undone.

amount
    Always stored as a positive number. The direction (debit vs. credit)
    is inferred from the account's perspective — for a TRANSFER debit the
    service subtracts from the balance; for a credit it adds.
    This avoids signed-amount confusion in reporting queries.
"""

from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy import DateTime, String, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Status(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REVERSED = "REVERSED"
    FAILED = "FAILED"


class Type(Enum):
    TRANSFER = "TRANSFER"
    WITHDRAWAL = "WITHDRAWAL"
    DEPOSIT = "DEPOSIT"
    PAYMENT = "PAYMENT"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # The account this transaction is recorded against.
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
    )

    # For TRANSFER transactions: links both the debit and credit row back to
    # the single Transfer record that originated them. NULL for all other types.
    transfer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transfers.id"),
        nullable=True,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="MZN",
    )

    status: Mapped[Status] = mapped_column(
        SQLEnum(Status),
        nullable=False,
    )

    type: Mapped[Type] = mapped_column(
        SQLEnum(Type),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Free-form reference string (e.g. external payment ID, merchant ref).
    reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )