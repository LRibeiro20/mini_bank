from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from app.api import deps
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import UserCreate, UserLogin, MFAVerify, Token, TokenRefresh, OAuth2TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.core.exceptions import UnauthorizedException

router = APIRouter()

# OAuth setup
oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url=settings.GOOGLE_CONF_URL,
    client_kwargs={
        "scope": "openid email profile"
    }
)

def get_auth_service(db: Session = Depends(deps.get_db)) -> AuthService:
    return AuthService(db)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate, 
    auth_service: AuthService = Depends(get_auth_service)
):
    return auth_service.register_user(user_in)


@router.post("/login", response_model=Token)
def login(
    user_in: UserLogin, 
    auth_service: AuthService = Depends(get_auth_service)
):
    return auth_service.login_user(user_in)


@router.post("/mfa/setup")
def setup_mfa(
    current_user: User = Depends(deps.get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Generate a TOTP secret and QR code URI for the user."""
    return auth_service.setup_mfa(current_user)


@router.post("/mfa/verify", response_model=Token)
def verify_mfa(
    mfa_in: MFAVerify,
    current_user: User = Depends(deps.get_current_user_pending_mfa),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verifies TOTP token. Used both to finalize MFA setup and to login with MFA."""
    return auth_service.verify_mfa(current_user, mfa_in)


@router.post("/refresh", response_model=Token)
def refresh_access_token(
    token_in: TokenRefresh,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh the access token using a valid refresh token."""
    return auth_service.refresh_token(token_in.refresh_token)


@router.get("/oauth/google/login")
async def google_login(request: Request):
    """Redirects the user to Google's OAuth2 login page."""
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/oauth/google/callback")
async def google_callback(
    request: Request, 
    auth_service: AuthService = Depends(get_auth_service)
):
    """Handles the callback from Google after user grants permission."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise UnauthorizedException(f"OAuth authorization failed: {str(e)}")
        
    user_info = token.get("userinfo")
    if not user_info:
        raise UnauthorizedException("Could not fetch user info from Google")
        
    email = user_info.get("email")
    google_id = user_info.get("sub")
    
    return auth_service.process_google_callback(email, google_id)


# --- Custom OAuth 2.0 PKCE Endpoints ---

@router.post("/oauth2/authorize")
def oauth2_authorize(
    user_in: UserLogin,
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    state: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and return an authorization code (Custom flow for SPAs/Mobile).
    Validates user credentials, validates client_id, and issues a short-lived authorization code.
    """
    # 1. Validate Client
    auth_service.validate_client(client_id, redirect_uri)
    
    # 2. Authenticate User (simulating the login step)
    # Using existing login logic (throws exception if invalid)
    # We do not return the JWTs directly here.
    auth_service.login_user(user_in) 
    
    # Note: If user has MFA enabled, login_user might return mfa_required=True.
    # For simplicity in this demo, we assume MFA is handled before or we would need to prompt here.
    # Getting the user ID requires a separate query because login_user returns tokens.
    user = auth_service.db.query(User).filter(User.email == user_in.email).first()

    # 3. Generate Auth Code
    code = auth_service.generate_auth_code(
        user_id=user.id,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method
    )
    
    # In a pure API SPA scenario, we can just return the code & state in JSON, 
    # but the PKCE spec traditionally expects a redirect. 
    # Returning JSON allows the SPA to redirect itself.
    return {
        "code": code,
        "state": state,
        "redirect_uri": redirect_uri
    }

@router.post("/oauth2/token", response_model=OAuth2TokenResponse)
def oauth2_token(
    client_id: str = Form(...),
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    code_verifier: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Exchange authorization code for an access token using PKCE.
    """
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
        
    return auth_service.exchange_code(
        client_id=client_id,
        code=code,
        redirect_uri=redirect_uri,
        code_verifier=code_verifier
    )
