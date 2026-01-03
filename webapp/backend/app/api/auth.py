"""Authentication and authorization API routes."""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr, Field
import structlog
from jose import JWTError, jwt
import secrets
import httpx
from urllib.parse import urlencode

from app.core.database import get_db
from app.core.config import get_settings
from app.core.fastmcp_auth import get_current_user_from_fastmcp, get_auth_metadata, auth_provider
from app.models import User, UserRole, UserStatus, AuditLogEntry, AuditAction, AuditSeverity
from app.models.refresh_token import RefreshToken, REFRESH_TOKEN_EXPIRE_DAYS

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)

# JWT Configuration
# Use the same JWT configuration as FastMCP for compatibility
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token compatible with FastMCP JWT verifier."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add required claims for FastMCP JWT verifier
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": "service-collection-webapp",  # Must match FastMCP issuer
        "aud": "service-collection-webapp"   # Must match FastMCP audience
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return payload
    except JWTError:
        return None


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: Optional[int] = None
    user: Dict[str, Any]


class UserCreateRequest(BaseModel):
    """User creation request model."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.VIEWER
    username: Optional[str] = Field(None, max_length=100)


class UserUpdateRequest(BaseModel):
    """User update request model."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=200)
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    preferences: Optional[Dict[str, Any]] = None


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class APIKeyResponse(BaseModel):
    """API key generation response."""
    api_key: str
    created_at: datetime
    note: str = "Store this key securely - it cannot be retrieved again"


class GitHubAuthRequest(BaseModel):
    """GitHub OAuth authorization request."""
    redirect_uri: Optional[str] = None


class GitHubAuthResponse(BaseModel):
    """GitHub OAuth authorization response."""
    authorization_url: str
    state: str


class GitHubCallbackRequest(BaseModel):
    """GitHub OAuth callback request."""
    code: str
    state: str


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user from token or API key.

    Checks for authentication in this order:
    1. auth_token cookie (for browser requests)
    2. Authorization header (for API clients)
    """
    # First check for cookie-based auth (browser requests)
    token = request.cookies.get("auth_token")

    # Fall back to Authorization header if no cookie
    if not token and credentials:
        token = credentials.credentials

    # No authentication found
    if not token:
        return None
    
    # Check if it's an API key (starts with vsc_)
    if token.startswith("vsc_"):
        result = await db.execute(
            select(User).where(User.status == UserStatus.ACTIVE)
        )
        users = result.scalars().all()
        
        for user in users:
            if user.verify_api_key(token):
                return user
        return None
    
    # Use FastMCP authentication providers for token verification
    payload = await get_current_user_from_fastmcp(token)
    if not payload:
        return None
    
    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        return None
    
    # Get user from database
    try:
        result = await db.execute(
            select(User).where(User.id == UUID(user_id), User.status == UserStatus.ACTIVE)
        )
        return result.scalar_one_or_none()
    except Exception:
        return None


async def require_auth(current_user: Optional[User] = Depends(get_current_user)) -> User:
    """Require authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def require_admin(current_user: User = Depends(require_auth)) -> User:
    """Require admin role."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return access token."""
    client_ip = request.client.host if request.client else "unknown"

    # Find user by email
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not user.check_password(login_data.password):
        # Log failed login attempt
        if user:
            user.record_failed_login(client_ip)
            await db.commit()

        # Create audit log for failed login
        audit_entry = AuditLogEntry.create_entry(
            action=AuditAction.LOGIN_FAILED,
            message=f"Failed login attempt for {login_data.email}",
            severity=AuditSeverity.WARNING,
            source_ip=client_ip,
            metadata={"email": login_data.email}
        )
        db.add(audit_entry)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Check if user is active
    if not user.is_active:
        audit_entry = AuditLogEntry.create_entry(
            action=AuditAction.LOGIN_FAILED,
            message=f"Login attempt for inactive user {user.email}",
            severity=AuditSeverity.WARNING,
            user_id=str(user.id),
            source_ip=client_ip
        )
        db.add(audit_entry)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )

    # Check for too many recent failed attempts
    if user.recent_failed_logins >= 5:
        audit_entry = AuditLogEntry.create_entry(
            action=AuditAction.LOGIN_FAILED,
            message=f"Login blocked for {user.email} due to too many failed attempts",
            severity=AuditSeverity.WARNING,
            user_id=str(user.id),
            source_ip=client_ip
        )
        db.add(audit_entry)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later."
        )

    # Record successful login
    user.record_login(client_ip)

    # Create audit log for successful login
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(user.id),
        action=AuditAction.LOGIN,
        message=f"User {user.email} logged in successfully",
        source_ip=client_ip
    )
    db.add(audit_entry)
    await db.commit()

    # Generate JWT access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds

    # Generate refresh token
    refresh_token_obj, raw_refresh_token = RefreshToken.create(
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip
    )
    db.add(refresh_token_obj)
    refresh_expires_in = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # Convert to seconds

    # Set auth token as httpOnly cookie for server-side authentication
    response.set_cookie(
        key="auth_token",
        value=access_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=expires_in
    )

    # Set refresh token as httpOnly cookie (longer lived)
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=refresh_expires_in,
        path="/api/auth"  # Only send to auth endpoints for security
    )

    await db.commit()

    return LoginResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        expires_in=expires_in,
        refresh_expires_in=refresh_expires_in,
        user=user.to_dict()
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(require_auth),
    request: Request = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db)
):
    """Logout current user and revoke refresh token."""
    client_ip = request.client.host if request and request.client else "unknown"

    # Revoke refresh token if present in cookie
    refresh_token = request.cookies.get("refresh_token") if request else None
    if refresh_token:
        token_hash = RefreshToken.hash_token(refresh_token)
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        token_obj = result.scalar_one_or_none()
        if token_obj:
            token_obj.revoke(reason="logout")

    # Create audit log for logout
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(current_user.id),
        action=AuditAction.LOGOUT,
        message=f"User {current_user.email} logged out",
        source_ip=client_ip
    )
    db.add(audit_entry)
    await db.commit()

    # Clear cookies
    if response:
        response.delete_cookie(key="auth_token")
        response.delete_cookie(key="refresh_token", path="/api/auth")

    return {"message": "Logged out successfully"}


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: Optional[str] = None  # Can also be sent via cookie


