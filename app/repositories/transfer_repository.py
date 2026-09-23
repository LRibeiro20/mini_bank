"""
transfer_repository.py
----------------------
Raw database operations for the Transfer entity.
This layer only talks to the DB — no business logic lives here.
The service layer is responsible for validation, orchestration, and commits.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.transfer import Transfer


class TransferRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, transfer: Transfer) -> Transfer:
        """Persist a new Transfer row. The caller is responsible for committing."""
        self.db.add(transfer)
        return transfer

    def get_by_id(self, transfer_id: UUID) -> Transfer | None:
        """Return the Transfer with the given id, or None if not found."""
        return self.db.query(Transfer).filter(Transfer.id == transfer_id).first()

    def get_by_idempotency_key(self, idempotency_key: str) -> Transfer | None:
        """
        Look up an existing Transfer by its idempotency key.
        Used to detect and short-circuit duplicate requests before any money moves.
        """
        return (
            self.db.query(Transfer)
            .filter(Transfer.idempotency_key == idempotency_key)
            .first()
        )
