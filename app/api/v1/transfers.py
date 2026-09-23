"""
transfers.py (API router)
--------------------------
Exposes two endpoints:

  POST /api/v1/transfers
      Execute a transfer between two accounts.
      Requires a Bearer token (authenticated user).
      The request body must include an `idempotency_key` to prevent double charges.

  GET  /api/v1/transfers/{transfer_id}
      Retrieve an existing transfer by its ID.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.transfer import TransferCreate, TransferResponse
from app.services.transfer_service import TransferService

router = APIRouter()


def get_transfer_service(db: Session = Depends(get_db)) -> TransferService:
    """Dependency that wires the DB session and a named logger into TransferService."""
    logger = logging.getLogger("transfer_service")
    return TransferService(db, logger)


@router.post(
    "/",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute a transfer between two accounts",
)
async def execute_transfer(
    data: TransferCreate,
    user: User = Depends(get_current_user),
    transfer_service: TransferService = Depends(get_transfer_service),
):
    """
    Transfer `amount` from `from_account_id` to `to_account_id`.

    **Idempotency**: include a unique `idempotency_key` in the request body.
    Re-submitting the same key returns the original transfer without
    charging the account again — safe to retry on network failures.

    Returns the created Transfer record on success.
    """
    transfer = transfer_service.execute_transfer(data, user_id=user.id)
    return transfer


@router.get(
    "/{transfer_id}",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a transfer by ID",
)
async def get_transfer(
    transfer_id: UUID,
    user: User = Depends(get_current_user),
    transfer_service: TransferService = Depends(get_transfer_service),
):
    """Return the Transfer record identified by `transfer_id`."""
    return transfer_service.get_transfer(transfer_id)
