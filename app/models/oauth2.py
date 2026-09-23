from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OAuth2Client(Base):
    __tablename__ = "oauth2_clients"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    client_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    client_secret: Mapped[str] = mapped_column(
        String(255),
        nullable=True, # Nullable for public clients like SPAs
    )

    client_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    redirect_uris: Mapped[str] = mapped_column(
        String(1000), # Comma separated URIs or JSON string
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )


class AuthorizationCode(Base):
    __tablename__ = "authorization_codes"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    client_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("oauth2_clients.client_id"),
        nullable=False,
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    redirect_uri: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    code_challenge: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    code_challenge_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False, # e.g. 'S256'
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    # Relationships
    user = relationship("User")
    client = relationship("OAuth2Client", foreign_keys=[client_id], primaryjoin="OAuth2Client.client_id == AuthorizationCode.client_id")
