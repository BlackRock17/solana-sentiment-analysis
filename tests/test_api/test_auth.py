import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from src.api.auth import router as auth_router
from src.data_processing.database import get_db
from src.data_processing.crud.auth import create_user, get_user_by_username

# Create a test application with only the auth router
auth_test_app = FastAPI()
auth_test_app.include_router(auth_router)

# Use the test application for client
client = TestClient(auth_test_app)


@pytest.fixture
def db():
    """Database session fixture"""
    session = next(get_db())
    yield session
    session.close()


def test_login_endpoint_valid_credentials(db: Session):
    """Test login endpoint with valid credentials"""
    # Create a test user
    timestamp = datetime.utcnow().timestamp()
    username = f"api_test_user_{timestamp}"
    password = "testpassword"

    user = create_user(
        db=db,
        username=username,
        email=f"api_test_{timestamp}@example.com",
        password=password
    )

    # Try to lo gin
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password}
    )

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_at" in data

    # Clean up
    db.delete(user)
    db.commit()

    print("✓ Successfully tested valid login")


def test_login_endpoint_invalid_credentials(db: Session):
    """Test login endpoint with invalid credentials"""
    timestamp = datetime.utcnow().timestamp()
    username = f"api_test_invalid_{timestamp}"

    # Create a test user
    user = create_user(
        db=db,
        username=username,
        email=f"api_test_invalid_{timestamp}@example.com",
        password="correctpassword"
    )

    # Try to lo gin with wrong password
    response = client.post(
        "/auth/token",
        data={"username": username, "password": "wrongpassword"}
    )

    # Check response
    assert response.status_code == 401

    # Clean up
    db.delete(user)
    db.commit()

    print("✓ Successfully tested invalid login")


def test_signup_endpoint(db: Session):
    """Test user registration endpoint"""
    timestamp = datetime.utcnow().timestamp()
    new_username = f"new_user_{timestamp}"

    user_data = {
        "username": new_username,
        "email": f"new_user_{timestamp}@example.com",
        "password": "newuserpassword"
    }

    # Try to register
    response = client.post("/auth/signup", json=user_data)

    # Check response
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == new_username
    assert "id" in data

    # Verify user was created in DB
    db_user = get_user_by_username(db, new_username)
    assert db_user is not None

    # Clean up
    db.delete(db_user)
    db.commit()

    print("✓ Successfully tested user registration")


def test_signup_endpoint_duplicate_username(db: Session):
    """Test registration with duplicate username"""
    timestamp = datetime.utcnow().timestamp()
    username = f"dup_user_{timestamp}"

    # Create a test user
    user = create_user(
        db=db,
        username=username,
        email=f"original_{timestamp}@example.com",
        password="userpassword"
    )

    # Try to register with same username
    user_data = {
        "username": username,
        "email": f"different_{timestamp}@example.com",
        "password": "userpassword"
    }

    response = client.post("/auth/signup", json=user_data)

    # Check response
    assert response.status_code == 400

    # Clean up
    db.delete(user)
    db.commit()

    print("✓ Successfully tested duplicate username registration")


def test_me_endpoint_with_auth(db: Session):
    """Test /me endpoint with valid authentication"""
    timestamp = datetime.utcnow().timestamp()
    username = f"me_test_user_{timestamp}"
    password = "testpassword"

    # Create a test user
    user = create_user(
        db=db,
        username=username,
        email=f"me_test_{timestamp}@example.com",
        password=password
    )

    # Login to get token
    login_response = client.post(
        "/auth/token",
        data={"username": username, "password": password}
    )

    token_data = login_response.json()

    # Use token to access /me endpoint
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"}
    )

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == username
    assert data["id"] == user.id

    # Clean up
    db.delete(user)
    db.commit()

    print("✓ Successfully tested /me endpoint with authentication")


def test_me_endpoint_without_auth():
    """Test /me endpoint without authentication"""
    response = client.get("/auth/me")

    # Check response - should require authentication
    assert response.status_code == 401

    print("✓ Successfully tested /me endpoint without authentication")