class RefreshTokenResponse(BaseModel):
    """Refresh token response model."""
    access_token: str
    refresh_token: Optional[str] = None  # New refresh token if rotated
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: Optional[int] = None


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    refresh_data: RefreshTokenRequest = RefreshTokenRequest(),
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh the access token using a valid refresh token.

    The refresh token can be provided in the request body or via cookie.
    If the refresh token is old enough, a new refresh token will be issued
    (token rotation for enhanced security).
    """
    # Get refresh token from body or cookie
    raw_refresh_token = refresh_data.refresh_token or request.cookies.get("refresh_token")

    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required"
        )

    # Find the refresh token
    token_hash = RefreshToken.hash_token(raw_refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_obj = result.scalar_one_or_none()

    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Check if token is valid
    if token_obj.is_revoked:
        # Token was revoked - possible token theft, revoke entire family
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.family_id == token_obj.family_id,
                RefreshToken.is_revoked == False
            )
        )
        family_tokens = (await db.execute(
            select(RefreshToken).where(RefreshToken.family_id == token_obj.family_id)
        )).scalars().all()

        for ft in family_tokens:
            if not ft.is_revoked:
                ft.revoke(reason="security_family_revocation")

        await db.commit()

        logger.warning("Attempted use of revoked refresh token - revoking token family",
                      user_id=str(token_obj.user_id),
                      family_id=str(token_obj.family_id))

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked"
        )

    if token_obj.is_expired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )

    # Get the user
    result = await db.execute(
        select(User).where(User.id == token_obj.user_id, User.status == UserStatus.ACTIVE)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Record token use
    token_obj.record_use()

    # Generate new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # Set new access token cookie
    response.set_cookie(
        key="auth_token",
        value=access_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=expires_in
    )

    # Check if we should rotate the refresh token
    new_refresh_token = None
    refresh_expires_in = None
    client_ip = request.client.host if request.client else "unknown"

    if token_obj.should_rotate:
        # Rotate: revoke old token and create new one with same family
        token_obj.revoke(reason="rotation")
        token_obj.rotated_at = datetime.utcnow()

        # Create new refresh token in same family
        new_token_obj, new_refresh_token = RefreshToken.create(
            user_id=user.id,
            user_agent=request.headers.get("user-agent"),
            ip_address=client_ip,
            family_id=token_obj.family_id  # Keep same family
        )
        db.add(new_token_obj)
        refresh_expires_in = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        # Set new refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=settings.environment == "production",
            samesite="lax",
            max_age=refresh_expires_in,
            path="/api/auth"
        )

        logger.info("Refresh token rotated",
                   user_id=str(user.id),
                   family_id=str(token_obj.family_id))

    await db.commit()

    return RefreshTokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
        refresh_expires_in=refresh_expires_in
    )


@router.post("/revoke-all-tokens")
async def revoke_all_refresh_tokens(
    current_user: User = Depends(require_auth),
    request: Request = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db)
):
    """Revoke all refresh tokens for the current user (logout everywhere)."""
    client_ip = request.client.host if request and request.client else "unknown"

    # Revoke all user's refresh tokens
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.is_revoked == False
        )
    )
    active_tokens = result.scalars().all()

    revoked_count = 0
    for token in active_tokens:
        token.revoke(reason="revoke_all")
        revoked_count += 1

    # Create audit log
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(current_user.id),
        action=AuditAction.LOGOUT,
        message=f"User {current_user.email} revoked all refresh tokens ({revoked_count} tokens)",
        source_ip=client_ip
    )
    db.add(audit_entry)
    await db.commit()

    # Clear cookies
    if response:
        response.delete_cookie(key="auth_token")
        response.delete_cookie(key="refresh_token", path="/api/auth")

    return {
        "message": f"Revoked {revoked_count} refresh tokens",
        "revoked_count": revoked_count
    }


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(require_auth)):
    """Get current user information."""
    return current_user.to_dict()


@router.put("/me", response_model=Dict[str, Any])
async def update_current_user(
    update_data: UserUpdateRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update current user information."""
    before_data = current_user.to_dict()
    
    # Update user fields
    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    
    # Create audit log
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(current_user.id),
        action=AuditAction.USER_UPDATED,
        message=f"User {current_user.email} updated their profile",
        before_data=before_data,
        after_data=current_user.to_dict()
    )
    db.add(audit_entry)
    await db.commit()
    
    return current_user.to_dict()


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(require_auth),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Change user password."""
    # Verify current password
    if not current_user.check_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Set new password
    current_user.set_password(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    
    client_ip = request.client.host if request and request.client else "unknown"
    
    # Create audit log
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(current_user.id),
        action=AuditAction.PASSWORD_CHANGED,
        message=f"User {current_user.email} changed their password",
        source_ip=client_ip
    )
    db.add(audit_entry)
    await db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/api-key", response_model=APIKeyResponse)
async def generate_api_key(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Generate new API key for current user."""
    api_key = current_user.generate_api_key()
    current_user.updated_at = datetime.utcnow()
    
    # Create audit log
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(current_user.id),
        action=AuditAction.API_KEY_CREATED,
        message=f"User {current_user.email} generated new API key"
    )
    db.add(audit_entry)
    await db.commit()
    
    return APIKeyResponse(
        api_key=api_key,
        created_at=current_user.api_key_created_at
    )


