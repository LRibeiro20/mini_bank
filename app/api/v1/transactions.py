"""
transactions.py (API router)
-----------------------------
Read-only endpoints for querying transaction history.

  GET /api/v1/transactions/account/{account_id}
      Paginated transaction list for a specific account.
      Only the account owner can access this.

  GET /api/v1/transactions/{transaction_id}
      Single transaction detail.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.transaction import TransactionHistoryResponse, TransactionResponse
from app.services.transaction_service import TransactionService

router = APIRouter()


def get_transaction_service(db: Session = Depends(get_db)) -> TransactionService:
    """Dependency that wires the DB session and a named logger into TransactionService."""
    logger = logging.getLogger("transaction_service")
    return TransactionService(db, logger)


@router.get(
    "/account/{account_id}",
    response_model=TransactionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List transactions for an account",
)
async def get_account_transactions(
    account_id: UUID,
    # `skip` and `limit` enable cursor-free pagination.
    # The client passes skip=20&limit=20 to get page 2, etc.
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Max records to return"),
    user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Return a paginated list of transactions for `account_id`.

    The response includes `total_count` so the client can calculate
    how many pages exist without an extra request.

    Only the account owner can access this endpoint.
    """
    return transaction_service.get_transactions_by_account(
        account_id=account_id,
        requesting_user_id=user.id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single transaction",
)
async def get_transaction(
    transaction_id: UUID,
    user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """Return the Transaction identified by `transaction_id`."""
    return transaction_service.get_transaction(transaction_id)
