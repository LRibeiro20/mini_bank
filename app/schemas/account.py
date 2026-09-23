from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccountBase(BaseModel):
    account_number: str
    currency: str
    balance: Decimal
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountCreate(AccountBase):
    user_id: UUID

class AccountResponse(AccountBase):
    id: UUID

class AccountUpdate(BaseModel):
    account_number: str
    currency: str
    balance: Decimal
    status: str
    created_at: datetime
    updated_at: datetime