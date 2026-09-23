"""
transaction_repository.py
--------------------------
Raw database operations for the Transaction entity.
Only concerns itself with persistence — no validation, no balance logic.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, transaction: Transaction) -> Transaction:
        """Persist a new Transaction row. The caller is responsible for committing."""
        self.db.add(transaction)
        return transaction

    def get_by_id(self, transaction_id: UUID) -> Transaction | None:
        """Return a single Transaction by primary key, or None."""
        return self.db.query(Transaction).filter(Transaction.id == transaction_id).first()

    def get_by_account(
        self,
        account_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Transaction]:
        """
        Return a paginated list of transactions for a given account,
        ordered newest-first so the most recent activity appears at the top.
        """
        return (
            self.db.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .order_by(Transaction.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_account(self, account_id: UUID) -> int:
        """Return the total number of transactions for an account (used for pagination metadata)."""
        return (
            self.db.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .count()
        )
