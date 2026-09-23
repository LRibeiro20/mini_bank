"""
transfer.py (model)
-------------------
Represents a money movement between two accounts.

A Transfer is the *parent* record that proves a transfer was requested.
It spawns exactly two Transaction rows:
  - a debit  on `from_account` (money leaves)
  - a credit on `to_account`   (money arrives)

Both transactions carry `transfer_id` as a FK back to this row,
so you can always reconstruct the full picture from either side.

idempotency_key
    A client-supplied unique token (e.g. UUID) that prevents double-charges.
    If the same key is submitted twice, the second request returns the first
    result without re-executing the transfer. See TransferService for details.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Transfer(Base):
    __tablename__ = "transfers"

    # Enforce uniqueness of idempotency_key at the DB level as a safety net
    # even if the application layer already checks it.
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_transfer_idempotency_key"),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    from_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
    )

    to_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    # Client-generated unique token used to detect and deduplicate retried requests.
    # Stored as a plain string so any format (UUID, hash, etc.) is accepted.
    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    description: Mapped[str | None] = mapped_column(
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