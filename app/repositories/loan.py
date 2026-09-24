"""
loan_repository.py
-------------------
Raw database operations for the Loan entity.
No business logic here — that belongs in LoanService.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.loan import Loan, LoanStatus


class LoanRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, loan: Loan) -> Loan:
        self.db.add(loan)
        return loan

    def get_by_id(self, loan_id: UUID) -> Loan | None:
        return self.db.query(Loan).filter(Loan.id == loan_id).first()

    def get_by_user(self, user_id: UUID, skip: int = 0, limit: int = 50) -> list[Loan]:
        return (
            self.db.query(Loan)
            .filter(Loan.user_id == user_id)
            .order_by(Loan.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_status(
        self, status: LoanStatus | None = None, skip: int = 0, limit: int = 50
    ) -> list[Loan]:
        query = self.db.query(Loan)
        if status is not None:
            query = query.filter(Loan.status == status)
        return query.order_by(Loan.created_at.desc()).offset(skip).limit(limit).all()

    def outstanding_amount_for_user(self, user_id: UUID) -> "Decimal":
        """Sum of already-approved loans for a user, used to prevent stacking
        approved loans past what their salary could reasonably service."""
        from decimal import Decimal

        loans = (
            self.db.query(Loan)
            .filter(Loan.user_id == user_id, Loan.status == LoanStatus.APPROVED)
            .all()
        )
        return sum((loan.amount for loan in loans), Decimal("0.00"))
