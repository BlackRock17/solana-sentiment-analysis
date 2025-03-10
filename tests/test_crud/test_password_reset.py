import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.data_processing.database import get_db
from src.data_processing.crud.auth import (
    create_user, create_password_reset, get_valid_password_reset,
    mark_password_reset_used, update_user_password, get_user_by_id,
    authenticate_user
)
from src.data_processing.models.auth import User, PasswordReset
from src.security.utils import verify_password


@pytest.fixture
def db():
    """Database session fixture"""
    session = next(get_db())
    yield session
    session.close()


@pytest.fixture
def test_user(db: Session):
    """Create a test user for password reset tests"""
    # Generate a unique username to avoid conflicts
    timestamp = datetime.utcnow().timestamp()
    username = f"reset_user_{timestamp}"
    email = f"reset_{timestamp}@example.com"
    password = "originalpassword"

    # Create a new test user
    user = create_user(
        db=db,
        username=username,
        email=email,
        password=password
    )

    yield user, password

    # Clean up - delete the test user
    db.delete(user)
    db.commit()


def test_create_password_reset(db: Session, test_user):
    """Test creating a password reset request"""
    user, _ = test_user

    # Create a password reset
    reset = create_password_reset(db, user.id)

    assert reset is not None
    assert reset.user_id == user.id
    assert reset.reset_code is not None
    assert len(reset.reset_code) > 0
    assert reset.is_used == False
    assert reset.expires_at > datetime.utcnow()

    # Clean up
    db.delete(reset)
    db.commit()

    print("✓ Successfully created and verified password reset")


def test_get_valid_password_reset(db: Session, test_user):
    """Test retrieving a valid password reset"""
    user, _ = test_user

    # Create a password reset
    reset = create_password_reset(db, user.id)

    # Test retrieving it
    retrieved_reset = get_valid_password_reset(db, reset.reset_code)

    assert retrieved_reset is not None
    assert retrieved_reset.id == reset.id
    assert retrieved_reset.user_id == user.id

    # Clean up
    db.delete(reset)
    db.commit()

    print("✓ Successfully retrieved valid password reset")


def test_expired_password_reset_not_valid(db: Session, test_user):
    """Test that an expired reset code is not considered valid"""
    user, _ = test_user

    # Create an expired password reset
    expiration = datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago

    reset = PasswordReset(
        user_id=user.id,
        reset_code="expired_test_reset_code",
        expires_at=expiration
    )

    db.add(reset)
    db.commit()

    # Test that it's not considered valid
    retrieved_reset = get_valid_password_reset(db, "expired_test_reset_code")
    assert retrieved_reset is None

    # Clean up
    db.delete(reset)
    db.commit()

    print("✓ Successfully verified expired reset code is not valid")


def test_used_password_reset_not_valid(db: Session, test_user):
    """Test that a used reset code is not considered valid"""
    user, _ = test_user

    # Create a used password reset
    reset = PasswordReset(
        user_id=user.id,
        reset_code="used_test_reset_code",
        expires_at=datetime.utcnow() + timedelta(hours=24),
        is_used=True
    )

    db.add(reset)
    db.commit()

    # Test that it's not considered valid
    retrieved_reset = get_valid_password_reset(db, "used_test_reset_code")
    assert retrieved_reset is None

    # Clean up
    db.delete(reset)
    db.commit()

    print("✓ Successfully verified used reset code is not valid")


def test_mark_password_reset_used(db: Session, test_user):
    """Test marking a password reset as used"""
    user, _ = test_user

    # Create a password reset
    reset = create_password_reset(db, user.id)

    # Mark it as used
    result = mark_password_reset_used(db, reset.reset_code)

    assert result is True

    # Verify it's marked as used
    db.refresh(reset)
    assert reset.is_used == True

    # Verify it's no longer considered valid
    assert get_valid_password_reset(db, reset.reset_code) is None

    # Clean up
    db.delete(reset)
    db.commit()

    print("✓ Successfully marked password reset as used")


def test_update_user_password(db: Session, test_user):
    """Test updating a user's password"""
    user, original_password = test_user

    # Update the password
    new_password = "newpassword123"
    result = update_user_password(db, user.id, new_password)

    assert result is True

    # Verify the password was updated
    updated_user = get_user_by_id(db, user.id)
    assert verify_password(new_password, updated_user.hashed_password)
    assert not verify_password(original_password, updated_user.hashed_password)

    # Verify authentication works with new password
    authenticated_user = authenticate_user(db, user.username, new_password)
    assert authenticated_user is not None
    assert authenticated_user.id == user.id

    print("✓ Successfully updated user password")


def test_full_password_reset_flow(db: Session, test_user):
    """Test the full password reset flow"""
    user, original_password = test_user

    # 1. Create a password reset
    reset = create_password_reset(db, user.id)

    # 2. Verify the reset code is valid
    valid_reset = get_valid_password_reset(db, reset.reset_code)
    assert valid_reset is not None

    # 3. Update the password
    new_password = "completelynewpassword"
    update_result = update_user_password(db, user.id, new_password)
    assert update_result is True

    # 4. Mark the reset code as used
    mark_result = mark_password_reset_used(db, reset.reset_code)
    assert mark_result is True

    # 5. Verify the reset code is no longer valid
    assert get_valid_password_reset(db, reset.reset_code) is None

    # 6. Verify authentication works with new password
    authenticated_user = authenticate_user(db, user.username, new_password)
    assert authenticated_user is not None
    assert authenticated_user.id == user.id

    # 7. Verify old password doesn't work
    assert authenticate_user(db, user.username, original_password) is None

    # Clean up
    db.delete(reset)
    db.commit()

    print("✓ Successfully tested full password reset flow")
