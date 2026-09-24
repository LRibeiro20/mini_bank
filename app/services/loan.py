"""
loan_service.py
----------------
Business logic for the loan system.

Core rule enforced here (not in the model or the API layer):
    A requested loan amount can never exceed 3x the applicant's declared
    monthly salary. See `MAX_SALARY_MULTIPLE` below.

Approval flow:
    When an admin approves a PENDING loan, this service:
      1. Marks the loan APPROVED and stamps reviewed_by / reviewed_at.
      2. Credits the borrower's account balance by the loan amount.
      3. Records a DEPOSIT transaction so the disbursement shows up in the
         account's ledger, consistent with how TransferService records
         transactions for transfers.
    All three steps happen in one DB transaction — if any step fails, the
    whole approval is rolled back so a loan is never marked APPROVED
    without the money actually landing in the account.
"""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccountNotFoundException,
    ForbiddenException,
    InvalidRequestException,
    LoanAlreadyReviewedException,
    LoanLimitExceededException,
    LoanNotFoundException,
)
from app.models.account import Account
from app.models.loan import Loan, LoanStatus
from app.models.transaction import Status as TransactionStatus
from app.models.transaction import Transaction
from app.models.transaction import Type as TransactionType
from app.repositories.loan_repository import LoanRepository
from app.schemas.loan import LoanApplicationCreate

# A loan can never exceed this multiple of the applicant's monthly salary.
MAX_SALARY_MULTIPLE = Decimal("3")


class LoanService:
    def __init__(self, db: Session, logger: logging.Logger):
        self.db = db
        self.logger = logger
        self.loan_repo = LoanRepository(db)

    # ------------------------------------------------------------------
    # Applicant-facing operations
    # ------------------------------------------------------------------

    def apply_for_loan(self, user_id: UUID, data: LoanApplicationCreate) -> Loan:
        account = self.db.query(Account).filter(Account.id == data.account_id).first()
        if not account:
            raise AccountNotFoundException("Account not found")
        if str(account.user_id) != str(user_id):
            raise ForbiddenException("You can only apply for a loan on your own account")

        max_allowed = data.monthly_salary * MAX_SALARY_MULTIPLE
        if data.amount > max_allowed:
            raise LoanLimitExceededException(
                f"Requested amount {data.amount} exceeds the maximum of "
                f"{max_allowed} (3x monthly salary of {data.monthly_salary})"
            )

        loan = Loan(
            user_id=user_id,
            account_id=data.account_id,
            amount=data.amount,
            currency=account.currency,
            monthly_salary_at_application=data.monthly_salary,
            purpose=data.purpose,
            status=LoanStatus.PENDING,
        )
        self.loan_repo.create(loan)
        self.db.commit()
        self.db.refresh(loan)
        self.logger.info(f"Loan {loan.id} applied for by user {user_id} (amount={loan.amount})")
        return loan

    def get_loan(self, loan_id: UUID) -> Loan:
        loan = self.loan_repo.get_by_id(loan_id)
        if not loan:
            raise LoanNotFoundException()
        return loan

    def get_loan_for_user(self, loan_id: UUID, user_id: UUID) -> Loan:
        loan = self.get_loan(loan_id)
        if str(loan.user_id) != str(user_id):
            raise ForbiddenException("You can only view your own loans")
        return loan

    def list_loans_for_user(self, user_id: UUID, skip: int = 0, limit: int = 50) -> list[Loan]:
        return self.loan_repo.get_by_user(user_id, skip=skip, limit=limit)

    # ------------------------------------------------------------------
    # Admin-facing operations
    # ------------------------------------------------------------------

    def list_loans(
        self, status: str | None = None, skip: int = 0, limit: int = 50
    ) -> list[Loan]:
        status_enum = None
        if status is not None:
            try:
                status_enum = LoanStatus[status.upper()]
            except KeyError:
                raise InvalidRequestException(f"Invalid status filter: {status}")
        return self.loan_repo.get_by_status(status_enum, skip=skip, limit=limit)

    def approve_loan(self, loan_id: UUID, admin_id: UUID) -> Loan:
        loan = self.get_loan(loan_id)
        if loan.status != LoanStatus.PENDING:
            raise LoanAlreadyReviewedException(
                f"Loan is already {loan.status.value}, cannot approve"
            )

        account = self.db.query(Account).filter(Account.id == loan.account_id).first()
        if not account:
            raise AccountNotFoundException("Loan's account no longer exists")

        from datetime import datetime

        loan.status = LoanStatus.APPROVED
        loan.reviewed_by = admin_id
        loan.reviewed_at = datetime.utcnow()

        account.balance = account.balance + loan.amount

        disbursement = Transaction(
            account_id=account.id,
            amount=loan.amount,
            currency=loan.currency,
            status=TransactionStatus.COMPLETED,
            type=TransactionType.DEPOSIT,
            description=f"Loan disbursement for loan {loan.id}",
            reference=str(loan.id),
        )
        self.db.add(disbursement)

        self.db.commit()
        self.db.refresh(loan)
        self.logger.info(f"Loan {loan.id} approved by admin {admin_id}, disbursed {loan.amount}")
        return loan

    def reject_loan(self, loan_id: UUID, admin_id: UUID, reason: str | None) -> Loan:
        loan = self.get_loan(loan_id)
        if loan.status != LoanStatus.PENDING:
            raise LoanAlreadyReviewedException(
                f"Loan is already {loan.status.value}, cannot reject"
            )

        from datetime import datetime

        loan.status = LoanStatus.REJECTED
        loan.reviewed_by = admin_id
        loan.reviewed_at = datetime.utcnow()
        loan.rejection_reason = reason

        self.db.commit()
        self.db.refresh(loan)
        self.logger.info(f"Loan {loan.id} rejected by admin {admin_id}")
        return loan
