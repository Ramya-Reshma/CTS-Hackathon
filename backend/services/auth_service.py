"""
Authentication and access-control service for MEDLYTICS.
Provides:
- Secure password hashing and verification using bcrypt
- Expiring, single-use email verification tokens
- JWT bearer session generation and verification
- Email dispatch / logging for verification workflows
- Admin seeding and approval workflow management
"""

import os
import re
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import bcrypt
import jwt
from sqlalchemy.orm import Session

from models import User, VerificationToken

logger = logging.getLogger(__name__)

# Authentication Configuration
SECRET_KEY = os.getenv("MEDLYTICS_JWT_SECRET", "medlytics-healthcare-super-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
VERIFICATION_TOKEN_EXPIRE_HOURS = 24

# Allowed email domains (optional restriction: empty or '*' allows any valid email format)
ALLOWED_EMAIL_DOMAINS = os.getenv("ALLOWED_EMAIL_DOMAINS", "*")


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt and a random salt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"[AUTH] Error verifying password: {e}")
        return False


def validate_email_format(email: str) -> Tuple[bool, Optional[str]]:
    """Validate email syntax and organizational domain rules."""
    if not email or "@" not in email:
        return False, "Invalid email address format."

    regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(regex, email.strip()):
        return False, "Invalid email address format."

    email_clean = email.strip().lower()
    if ALLOWED_EMAIL_DOMAINS and ALLOWED_EMAIL_DOMAINS != "*":
        domain = email_clean.split("@")[-1]
        allowed_list = [d.strip().lower().lstrip("@") for d in ALLOWED_EMAIL_DOMAINS.split(",")]
        if domain not in allowed_list:
            return False, f"Email domain '@{domain}' is not authorized. Permitted: {ALLOWED_EMAIL_DOMAINS}"

    return True, None


def validate_password_strength(password: str, confirm_password: str) -> Tuple[bool, Optional[str]]:
    """Validate password strength and confirmation match."""
    if not password:
        return False, "Password is required."
    if password != confirm_password:
        return False, "Password and confirmation password do not match."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    return True, None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError as e:
        logger.warning(f"[AUTH] Invalid token: {e}")
        return None


def generate_verification_token(db: Session, user: User, token_type: str = "EMAIL_VERIFICATION") -> VerificationToken:
    """Generate a secure, single-use, expiring verification token."""
    # Invalidate existing unused tokens of the same type for this user
    db.query(VerificationToken).filter(
        VerificationToken.user_id == user.id,
        VerificationToken.token_type == token_type,
        VerificationToken.is_used == False,
    ).update({"is_used": True})

    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)

    token_record = VerificationToken(
        user_id=user.id,
        token=raw_token,
        token_type=token_type,
        expires_at=expires_at,
        is_used=False,
    )
    db.add(token_record)
    db.commit()
    db.refresh(token_record)
    return token_record


def send_verification_email(email: str, name: str, token: str) -> bool:
    """
    Send or dispatch a verification email with the secure activation link.
    Supports SMTP environment variables or structured local dispatch logging.
    """
    app_url = os.getenv("MEDLYTICS_APP_URL", "http://localhost:5173")
    verify_url = f"{app_url}/verify-email?token={token}"

    email_host = os.getenv("EMAIL_HOST")
    email_port = int(os.getenv("EMAIL_PORT", "587"))
    email_user = os.getenv("EMAIL_USERNAME")
    email_pass = os.getenv("EMAIL_PASSWORD")
    email_from = os.getenv("EMAIL_FROM", "no-reply@medlytics.com")

    subject = "Verify your MEDLYTICS account"
    body = f"""Welcome to MEDLYTICS, {name}.

Please verify your email address to activate your account:
{verify_url}

This verification link will expire in 24 hours.

If you did not create a MEDLYTICS account, please disregard this email.
"""

    if email_host and email_user and email_pass:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = email_from
            msg["To"] = email

            with smtplib.SMTP(email_host, email_port) as server:
                server.starttls()
                server.login(email_user, email_pass)
                server.sendmail(email_from, [email], msg.as_string())
            logger.info(f"[EMAIL] Verification email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send email via SMTP: {e}")

    # Development fallback dispatch: log the complete verification message
    logger.info(f"""
================================================================================
[MEDLYTICS DISPATCH] Verification Email
To: {email}
Subject: {subject}
Verification URL: {verify_url}
================================================================================
""")
    return True


def seed_initial_admin(db: Session):
    """Seed default administrator account if none exists."""
    admin = db.query(User).filter(User.role == "ADMIN").first()
    if not admin:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@medlytics.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "MedlyticsAdmin2026!")
        admin_name = "MEDLYTICS Administrator"

        new_admin = User(
            name=admin_name,
            email=admin_email.strip().lower(),
            password_hash=hash_password(admin_password),
            email_verified=True,
            approval_status="APPROVED",
            role="ADMIN",
            is_active=True,
        )
        db.add(new_admin)
        db.commit()
        logger.info(f"[AUTH] Initial administrator seeded: {admin_email}")
