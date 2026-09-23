import jwt
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core import security
from app.core.config import settings
from app.core.exceptions import InvalidRequestException, UnauthorizedException
from app.models.user import User
from app.models.oauth2 import OAuth2Client, AuthorizationCode
from app.schemas.auth import UserCreate, UserLogin, MFAVerify
import secrets
from datetime import datetime, timedelta

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(self, user_in: UserCreate) -> User:
        user = self.db.query(User).filter(User.email == user_in.email).first()
        if user:
            raise InvalidRequestException("The user with this email already exists in the system.")
            
        user = User(
            email=user_in.email,
            hashed_password=security.get_password_hash(user_in.password),
        )
        self.db.add(user)
        try:
            self.db.commit()
            self.db.refresh(user)
        except IntegrityError:
            self.db.rollback()
            raise InvalidRequestException("Database integrity error.")
        return user

    def login_user(self, user_in: UserLogin) -> dict:
        user = self.db.query(User).filter(User.email == user_in.email).first()
        if not user or not user.hashed_password:
            raise UnauthorizedException("Incorrect email or password")
            
        if not security.verify_password(user_in.password, user.hashed_password):
            raise UnauthorizedException("Incorrect email or password")
            
        if not user.is_active:
            raise UnauthorizedException("Inactive user")

        if user.mfa_enabled:
            return {
                "access_token": security.create_temporary_token(user.id),
                "refresh_token": None,
                "token_type": "bearer",
                "mfa_required": True
            }
            
        return {
            "access_token": security.create_access_token(user.id),
            "refresh_token": security.create_refresh_token(user.id),
            "token_type": "bearer",
            "mfa_required": False
        }

    def setup_mfa(self, user: User) -> dict:
        if user.mfa_enabled:
            raise InvalidRequestException("MFA is already enabled")
            
        secret = security.generate_totp_secret()
        user.mfa_secret = secret
        self.db.add(user)
        self.db.commit()
        
        uri = security.get_totp_uri(secret, user.email)
        
        return {
            "secret": secret,
            "totp_uri": uri,
            "message": "Use this secret or URI in Google Authenticator or Authy."
        }

    def verify_mfa(self, user: User, mfa_in: MFAVerify) -> dict:
        if not user.mfa_secret:
            raise InvalidRequestException("MFA is not set up for this user")
            
        if not security.verify_totp(user.mfa_secret, mfa_in.token):
            raise UnauthorizedException("Invalid MFA token")
            
        if not user.mfa_enabled:
            user.mfa_enabled = True
            self.db.add(user)
            self.db.commit()
            
        return {
            "access_token": security.create_access_token(user.id),
            "refresh_token": security.create_refresh_token(user.id),
            "token_type": "bearer",
            "mfa_required": False
        }

    def process_google_callback(self, email: str, google_id: str) -> dict:
        user = self.db.query(User).filter(User.email == email).first()
        
        if not user:
            user = User(
                email=email,
                oauth_provider="google",
                oauth_id=google_id,
                is_active=True
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        elif user.oauth_provider != "google":
            user.oauth_provider = "google"
            user.oauth_id = google_id
            self.db.add(user)
            self.db.commit()
            
        return {
            "access_token": security.create_access_token(user.id),
            "refresh_token": security.create_refresh_token(user.id),
            "token_type": "bearer",
            "mfa_required": False
        }

    def refresh_token(self, refresh_token: str) -> dict:
        try:
            payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")
            
            if user_id is None or token_type != "refresh":
                raise UnauthorizedException("Invalid refresh token")
        except jwt.InvalidTokenError:
            raise UnauthorizedException("Invalid or expired refresh token")
            
        user = self.db.query(User).filter(User.id == user_id).first()
        if user is None or not user.is_active:
            raise UnauthorizedException("User not found or inactive")
            
        return {
            "access_token": security.create_access_token(user.id),
            "refresh_token": security.create_refresh_token(user.id),
            "token_type": "bearer",
            "mfa_required": False
        }

    # --- OAuth2 PKCE Methods ---
    def validate_client(self, client_id: str, redirect_uri: str) -> OAuth2Client:
        client = self.db.query(OAuth2Client).filter(OAuth2Client.client_id == client_id).first()
        if not client or not client.is_active:
            raise InvalidRequestException("Invalid or inactive client")
            
        # Basic validation: ensure redirect_uri is in the allowed list
        allowed_uris = [uri.strip() for uri in client.redirect_uris.split(',')]
        if redirect_uri not in allowed_uris:
            raise InvalidRequestException("Invalid redirect_uri")
            
        return client

    def generate_auth_code(self, user_id: str, client_id: str, redirect_uri: str, code_challenge: str, code_challenge_method: str) -> str:
        # Validate method
        if code_challenge_method not in ("S256", "plain"):
            raise InvalidRequestException("Unsupported code_challenge_method. Use S256 or plain.")
            
        code = secrets.token_urlsafe(32)
        auth_code = AuthorizationCode(
            code=code,
            client_id=client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=datetime.utcnow() + timedelta(minutes=10) # 10 mins expiry
        )
        self.db.add(auth_code)
        self.db.commit()
        return code

    def exchange_code(self, client_id: str, code: str, redirect_uri: str, code_verifier: str) -> dict:
        auth_code = self.db.query(AuthorizationCode).filter(
            AuthorizationCode.code == code,
            AuthorizationCode.client_id == client_id,
            AuthorizationCode.redirect_uri == redirect_uri
        ).first()
        
        if not auth_code:
            raise UnauthorizedException("Invalid authorization code")
            
        if datetime.utcnow() > auth_code.expires_at:
            self.db.delete(auth_code)
            self.db.commit()
            raise UnauthorizedException("Authorization code expired")
            
        # Verify PKCE
        if not security.verify_code_challenge(code_verifier, auth_code.code_challenge, auth_code.code_challenge_method):
            raise UnauthorizedException("Invalid code_verifier")
            
        # Code is single use
        user_id = auth_code.user_id
        self.db.delete(auth_code)
        self.db.commit()
        
        # Issue tokens
        return {
            "access_token": security.create_access_token(user_id),
            "refresh_token": security.create_refresh_token(user_id),
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
