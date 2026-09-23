from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=True,  # Nullable for OAuth-only users
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    # MFA support
    mfa_secret: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
    )

    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    # OAuth 2.0 support
    oauth_provider: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
    )

    oauth_id: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
