from uuid import UUID
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from app.api.deps import get_current_user
from app.services.account_service import AccountService
from app.models.user import User
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter()

def get_account_service(db: Session = Depends(get_db)) -> AccountService:
    logger = logging.getLogger("account_service")
    return AccountService(db, logger)

@router.post("/create-account", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service)
):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return account_service.create_account(user.id)

@router.put("/update-account/{account_id}", response_model=AccountUpdate, status_code=status.HTTP_202_ACCEPTED)
async def update_account(
    account_id: UUID,
    account_data: AccountUpdate,
    user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service)
):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return account_service.update_account(user, account_id, account_data)

@router.get("/get-account-number/{account_id}", response_model=AccountUpdate, status_code=status.HTTP_200_OK)
async def get_account_number(
    account_id: UUID,
    user: User = Depends(get_current_user),
    account_service: AccountService = Depends(get_account_service)
):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return account_service.get_account_by_number(account_id)
