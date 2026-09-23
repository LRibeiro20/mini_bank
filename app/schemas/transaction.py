"""
transaction.py (schema)
-----------------------
Pydantic models for the Transaction API surface.
"""

from datetime import datetime
from uuid import UUID
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionBase(BaseModel):
    """Shared fields used by both the DB-read and list-response shapes."""
    account_id: UUID
    # transfer_id is None for deposits, withdrawals, and payments.
    # For transfers it links both the debit and credit rows back to the Transfer record.
    transfer_id: UUID | None = None
    type: Literal["DEPOSIT", "WITHDRAWAL", "TRANSFER", "PAYMENT"]
    amount: Decimal = Field(..., gt=0)
    currency: str
    description: str | None = None
    status: Literal["PENDING", "COMPLETED", "FAILED", "REVERSED"] = "PENDING"
    created_at: datetime
    updated_at: datetime

    # Allows constructing this schema directly from a SQLAlchemy model instance.
    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    """Used internally by services to create a transaction row. Not exposed as an API endpoint."""
    account_id: UUID
    transfer_id: UUID | None = None
    type: Literal["DEPOSIT", "WITHDRAWAL", "TRANSFER", "PAYMENT"]
    amount: Decimal = Field(..., gt=0)
    currency: str
    description: str | None = None


class TransactionResponse(TransactionBase):
    """Full transaction detail including the primary key."""
    id: UUID


class TransactionUpdate(BaseModel):
    """Partial update — only status can be changed post-creation (e.g. PENDING → COMPLETED)."""
    type: Literal["DEPOSIT", "WITHDRAWAL", "TRANSFER", "PAYMENT"] | None = None
    amount: Decimal | None = None
    currency: str | None = None
    description: str | None = None
    status: Literal["PENDING", "COMPLETED", "FAILED", "REVERSED"] | None = None


class TransactionHistoryResponse(BaseModel):
    """Paginated list of transactions returned by GET /transactions/account/{id}."""
    transactions: list[TransactionResponse]
    total_count: int
