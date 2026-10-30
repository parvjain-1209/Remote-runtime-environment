"""
Authentication API Endpoints.
"""

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User
from app.schemas.user import MFAEnableRequest, MFASetupResponse, Token, UserLogin, UserRegister, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    """
    Registers a new user account and returns a signed JWT access token.
    Registration always assigns role='student' and never accepts a role from the client.
    """
    # Check if username or email exists
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered."
        )

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered."
        )

    hashed_pw = hash_password(user_in.password)
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pw,
        role="student",
        is_mfa_enabled=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token_str = create_access_token(subject=user.username)
    return Token(
        access_token=token_str,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates user credentials (JSON payload) and returns a signed JWT access token.
    Enforces TOTP verification if is_mfa_enabled is True.
    """
    user = db.query(User).filter(User.username == user_in.username).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_mfa_enabled:
        if not user_in.totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA code required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(user_in.totp_code.strip(), valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code",
                headers={"WWW-Authenticate": "Bearer"},
            )

    token_str = create_access_token(subject=user.username)
    return Token(
        access_token=token_str,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 standard form-encoded authentication endpoint for Swagger UI / OAuth2 clients.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Use /auth/login with totp_code",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_str = create_access_token(subject=user.username)
    return Token(
        access_token=token_str,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/mfa/setup", response_model=MFASetupResponse)
def mfa_setup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates a new base32 secret, stores it in mfa_secret with is_mfa_enabled=False,
    and returns {"secret": ..., "otpauth_uri": ...} with issuer "RemoteRuntime".
    """
    secret = pyotp.random_base32()
    current_user.mfa_secret = secret
    current_user.is_mfa_enabled = False
    db.commit()
    db.refresh(current_user)

    totp = pyotp.TOTP(secret)
    otpauth_uri = totp.provisioning_uri(name=current_user.username, issuer_name="RemoteRuntime")
    return MFASetupResponse(secret=secret, otpauth_uri=otpauth_uri)


@router.post("/mfa/enable")
def mfa_enable(
    payload: MFAEnableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verifies TOTP code against mfa_secret with valid_window=1.
    If valid, sets is_mfa_enabled=True; otherwise returns 400 Bad Request.
    """
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA secret not configured. Run /auth/mfa/setup first.",
        )

    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(payload.code.strip(), valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA code",
        )

    current_user.is_mfa_enabled = True
    db.commit()
    db.refresh(current_user)
    return {"detail": "MFA enabled successfully", "is_mfa_enabled": True}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns authenticated user profile details.
    """
    return current_user
