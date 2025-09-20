"""Authentication and authorization API routes."""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    token_type: str = "bearer"
    expires_in: int
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current authenticated user from token or API key."""
    if not credentials:
        return None
    
    token = credentials.credentials
    
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
    
    # Generate JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    
    return LoginResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=user.to_dict()
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(require_auth),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """Logout current user."""
    client_ip = request.client.host if request and request.client else "unknown"
    
    # Create audit log for logout
    audit_entry = AuditLogEntry.log_user_action(
        user_id=str(current_user.id),
        action=AuditAction.LOGOUT,
        message=f"User {current_user.email} logged out",
        source_ip=client_ip
    )
    db.add(audit_entry)
    await db.commit()
    
    return {"message": "Logged out successfully"}


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
    
    # Find or create user
    result = await db.execute(
        select(User).where(User.email == primary_email)
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
    
    # Generate JWT token for the webapp session
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
    
    logger.info("GitHub OAuth login successful", 
               user_id=str(user.id), email=user.email)
    
    return LoginResponse(
        access_token=jwt_token,
        expires_in=expires_in,
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

        # For a browser redirect, redirect to the frontend dashboard with the token
        # We'll use a RedirectResponse to send them to the dashboard
        return RedirectResponse(
            url=f"/dashboard?token={result.access_token}",
            status_code=status.HTTP_302_FOUND
        )

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