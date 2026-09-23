import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1 import auth, health, accounts, transfers, transactions
from app.core.config import settings
from app.core.database import engine, Base
from app.core.exceptions import BankException

# Import all models here so SQLAlchemy metadata is registered and
# Base.metadata.create_all() creates every table.
from app.models.user import User
from app.models.account import Account
from app.models.oauth2 import OAuth2Client, AuthorizationCode
from app.models.transfer import Transfer          # must come before Transaction (FK dependency)
from app.models.transaction import Transaction
from app.models.payment import Payment

# Create tables (for development/interview purposes)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Mini Bank System API",
    description="API for the mini bank system",
    version="0.1.0"
)

# Request ID Middleware
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestIdMiddleware)

# Authlib requires session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(BankException)
async def bank_exception_handler(request: Request, exc: BankException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        },
    )

app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(transfers.router, prefix="/api/v1/transfers", tags=["transfers"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])

@app.get("/")
def root():
    return {"message": "Welcome to Mini Bank System API"}
