"""
FastAPI router for MEDLYTICS authentication, registration, verification and approval workflows.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from models import User, VerificationToken
from services.auth_service import (
    hash_password,
    verify_password,
    validate_email_format,
    validate_password_strength,
    create_access_token,
    decode_access_token,
    generate_verification_token,
    send_verification_email,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Schemas
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    email_verified: bool
    approval_status: str
    role: str
    is_active: bool
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class StatusMessageResponse(BaseModel):
    message: str
    status: str
    email: Optional[str] = None


# Dependencies
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate the JWT Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload.get("sub"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed session token.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
        )

    return user


def get_current_active_approved_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is verified, approved, and active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled.",
        )
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before accessing MEDLYTICS.",
        )
    if current_user.approval_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your MEDLYTICS account is pending administrator approval.",
        )
    return current_user


# Endpoints
@router.post("/register", response_model=StatusMessageResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.
    Initial state: email_verified=False, approval_status='PENDING_EMAIL_VERIFICATION'.
    """
    # 1. Validate fields
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="Full Name is required.")

    valid_email, email_err = validate_email_format(req.email)
    if not valid_email:
        raise HTTPException(status_code=400, detail=email_err or "Invalid email format.")

    valid_pass, pass_err = validate_password_strength(req.password, req.confirm_password)
    if not valid_pass:
        raise HTTPException(status_code=400, detail=pass_err or "Invalid password.")

    email_clean = req.email.strip().lower()

    # 2. Check for duplicate email
    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email address already exists. Please sign in or reset your password.",
        )

    # 3. Create user record
    hashed = hash_password(req.password)
    new_user = User(
        name=req.name.strip(),
        email=email_clean,
        password_hash=hashed,
        email_verified=False,
        approval_status="PENDING_EMAIL_VERIFICATION",
        role="USER",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 4. Generate verification token and send email
    token_record = generate_verification_token(db, new_user, token_type="EMAIL_VERIFICATION")
    send_verification_email(email_clean, new_user.name, token_record.token)

    logger.info(f"[AUTH] New user registered: {email_clean} (id={new_user.id})")

    return StatusMessageResponse(
        message="Account created successfully. Please verify your email address to activate your account.",
        status="PENDING_EMAIL_VERIFICATION",
        email=email_clean,
    )


@router.get("/verify-email", response_model=StatusMessageResponse)
@router.post("/verify-email", response_model=StatusMessageResponse)
def verify_email(
    token: Optional[str] = Query(None),
    req: Optional[VerifyEmailRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Validate verification token and transition account to PENDING_APPROVAL.
    """
    raw_token = token or (req.token if req else None)
    if not raw_token:
        raise HTTPException(status_code=400, detail="Verification token is required.")

    token_record = db.query(VerificationToken).filter(
        VerificationToken.token == raw_token,
        VerificationToken.token_type == "EMAIL_VERIFICATION",
    ).first()

    if not token_record:
        raise HTTPException(status_code=400, detail="Invalid verification token.")

    if token_record.is_used:
        raise HTTPException(status_code=400, detail="This verification token has already been used.")

    if token_record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification token has expired. Please request a new one.")

    user = token_record.user
    if not user:
        raise HTTPException(status_code=404, detail="Associated user account not found.")

    # Mark token used
    token_record.is_used = True
    user.email_verified = True
    user.approval_status = "PENDING_APPROVAL"
    db.commit()

    logger.info(f"[AUTH] Email verified for user: {user.email} (id={user.id}) -> PENDING_APPROVAL")

    return StatusMessageResponse(
        message="Your email address has been successfully verified. Your account is now awaiting administrator approval.",
        status="PENDING_APPROVAL",
        email=user.email,
    )


@router.post("/resend-verification", response_model=StatusMessageResponse)
def resend_verification(email: str = Query(...), db: Session = Depends(get_db)):
    """Resend email verification token for pending accounts."""
    email_clean = email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")

    if user.email_verified:
        return StatusMessageResponse(
            message="Email address is already verified.",
            status=user.approval_status,
            email=user.email,
        )

    token_record = generate_verification_token(db, user, token_type="EMAIL_VERIFICATION")
    send_verification_email(user.email, user.name, token_record.token)

    return StatusMessageResponse(
        message="A new verification link has been sent to your email address.",
        status="PENDING_EMAIL_VERIFICATION",
        email=user.email,
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user credentials and enforce verification & approval rules.
    """
    email_clean = req.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()

    # Rule 1: Account exists?
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found. Please create a MEDLYTICS account.",
        )

    # Rule 2: Password correct?
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    # Rule 3: Email verified?
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before signing in.",
        )

    # Rule 4: Approval status?
    if user.approval_status == "PENDING_APPROVAL":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your MEDLYTICS account has been verified and is awaiting approval.",
        )
    elif user.approval_status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not currently approved for MEDLYTICS access.",
        )
    elif user.approval_status == "DISABLED" or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been disabled. Please contact administrator.",
        )
    elif user.approval_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account status: {user.approval_status}. Access not permitted.",
        )

    # Rule 5: Create JWT Session Token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )

    logger.info(f"[AUTH] User logged in successfully: {user.email} (id={user.id}, role={user.role})")

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            email_verified=user.email_verified,
            approval_status=user.approval_status,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return currently authenticated user profile."""
    return UserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        email_verified=current_user.email_verified,
        approval_status=current_user.approval_status,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
    )


@router.get("/users", response_model=List[UserResponse])
def list_users(
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all registered users (for admin management)."""
    query = db.query(User)
    if status_filter:
        query = query.filter(User.approval_status == status_filter.upper())
    users = query.order_by(User.created_at.desc()).all()

    return [
        UserResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            email_verified=u.email_verified,
            approval_status=u.approval_status,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else None,
        )
        for u in users
    ]


@router.post("/approve/{user_id}", response_model=StatusMessageResponse)
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Approve a pending user account (sets approval_status='APPROVED').
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    target_user.approval_status = "APPROVED"
    target_user.is_active = True
    db.commit()

    logger.info(f"[AUTH] User {target_user.email} approved by {current_user.email if current_user else 'system'}")

    return StatusMessageResponse(
        message=f"User {target_user.email} has been approved successfully.",
        status="APPROVED",
        email=target_user.email,
    )


@router.post("/reject/{user_id}", response_model=StatusMessageResponse)
def reject_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Reject a user account.
    """
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    target_user.approval_status = "REJECTED"
    db.commit()

    logger.info(f"[AUTH] User {target_user.email} rejected by {current_user.email if current_user else 'system'}")

    return StatusMessageResponse(
        message=f"User {target_user.email} has been rejected.",
        status="REJECTED",
        email=target_user.email,
    )


@router.post("/logout", response_model=StatusMessageResponse)
def logout():
    """Client-side token invalidation."""
    return StatusMessageResponse(
        message="Logged out successfully.",
        status="LOGGED_OUT",
    )
