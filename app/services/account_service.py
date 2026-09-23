from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import secrets
from decimal import Decimal
from app.core import security
from app.core.config import settings
from app.core.exceptions import InvalidRequestException, UnauthorizedException, AccountNotFoundException,AccountBlockedException 
from app.models.user import User
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountUpdate


class AccountService:
    def __init__(self, db: Session, logger):
        self.db = db
        self.logger = logger
    
    def generate_account_number(self) -> str:
        while True:
            account_number = str(secrets.randbelow(90_000_000_000_000) + 10_000_000_000_000)
            exists = self.db.query(Account).filter(Account.account_number == account_number).first()
            if not exists:
                return account_number
            
    def get_account_by_number(self, account_number: str) -> Account | None:
        account = self.db.query(Account).filter(Account.account_number == account_number).first()
        if not account:
            raise AccountNotFoundException("Account not found")
        return account
    
    def create_account(self, user_id: str) -> Account:
        account = self.db.query(Account).filter(Account.user_id == user_id).first()
        account_number = self.generate_account_number()
        if account:
            raise InvalidRequestException("Account already exists")
        
        account = Account(
            user_id=user_id,
            account_number=account_number,
            currency="MZN",
            balance=Decimal("0.00"),
            status="active",
        )
        self.logger.info(f"Account created for user {user_id}")
        self.db.add(account)
        try:
            self.db.commit()
            self.db.refresh(account)
        except IntegrityError:
            self.db.rollback()
            self.logger.error(f"Account already exists")
            raise InvalidRequestException("Account already exists")
        return account
    
        