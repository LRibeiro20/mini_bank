"""
loans.py (API router)
----------------------
Applicant-facing endpoints (any authenticated user):

  POST /api/v1/loans/apply
      Submit a new loan application. Rejected up front (400) if the
      requested amount exceeds 3x the declared monthly salary.

  GET  /api/v1/loans/my-loans
      List the current user's own loan applications.

  GET  /api/v1/loans/{loan_id}
      Fetch a single loan application the current user owns.

Admin-only endpoints (require User.is_admin, gated by get_current_admin_user):

  GET  /api/v1/loans/admin/loans
      List loan applications, optionally filtered by status
      (PENDING / APPROVED / REJECTED). This is the admin portal's queue.

  POST /api/v1/loans/admin/loans/{loan_id}/approve
      Approve a PENDING loan: disburses funds into the borrower's account.

  POST /api/v1/loans/admin/loans/{loan_id}/reject
      Reject a PENDING loan, optionally with a reason.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user, get_current_user, get_db
from app.models.user import User
from app.schemas.loan import LoanApplicationCreate, LoanResponse, LoanReviewRequest
from app.services.loan_service import LoanService

router = APIRouter()


def get_loan_service(db: Session = Depends(get_db)) -> LoanService:
    logger = logging.getLogger("loan_service")
    return LoanService(db, logger)


# ---------------------------------------------------------------------
# Applicant-facing routes
# ---------------------------------------------------------------------

@router.post(
    "/apply",
    response_model=LoanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for a loan (amount capped at 3x monthly salary)",
)
async def apply_for_loan(
    data: LoanApplicationCreate,
    user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service),
):
    return loan_service.apply_for_loan(user.id, data)


@router.get(
    "/my-loans",
    response_model=list[LoanResponse],
    summary="List the current user's own loan applications",
)
async def list_my_loans(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service),
):
    return loan_service.list_loans_for_user(user.id, skip=skip, limit=limit)


@router.get(
    "/{loan_id}",
    response_model=LoanResponse,
    summary="Get a single loan application you own",
)
async def get_loan(
    loan_id: UUID,
    user: User = Depends(get_current_user),
    loan_service: LoanService = Depends(get_loan_service),
):
    return loan_service.get_loan_for_user(loan_id, user.id)


# ---------------------------------------------------------------------
# Admin portal routes
# ---------------------------------------------------------------------

@router.get(
    "/admin/loans",
    response_model=list[LoanResponse],
    summary="[Admin] List loan applications, optionally filtered by status",
)
async def admin_list_loans(
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_current_admin_user),
    loan_service: LoanService = Depends(get_loan_service),
):
    return loan_service.list_loans(status=status_filter, skip=skip, limit=limit)


@router.post(
    "/admin/loans/{loan_id}/approve",
    response_model=LoanResponse,
    summary="[Admin] Approve a pending loan and disburse funds",
)
async def admin_approve_loan(
    loan_id: UUID,
    admin: User = Depends(get_current_admin_user),
    loan_service: LoanService = Depends(get_loan_service),
):
    return loan_service.approve_loan(loan_id, admin.id)


@router.post(
    "/admin/loans/{loan_id}/reject",
    response_model=LoanResponse,
    summary="[Admin] Reject a pending loan",
)
async def admin_reject_loan(
    loan_id: UUID,
    data: LoanReviewRequest,
    admin: User = Depends(get_current_admin_user),
    loan_service: LoanService = Depends(get_loan_service),
):
    return loan_service.reject_loan(loan_id, admin.id, data.rejection_reason)