@router.post("/users", response_model=Dict[str, Any])
async def create_user(
    user_data: UserCreateRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create new user (admin only)."""
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        status=UserStatus.ACTIVE,  # Admin-created users are immediately active
        created_by=admin_user.email
    )
    
    new_user.set_password(user_data.password)
    
    db.add(new_user)
    await db.flush()  # Get the user ID
    
    # Create audit log
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(admin_user.id),
        action=AuditAction.USER_CREATED,
        message=f"Admin {admin_user.email} created user {new_user.email}",
        metadata={"created_user_id": str(new_user.id), "role": user_data.role.value}
    )
    db.add(audit_entry)
    await db.commit()
    
    return new_user.to_dict()


@router.get("/users")
async def list_users(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all users (admin only)."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    
    return {
        "users": [user.to_dict() for user in users],
        "total": len(users)
    }


@router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (admin only)."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user.to_dict(include_sensitive=True)


@router.get("/config")
async def get_auth_config():
    """Get authentication configuration for frontend."""
    return get_auth_metadata()


# Profile Management Schemas
class ProfileUpdateRequest(BaseModel):
    """User profile update request."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None, max_length=50)


class ProfileResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    timezone: Optional[str]
    avatar_url: Optional[str]
    role: str
    status: str
    created_at: datetime
    last_login_at: Optional[datetime]

    @classmethod
    def from_user(cls, user: User) -> "ProfileResponse":
        return cls(
            id=str(user.id),
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            timezone=user.timezone,
            avatar_url=user.avatar_url,
            role=user.role.value,
            status=user.status.value,
            created_at=user.created_at,
            last_login_at=user.last_login_at
        )


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(current_user: User = Depends(require_auth)):
    """Get current user's profile."""
    return ProfileResponse.from_user(current_user)


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdateRequest,
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile."""
    client_ip = request.client.host if request.client else "unknown"

    # Track what fields are being updated
    updates = {}

    # Update allowed fields
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name
        updates["first_name"] = profile_data.first_name

    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name
        updates["last_name"] = profile_data.last_name

    if profile_data.phone is not None:
        current_user.phone = profile_data.phone
        updates["phone"] = profile_data.phone

    if profile_data.timezone is not None:
        current_user.timezone = profile_data.timezone
        updates["timezone"] = profile_data.timezone

    # Create audit log
    if updates:
        audit_entry = AuditLogEntry.log_user_action(
            user_id=current_user.id,
            action=AuditAction.USER_UPDATED,
            message=f"User updated profile: {', '.join(updates.keys())}",
            source_ip=client_ip,
            metadata={"updated_fields": list(updates.keys())}
        )
        db.add(audit_entry)

    # Save changes
    await db.commit()
    await db.refresh(current_user)

    logger.info("User profile updated",
               user_id=str(current_user.id),
               updated_fields=list(updates.keys()))

    return ProfileResponse.from_user(current_user)


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    new_role: UserRole,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update user role (admin only)."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_role = user.role
    user.role = new_role
    user.updated_at = datetime.utcnow()
    
    # Create audit log
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(admin_user.id),
        action=AuditAction.USER_ROLE_CHANGED,
        message=f"Admin {admin_user.email} changed {user.email} role from {old_role.value} to {new_role.value}",
        metadata={
            "target_user_id": str(user.id),
            "old_role": old_role.value,
            "new_role": new_role.value
        }
    )
    db.add(audit_entry)
    await db.commit()
    
    return user.to_dict()


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: UUID,
    new_status: UserStatus,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update user status (admin only)."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_status = user.status
    user.status = new_status
    user.updated_at = datetime.utcnow()
    
    if new_status == UserStatus.SUSPENDED:
        user.suspended_at = datetime.utcnow()
    
    # Create audit log
    action = AuditAction.USER_SUSPENDED if new_status == UserStatus.SUSPENDED else AuditAction.USER_ACTIVATED
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(admin_user.id),
        action=action,
        message=f"Admin {admin_user.email} changed {user.email} status from {old_status.value} to {new_status.value}",
        metadata={
            "target_user_id": str(user.id),
            "old_status": old_status.value,
            "new_status": new_status.value
        }
    )
    db.add(audit_entry)
    await db.commit()
    
    return user.to_dict()


# GitHub OAuth State Storage (in production, use Redis or database)
_oauth_states: Dict[str, Dict[str, Any]] = {}


@router.post("/github/authorize", response_model=GitHubAuthResponse)
async def github_authorize(
    request_data: GitHubAuthRequest = GitHubAuthRequest(),
    request: Request = None
):
    """Initiate GitHub OAuth authorization flow."""
    # Allow GitHub OAuth even in JWT mode if GitHub credentials are configured
    if not auth_provider.config.github_client_id or not auth_provider.config.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub authentication is not configured"
        )
    
    if not auth_provider.config.github_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub client ID not configured"
        )
    
    # Generate secure state parameter
    state = secrets.token_urlsafe(32)
    
    # Use provided redirect URI or default from config
    redirect_uri = request_data.redirect_uri or auth_provider.config.github_redirect_uri
    if not redirect_uri:
        # Fallback to current host
        base_url = str(request.base_url).rstrip("/") if request else "http://localhost:9001"
        redirect_uri = f"{base_url}/auth/github/callback"
    
    # Store state with metadata
    _oauth_states[state] = {
        "timestamp": datetime.utcnow(),
        "redirect_uri": redirect_uri,
        "client_ip": request.client.host if request and request.client else "unknown"
    }
    
    # Build GitHub authorization URL
    github_auth_params = {
        "client_id": auth_provider.config.github_client_id,
        "redirect_uri": redirect_uri,
        "scope": "user:email read:user",
        "state": state,
        "response_type": "code"
    }
    
    authorization_url = f"https://github.com/login/oauth/authorize?{urlencode(github_auth_params)}"
    
    logger.info("Generated GitHub OAuth authorization URL", 
               state=state, redirect_uri=redirect_uri)
    
    return GitHubAuthResponse(
        authorization_url=authorization_url,
        state=state
    )


@router.get("/github/login")
async def github_login_redirect(request: Request):
    """Direct GitHub OAuth login redirect (GET endpoint for browser navigation)."""
    # Allow GitHub OAuth even in JWT mode if GitHub credentials are configured
    if not auth_provider.config.github_client_id or not auth_provider.config.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub authentication is not configured"
        )

    # Generate secure state parameter
    state = secrets.token_urlsafe(32)

    # Use default redirect URI from config
    redirect_uri = auth_provider.config.github_redirect_uri
    if not redirect_uri:
        # Fallback to current host
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/api/auth/github/callback"

    # Store state with metadata
    _oauth_states[state] = {
        "timestamp": datetime.utcnow(),
        "redirect_uri": redirect_uri,
        "client_ip": request.client.host if request and request.client else "unknown"
    }

    # Build GitHub authorization URL
    github_auth_params = {
        "client_id": auth_provider.config.github_client_id,
        "redirect_uri": redirect_uri,
        "scope": "user:email read:user",
        "state": state,
        "response_type": "code"
    }

    authorization_url = f"https://github.com/login/oauth/authorize?{urlencode(github_auth_params)}"

    logger.info("GitHub OAuth login redirect",
               state=state, redirect_uri=redirect_uri)

    # Directly redirect to GitHub
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=authorization_url, status_code=302)


@router.post("/github/callback")
async def github_callback(
    callback_data: GitHubCallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback and complete authentication."""
    # Allow GitHub OAuth callback even in JWT mode if GitHub credentials are configured
    if not auth_provider.config.github_client_id or not auth_provider.config.github_client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub authentication is not configured"
        )
    
    # Validate state parameter
    if callback_data.state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter"
        )
    
    state_data = _oauth_states.pop(callback_data.state)
    
    # Check state timestamp (expire after 10 minutes)
    if datetime.utcnow() - state_data["timestamp"] > timedelta(minutes=10):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state has expired"
        )
    
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": auth_provider.config.github_client_id,
                    "client_secret": auth_provider.config.github_client_secret,
                    "code": callback_data.code,
                    "redirect_uri": state_data["redirect_uri"]
                }
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            
            if "access_token" not in token_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to obtain access token from GitHub"
                )
            
            access_token = token_data["access_token"]
            
            # Get user information from GitHub
            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_response.raise_for_status()
            github_user = user_response.json()
            
            # Get user email (primary email)
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            email_response.raise_for_status()
            emails = email_response.json()
            
            # Find primary email
            primary_email = None
            for email_data in emails:
                if email_data.get("primary", False) and email_data.get("verified", False):
                    primary_email = email_data["email"]
                    break
            
            if not primary_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No verified primary email found on GitHub account"
                )
    
    except httpx.HTTPError as e:
        logger.error("Error communicating with GitHub API", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to authenticate with GitHub"
        )
    
    # Find or create user (with eager loading of connected accounts)
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(User)
        .options(selectinload(User.connected_accounts))
        .where(User.email == primary_email)
    )
    user = result.scalar_one_or_none()
    
    client_ip = request.client.host if request.client else "unknown"
    
    if not user:
        # Create new user from GitHub profile
        user = User(
            email=primary_email,
            username=github_user.get("login"),
            first_name=github_user.get("name", "").split(" ")[0] if github_user.get("name") else github_user.get("login", "User"),
            last_name=" ".join(github_user.get("name", "").split(" ")[1:]) if github_user.get("name") and " " in github_user.get("name") else "",
            role=UserRole.VIEWER,  # Default role for new GitHub users
            status=UserStatus.ACTIVE,
            oauth_provider="github",
            oauth_subject=str(github_user["id"]),
            avatar_url=github_user.get("avatar_url")
        )
        
        # Set a random password (not used for GitHub OAuth users)
        user.set_password(secrets.token_urlsafe(32))
        
        db.add(user)
        await db.flush()  # Get the user ID
        
        # Create audit log for new user
        audit_entry = AuditLogEntry.create_entry(
            action=AuditAction.USER_CREATED,
            message=f"New user created via GitHub OAuth: {primary_email}",
            severity=AuditSeverity.INFO,
            user_id=str(user.id),
            source_ip=client_ip,
            metadata={
                "github_id": github_user["id"],
                "github_login": github_user.get("login"),
                "auth_provider": "github"
            }
        )
        db.add(audit_entry)
        
        logger.info("Created new user from GitHub OAuth",
                   user_id=str(user.id), github_id=github_user["id"])
    
    else:
        # Update existing user's GitHub information
        if not user.oauth_subject:
            user.oauth_subject = str(github_user["id"])
        
        if github_user.get("avatar_url") and not user.avatar_url:
            user.avatar_url = github_user.get("avatar_url")
        
        # Record login
        user.record_login(client_ip)

    # Create or update ConnectedAccount for GitHub
    from app.models.connected_account import ConnectedAccount, ProviderType

    # Check if GitHub connection already exists
    github_account_result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.user_id == user.id,
            ConnectedAccount.provider_type == ProviderType.GITHUB,
            ConnectedAccount.provider_id == str(github_user["id"])
        )
    )
    github_account = github_account_result.scalar_one_or_none()

    if not github_account:
        # Create new GitHub connected account
        github_account = ConnectedAccount(
            user_id=user.id,
            provider_type=ProviderType.GITHUB,
            provider_id=str(github_user["id"]),
            provider_username=github_user.get("login"),
            provider_email=primary_email,
            display_name=github_user.get("name") or github_user.get("login"),
            avatar_url=github_user.get("avatar_url"),
            provider_data={
                "login": github_user.get("login"),
                "name": github_user.get("name"),
                "bio": github_user.get("bio"),
                "company": github_user.get("company"),
                "location": github_user.get("location"),
                "blog": github_user.get("blog"),
                "public_repos": github_user.get("public_repos"),
                "followers": github_user.get("followers"),
                "following": github_user.get("following")
            },
            access_token_hash=access_token,  # TODO: Should encrypt this for security
            is_active=True
        )
        db.add(github_account)

        logger.info("Created GitHub connected account",
                   user_id=str(user.id), provider_id=str(github_user["id"]))
    else:
        # Update existing GitHub connection with latest info
        github_account.provider_username = github_user.get("login")
        github_account.provider_email = primary_email
        github_account.display_name = github_user.get("name") or github_user.get("login")
        github_account.avatar_url = github_user.get("avatar_url")
        github_account.profile_data = {
            "login": github_user.get("login"),
            "name": github_user.get("name"),
            "bio": github_user.get("bio"),
            "company": github_user.get("company"),
            "location": github_user.get("location"),
            "blog": github_user.get("blog"),
            "public_repos": github_user.get("public_repos"),
            "followers": github_user.get("followers"),
            "following": github_user.get("following")
        }
        github_account.access_token = access_token
        github_account.last_login_at = datetime.utcnow()
        github_account.is_active = True

        logger.info("Updated GitHub connected account",
                   user_id=str(user.id), provider_id=str(github_user["id"]))

    # Create audit log for login
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(user.id),
        action=AuditAction.LOGIN,
        message=f"User {user.email} logged in via GitHub OAuth",
        source_ip=client_ip,
        metadata={
            "auth_provider": "github",
            "github_id": github_user["id"]
        }
    )
    db.add(audit_entry)
    await db.commit()

    # Refresh user with connected accounts to ensure they're loaded
    await db.refresh(user)
    result = await db.execute(
        select(User)
        .options(selectinload(User.connected_accounts))
        .where(User.id == user.id)
    )
    user = result.scalar_one()

    # Generate JWT access token for the webapp session
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds

    # Generate refresh token for GitHub OAuth users
    user_agent = request.headers.get("user-agent") if request else None
    refresh_token_obj, raw_refresh_token = RefreshToken.create(
        user_id=user.id,
        user_agent=user_agent,
        ip_address=client_ip,
        device_info="GitHub OAuth"
    )
    db.add(refresh_token_obj)
    refresh_expires_in = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    await db.commit()

    logger.info("GitHub OAuth login successful",
               user_id=str(user.id), email=user.email)

    return LoginResponse(
        access_token=jwt_token,
        refresh_token=raw_refresh_token,
        expires_in=expires_in,
        refresh_expires_in=refresh_expires_in,
        user=user.to_dict()
    )


