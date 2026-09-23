"""
transfer.py (schema)
--------------------
Pydantic models that define the shape of transfer API requests and responses.
These are distinct from the SQLAlchemy model — they handle validation,
serialisation, and what we expose to the outside world.
"""

from datetime import datetime
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransferCreate(BaseModel):
    """
    Payload the client sends to POST /api/v1/transfers.

    from_account_number / to_account_number
        The human-readable account number (e.g. "15286168458595").
        The service resolves these to internal UUIDs before writing to the DB.
        This is what users actually know — they don't deal with internal UUIDs.

    idempotency_key
        A unique token the client generates per transfer attempt (e.g. a UUID).
        Re-submitting the same key returns the original result instead of
        executing the transfer again — safe to retry on network failures.
    """
    from_account_number: str = Field(..., description="Source account number, e.g. 15286168458595")
    to_account_number: str = Field(..., description="Destination account number")
    amount: Decimal = Field(..., gt=0, description="Amount to transfer — must be positive")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code, e.g. MZN")
    description: str | None = Field(None, max_length=255)
    idempotency_key: str = Field(..., min_length=1, max_length=64, description="Client-generated unique key to prevent duplicate transfers")


class TransferResponse(BaseModel):
    """
    Shape returned to the client after a successful transfer.
    Exposes enough information to reconstruct what happened
    without leaking internal DB details.
    """
    id: UUID
    from_account_id: UUID
    to_account_id: UUID
    amount: Decimal
    currency: str
    description: str | None
    idempotency_key: str
    created_at: datetime

    # orm_mode / from_attributes lets Pydantic read SQLAlchemy model instances directly.
    model_config = ConfigDict(from_attributes=True)
