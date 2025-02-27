from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from config.settings import ACCESS_TOKEN_EXPIRE_MINUTES
from src.data_processing.crud.auth import (
    create_user, authenticate_user, create_api_key,
    get_user_by_username, get_user_by_email
)
from src.data_processing.database import get_db
from src.schemas.auth import (
    UserCreate, UserResponse, Token, ApiKeyCreate, ApiKeyResponse
)
from src.security.auth import get_current_active_user, get_current_superuser
from src.security.utils import create_user_token
from src.data_processing.models.auth import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login endpoint
    """
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    token = create_user_token(db, user)

    return {
        "access_token": token.token,
        "token_type": token.token_type,
        "expires_at": token.expires_at
    }