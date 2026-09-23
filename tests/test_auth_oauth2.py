from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.models.oauth2 import OAuth2Client
from app.models.user import User
from app.core import security
import pytest
import base64
import hashlib

@pytest.fixture(scope="module")
def db():
    # Setup
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    yield db
    # Teardown
    db.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def setup_data(db: Session):
    # Create test user
    user = User(email="test@example.com", hashed_password=security.get_password_hash("Test!123"), is_active=True)
    db.add(user)
    
    # Create test OAuth2 Client
    oauth_client = OAuth2Client(
        client_id="test_client",
        client_secret="test_secret",
        client_name="Test Client",
        redirect_uris="http://localhost:3000/callback",
        is_active=True
    )
    db.add(oauth_client)
    db.commit()
    return user, oauth_client

def test_oauth2_pkce_flow(client: TestClient, setup_data):
    user, oauth_client = setup_data
    
    # 1. Generate verifier and challenge
    code_verifier = security.generate_code_verifier()
    code_challenge = security.generate_code_challenge(code_verifier, method="S256")
    
    # 2. Authorize
    authorize_response = client.post(
        "/api/v1/auth/oauth2/authorize",
        json={"email": "test@example.com", "password": "Test!123"},
        data={
            "client_id": "test_client",
            "redirect_uri": "http://localhost:3000/callback",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": "random_state_123"
        }
    )
    assert authorize_response.status_code == 200, authorize_response.text
    data = authorize_response.json()
    assert "code" in data
    assert data["state"] == "random_state_123"
    auth_code = data["code"]
    
    # 3. Token exchange
    token_response = client.post(
        "/api/v1/auth/oauth2/token",
        data={
            "client_id": "test_client",
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "http://localhost:3000/callback",
            "code_verifier": code_verifier
        }
    )
    assert token_response.status_code == 200, token_response.text
    token_data = token_response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"