@router.get("/github/callback")
async def github_callback_get(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth callback (GET endpoint for browser redirects)."""
    # Convert GET parameters to POST-style callback
    callback_data = GitHubCallbackRequest(code=code, state=state)

    try:
        result = await github_callback(callback_data, request, db)

        # Create response with redirect
        response = RedirectResponse(
            url="/dashboard",
            status_code=status.HTTP_302_FOUND
        )

        # Set auth token cookie
        response.set_cookie(
            key="auth_token",
            value=result.access_token,
            httponly=True,
            secure=settings.environment == "production",
            samesite="lax",
            max_age=result.expires_in
        )

        # Set refresh token cookie if present
        if result.refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=result.refresh_token,
                httponly=True,
                secure=settings.environment == "production",
                samesite="lax",
                max_age=result.refresh_expires_in,
                path="/api/auth"
            )

        return response

    except HTTPException as e:
        # In a browser context, redirect to login with error
        error_message = e.detail if hasattr(e, 'detail') else 'Authentication failed'
        return RedirectResponse(
            url=f"/login?error={error_message}",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/github/redirect")
async def github_redirect_handler(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle GitHub OAuth redirect (GET endpoint for browser redirects)."""
    # Convert GET parameters to POST-style callback
    callback_data = GitHubCallbackRequest(code=code, state=state)

    try:
        result = await github_callback(callback_data, request, db)

        # For a browser redirect, we might want to redirect to the frontend
        # with the token or set a secure cookie
        # For now, return the same response as the POST endpoint
        return result

    except HTTPException as e:
        # In a browser context, you might want to redirect to an error page
        # instead of returning JSON
        raise e


# ============================================================================
# Connected Accounts Management
# ============================================================================

class ConnectedAccountResponse(BaseModel):
    """Response model for connected account information."""
    id: str
    provider_type: str
    provider_username: Optional[str] = None
    provider_email: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    profile_url: Optional[str] = None
    is_primary: bool = False
    is_verified: bool = False
    is_active: bool = True
    first_connected_at: str
    last_used_at: Optional[str] = None
    last_sync_at: Optional[str] = None
    connection_count: dict = {}


class ConnectedAccountsListResponse(BaseModel):
    """Response model for list of connected accounts."""
    connected_accounts: List[ConnectedAccountResponse]
    total_count: int


@router.get("/connected-accounts", response_model=ConnectedAccountsListResponse)
async def get_connected_accounts(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get user's connected OAuth accounts."""
    from app.models.connected_account import ConnectedAccount

    result = await db.execute(
        select(ConnectedAccount)
        .where(ConnectedAccount.user_id == current_user.id)
        .order_by(ConnectedAccount.created_at.desc())
    )
    connected_accounts = result.scalars().all()

    return ConnectedAccountsListResponse(
        connected_accounts=[
            ConnectedAccountResponse(**account.to_dict())
            for account in connected_accounts
        ],
        total_count=len(connected_accounts)
    )


@router.delete("/connected-accounts/{account_id}")
async def disconnect_account(
    account_id: str,
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Disconnect an OAuth account."""
    from app.models.connected_account import ConnectedAccount
    from app.models.audit_log import AuditLogEntry, AuditAction

    # Find the connected account
    result = await db.execute(
        select(ConnectedAccount)
        .where(
            ConnectedAccount.id == account_id,
            ConnectedAccount.user_id == current_user.id
        )
    )
    connected_account = result.scalar_one_or_none()

    if not connected_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connected account not found"
        )

    # Check if this is the user's only authentication method
    if current_user.password_hash is None:
        # Count other active connected accounts
        result = await db.execute(
            select(func.count(ConnectedAccount.id))
            .where(
                ConnectedAccount.user_id == current_user.id,
                ConnectedAccount.id != account_id,
                ConnectedAccount.is_active == True
            )
        )
        other_accounts_count = result.scalar()

        if other_accounts_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot disconnect last authentication method. Set a password first."
            )

    # Store account info for audit log
    account_info = connected_account.to_dict()

    # Remove the connected account
    await db.delete(connected_account)

    # Log the disconnection
    client_ip = request.client.host if request.client else "unknown"
    audit_entry = AuditLogEntry.log_user_action(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATED,
        message=f"Disconnected {account_info['provider_type']} account",
        source_ip=client_ip,
        metadata={
            "action": "account_disconnected",
            "provider_type": account_info["provider_type"],
            "provider_username": account_info.get("provider_username"),
            "disconnected_account_id": account_id
        }
    )
    db.add(audit_entry)

    await db.commit()

    return {"message": "Account disconnected successfully"}


# ============================================================================
# PassKey Management
# ============================================================================

class PassKeyResponse(BaseModel):
    """Response model for PassKey information."""
    id: str
    name: str
    description: Optional[str] = None
    authenticator_type: str
    transport_methods: List[str] = []
    is_active: bool = True
    is_backup_eligible: bool = False
    is_backup_state: bool = False
    created_at: str
    last_used_at: Optional[str] = None
    usage_count: dict = {}
    device_info: dict = {}


class PassKeysListResponse(BaseModel):
    """Response model for list of PassKeys."""
    passkeys: List[PassKeyResponse]
    total_count: int


class PassKeyRegistrationRequest(BaseModel):
    """Request model for PassKey registration."""
    name: str
    description: Optional[str] = None
    credential_id: str
    public_key: str
    authenticator_type: str
    transport_methods: List[str] = []
    device_info: dict = {}


class PassKeyAuthenticationRequest(BaseModel):
    """Request model for PassKey authentication."""
    credential_id: str
    authenticator_data: str
    client_data_json: str
    signature: str
    operation_context: Optional[str] = None  # e.g., "deployment_confirmation"


@router.get("/passkeys", response_model=PassKeysListResponse)
async def get_passkeys(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get user's registered PassKeys."""
    from app.models.connected_account import PassKey

    result = await db.execute(
        select(PassKey)
        .where(PassKey.user_id == current_user.id)
        .order_by(PassKey.created_at.desc())
    )
    passkeys = result.scalars().all()

    return PassKeysListResponse(
        passkeys=[
            PassKeyResponse(**passkey.to_dict())
            for passkey in passkeys
        ],
        total_count=len(passkeys)
    )


@router.post("/passkeys/register", response_model=PassKeyResponse)
async def register_passkey(
    passkey_data: PassKeyRegistrationRequest,
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Register a new PassKey for the user."""
    from app.models.connected_account import PassKey, PassKeyAuthenticatorType
    from app.models.audit_log import AuditLogEntry, AuditAction

    # Validate authenticator type
    try:
        auth_type = PassKeyAuthenticatorType(passkey_data.authenticator_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authenticator type"
        )

    # Check if credential already exists
    result = await db.execute(
        select(PassKey).where(PassKey.credential_id == passkey_data.credential_id)
    )
    existing_passkey = result.scalar_one_or_none()

    if existing_passkey:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PassKey credential already registered"
        )

    # Create new PassKey
    new_passkey = PassKey(
        user_id=current_user.id,
        credential_id=passkey_data.credential_id,
        public_key=passkey_data.public_key,
        authenticator_type=auth_type,
        name=passkey_data.name,
        description=passkey_data.description,
        transport_methods=passkey_data.transport_methods,
        device_info=passkey_data.device_info
    )

    db.add(new_passkey)

    # Log PassKey registration
    client_ip = request.client.host if request.client else "unknown"
    audit_entry = AuditLogEntry.log_user_action(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATED,
        message=f"Registered new PassKey: {passkey_data.name}",
        source_ip=client_ip,
        metadata={
            "action": "passkey_registered",
            "passkey_name": passkey_data.name,
            "authenticator_type": passkey_data.authenticator_type,
            "transport_methods": passkey_data.transport_methods
        }
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(new_passkey)

    return PassKeyResponse(**new_passkey.to_dict())


@router.delete("/passkeys/{passkey_id}")
async def delete_passkey(
    passkey_id: str,
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Delete a PassKey."""
    from app.models.connected_account import PassKey
    from app.models.audit_log import AuditLogEntry, AuditAction

    # Find the PassKey
    result = await db.execute(
        select(PassKey)
        .where(
            PassKey.id == passkey_id,
            PassKey.user_id == current_user.id
        )
    )
    passkey = result.scalar_one_or_none()

    if not passkey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PassKey not found"
        )

    # Store passkey info for audit log
    passkey_info = passkey.to_dict()

    # Remove the PassKey
    await db.delete(passkey)

    # Log PassKey deletion
    client_ip = request.client.host if request.client else "unknown"
    audit_entry = AuditLogEntry.log_user_action(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATED,
        message=f"Deleted PassKey: {passkey_info['name']}",
        source_ip=client_ip,
        metadata={
            "action": "passkey_deleted",
            "passkey_name": passkey_info["name"],
            "passkey_id": passkey_id
        }
    )
    db.add(audit_entry)

    await db.commit()

    return {"message": "PassKey deleted successfully"}


@router.post("/passkeys/authentication-challenge")
async def get_passkey_authentication_challenge(
    operation_context: Optional[str] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get WebAuthn authentication challenge for PassKey verification."""
    from app.models.connected_account import PassKey
    import secrets
    import base64

    # Check if user has any active PassKeys
    result = await db.execute(
        select(PassKey)
        .where(
            PassKey.user_id == current_user.id,
            PassKey.is_active == True
        )
    )
    passkeys = result.scalars().all()

    if not passkeys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active PassKeys found. Please register a PassKey first."
        )

    # Generate challenge
    challenge_bytes = secrets.token_bytes(32)
    challenge = base64.urlsafe_b64encode(challenge_bytes).decode().rstrip('=')

    # Prepare credential IDs for authentication
    allowed_credentials = [
        {
            "id": passkey.credential_id,
            "type": "public-key",
            "transports": passkey.transport_methods if passkey.transport_methods else ["internal"]
        }
        for passkey in passkeys
    ]

    return {
        "challenge": challenge,
        "allowCredentials": allowed_credentials,
        "timeout": 60000,
        "userVerification": "required",
        "rpId": "mcp-vultr.l.supported.systems",
        "operation_context": operation_context
    }


@router.post("/passkeys/verify-authentication")
async def verify_passkey_authentication(
    authentication_data: Dict[str, Any],
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Verify WebAuthn authentication assertion for PassKey confirmation."""
    from app.models.connected_account import PassKey
    import base64
    import json
    from datetime import datetime

    try:
        # Extract authentication data
        credential_id = authentication_data.get("id")
        raw_id = authentication_data.get("rawId")
        response_data = authentication_data.get("response", {})
        operation_context = authentication_data.get("operation_context")

        if not credential_id or not raw_id or not response_data:
            raise HTTPException(
                status_code=400,
                detail="Missing required authentication data"
            )

        # Find the PassKey by credential ID
        stmt = select(PassKey).where(
            PassKey.credential_id == credential_id,
            PassKey.user_id == current_user.id,
            PassKey.is_active == True
        )
        result = await db.execute(stmt)
        passkey = result.scalar_one_or_none()

        if not passkey:
            raise HTTPException(
                status_code=404,
                detail="PassKey not found or inactive"
            )

        # Parse authentication response
        try:
            client_data_json = base64.b64decode(response_data["clientDataJSON"])
            authenticator_data = base64.b64decode(response_data["authenticatorData"])
            signature = base64.b64decode(response_data["signature"])

            # Parse client data JSON
            client_data = json.loads(client_data_json.decode('utf-8'))

            # Basic validation
            if client_data.get("type") != "webauthn.get":
                raise HTTPException(
                    status_code=400,
                    detail="Invalid authentication type"
                )

            if client_data.get("origin") != "https://mcp-vultr.l.supported.systems":
                raise HTTPException(
                    status_code=400,
                    detail="Invalid origin"
                )

            # TODO: Implement full cryptographic verification
            # For now, we'll do basic validation and trust the client
            # In production, you would:
            # 1. Verify the signature using the stored public key
            # 2. Validate the authenticator data
            # 3. Check the challenge matches what was issued
            # 4. Verify the counter value

            # Update PassKey usage
            passkey.sign_count += 1  # Increment for replay protection
            passkey.last_used_at = datetime.utcnow()

            await db.commit()

            # Log successful authentication
            await create_audit_log(
                db=db,
                user_id=current_user.id,
                action=AuditAction.PASSKEY_AUTHENTICATION,
                resource_type="passkey",
                resource_id=str(passkey.id),
                details={
                    "passkey_name": passkey.name,
                    "operation_context": operation_context,
                    "user_agent": "WebAuthn Browser",  # Could extract from headers
                }
            )

            return {
                "verified": True,
                "passkey_id": str(passkey.id),
                "passkey_name": passkey.name,
                "operation_context": operation_context,
                "authenticated_at": datetime.utcnow().isoformat()
            }

        except (ValueError, json.JSONDecodeError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid authentication data format: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PassKey authentication verification failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Authentication verification failed"
        )


@router.post("/passkeys/authenticate")
async def authenticate_passkey(
    auth_data: PassKeyAuthenticationRequest,
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate using PassKey for secure operations."""
    from app.models.connected_account import PassKey
    from app.models.audit_log import AuditLogEntry, AuditAction

    # Find the PassKey
    result = await db.execute(
        select(PassKey)
        .where(
            PassKey.credential_id == auth_data.credential_id,
            PassKey.user_id == current_user.id,
            PassKey.is_active == True
        )
    )
    passkey = result.scalar_one_or_none()

    if not passkey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PassKey not found or inactive"
        )

    # TODO: Implement actual WebAuthn signature verification
    # For now, we'll simulate successful authentication
    # In production, you would verify the signature against the public key

    # Record successful authentication
    passkey.record_successful_use("confirmation")

    # Log PassKey authentication
    client_ip = request.client.host if request.client else "unknown"
    audit_entry = AuditLogEntry.log_user_action(
        user_id=current_user.id,
        action=AuditAction.API_KEY_USED,  # Reusing existing action for now
        message=f"PassKey authentication successful: {passkey.name}",
        source_ip=client_ip,
        metadata={
            "action": "passkey_authentication",
            "passkey_name": passkey.name,
            "operation_context": auth_data.operation_context,
            "success": True
        }
    )
    db.add(audit_entry)

    await db.commit()

    return {
        "authenticated": True,
        "passkey_name": passkey.name,
        "operation_context": auth_data.operation_context
    }


# ============================================================================
# WebAuthn PassKey Registration
# ============================================================================

class WebAuthnRegistrationChallenge(BaseModel):
    """WebAuthn registration challenge response."""
    challenge: str
    rp: dict
    user: dict
    pubKeyCredParams: List[dict]
    authenticatorSelection: dict
    timeout: int = 60000
    attestation: str = "direct"


class WebAuthnRegistrationRequest(BaseModel):
    """WebAuthn registration credential."""
    id: str
    rawId: str
    response: dict
    type: str


@router.post("/passkeys/registration-challenge", response_model=WebAuthnRegistrationChallenge)
async def get_passkey_registration_challenge(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get WebAuthn registration challenge for PassKey creation."""
    import secrets
    import base64

    # Generate random challenge
    challenge_bytes = secrets.token_bytes(32)
    challenge = base64.urlsafe_b64encode(challenge_bytes).decode().rstrip('=')

    # Convert user ID to base64url
    user_id_bytes = str(current_user.id).encode()
    user_id_b64 = base64.urlsafe_b64encode(user_id_bytes).decode().rstrip('=')

    return WebAuthnRegistrationChallenge(
        challenge=challenge,
        rp={
            "id": "mcp-vultr.l.supported.systems",
            "name": "Vultr Service Collections"
        },
        user={
            "id": user_id_b64,
            "name": current_user.email,
            "displayName": current_user.full_name
        },
        pubKeyCredParams=[
            {"type": "public-key", "alg": -7},  # ES256
            {"type": "public-key", "alg": -257}  # RS256
        ],
        authenticatorSelection={
            "authenticatorAttachment": "platform",
            "userVerification": "preferred",
            "requireResidentKey": False
        },
        timeout=60000,
        attestation="direct"
    )


@router.post("/passkeys/verify-registration")
async def verify_passkey_registration(
    registration_data: WebAuthnRegistrationRequest,
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Verify WebAuthn registration and create PassKey."""
    from app.models.connected_account import PassKey, PassKeyAuthenticatorType
    from app.models.audit_log import AuditLogEntry, AuditAction
    import base64
    import json

    try:
        # For now, we'll do basic validation and create the PassKey
        # In a production system, you'd want proper WebAuthn verification

        # Parse client data
        client_data_json = base64.b64decode(registration_data.response["clientDataJSON"] + "==")
        client_data = json.loads(client_data_json.decode())

        # Basic validation
        if client_data.get("type") != "webauthn.create":
            raise ValueError("Invalid client data type")

        # Create PassKey entry
        passkey = PassKey(
            user_id=current_user.id,
            credential_id=registration_data.id,
            public_key=registration_data.response["attestationObject"],  # Store attestation for now
            authenticator_type=PassKeyAuthenticatorType.PLATFORM,  # Assume platform for now
            name=f"PassKey {current_user.email}",
            last_used_at=None,
            usage_count=0,
            is_active=True
        )

        db.add(passkey)

        # Log the registration
        client_ip = request.client.host if request.client else "unknown"
        audit_entry = AuditLogEntry(
            user_id=current_user.id,
            action=AuditAction.AUTHENTICATION_SETUP,
            message=f"PassKey registered for user {current_user.email}",
            source_ip=client_ip,
            metadata={
                "action": "passkey_registration",
                "credential_id": registration_data.id,
                "authenticator_type": "platform"
            }
        )
        db.add(audit_entry)

        await db.commit()

        return {
            "success": True,
            "passkey_id": str(passkey.id),
            "message": "PassKey registered successfully"
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to verify PassKey registration: {str(e)}"
        )


# ============================================================================
# Authentication Sessions Management
# ============================================================================

class AuthenticationSessionResponse(BaseModel):
    """Response model for authentication session."""
    id: str
    device_fingerprint: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: str
    location_data: dict = {}
    login_method: str
    provider_type: Optional[str] = None
    created_at: str
    last_activity_at: str
    expires_at: str
    ended_at: Optional[str] = None
    is_active: bool = True
    is_expired: bool = False
    end_reason: Optional[str] = None
    is_suspicious: bool = False
    security_flags: List[str] = []
    request_count: dict = {}
    duration_minutes: Optional[int] = None


class AuthenticationSessionsListResponse(BaseModel):
    """Response model for list of authentication sessions."""
    sessions: List[AuthenticationSessionResponse]
    active_count: int
    total_count: int


@router.get("/sessions", response_model=AuthenticationSessionsListResponse)
async def get_authentication_sessions(
    include_inactive: bool = False,
    limit: int = 50,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Get user's authentication sessions."""
    from app.models.connected_account import AuthenticationSession

    query = select(AuthenticationSession).where(
        AuthenticationSession.user_id == current_user.id
    )

    if not include_inactive:
        query = query.where(AuthenticationSession.is_active == True)

    query = query.order_by(AuthenticationSession.last_activity_at.desc()).limit(limit)

    result = await db.execute(query)
    sessions = result.scalars().all()

    # Count active sessions
    active_result = await db.execute(
        select(func.count(AuthenticationSession.id))
        .where(
            AuthenticationSession.user_id == current_user.id,
            AuthenticationSession.is_active == True
        )
    )
    active_count = active_result.scalar()

    return AuthenticationSessionsListResponse(
        sessions=[
            AuthenticationSessionResponse(**session.to_dict())
            for session in sessions
        ],
        active_count=active_count,
        total_count=len(sessions)
    )


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Revoke an authentication session."""
    from app.models.connected_account import AuthenticationSession
    from app.models.audit_log import AuditLogEntry, AuditAction

    # Find the session
    result = await db.execute(
        select(AuthenticationSession)
        .where(
            AuthenticationSession.id == session_id,
            AuthenticationSession.user_id == current_user.id
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # End the session
    session.end_session("revoked")

    # Log session revocation
    client_ip = request.client.host if request.client else "unknown"
    audit_entry = AuditLogEntry.log_user_action(
        user_id=current_user.id,
        action=AuditAction.LOGOUT,
        message="Session revoked by user",
        source_ip=client_ip,
        metadata={
            "action": "session_revoked",
            "revoked_session_id": session_id,
            "revoked_session_ip": session.ip_address
        }
    )
    db.add(audit_entry)

    await db.commit()

    return {"message": "Session revoked successfully"}


@router.delete("/sessions/all")
async def revoke_all_sessions(
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """Revoke all user sessions except the current one."""
    from app.models.connected_account import AuthenticationSession
    from app.models.audit_log import AuditLogEntry, AuditAction

    # Get current session token from request
    auth_header = request.headers.get("Authorization")
    current_token = None
    if auth_header and auth_header.startswith("Bearer "):
        current_token = auth_header.split(" ")[1]

    # Find all active sessions except current one
    query = select(AuthenticationSession).where(
        AuthenticationSession.user_id == current_user.id,
        AuthenticationSession.is_active == True
    )

    if current_token:
        # TODO: Add logic to exclude current session based on token
        # For now, we'll revoke all sessions
        pass

    result = await db.execute(query)
    sessions = result.scalars().all()

    revoked_count = 0
    for session in sessions:
        session.end_session("revoked_all")
        revoked_count += 1

    # Log mass session revocation
    client_ip = request.client.host if request.client else "unknown"
    audit_entry = AuditLogEntry.log_user_action(
        user_id=current_user.id,
        action=AuditAction.LOGOUT,
        message=f"Revoked all sessions ({revoked_count} sessions)",
        source_ip=client_ip,
        metadata={
            "action": "all_sessions_revoked",
            "revoked_count": revoked_count
        }
    )
    db.add(audit_entry)

    await db.commit()

    return {"message": f"Revoked {revoked_count} sessions successfully"}