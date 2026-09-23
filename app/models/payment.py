from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    transaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=False,
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
    )
    
    merchant_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    merchant_reference: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(18, 2),
        nullable=False,
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