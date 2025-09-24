"""Connected accounts models for OAuth providers and PassKey management."""

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, DateTime, Boolean, JSON, Text,
    ForeignKey, UniqueConstraint, Index, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProviderType(enum.Enum):
    """OAuth provider types."""
    GITHUB = "github"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    DISCORD = "discord"
    SLACK = "slack"


class PassKeyAuthenticatorType(enum.Enum):
    """PassKey authenticator types based on WebAuthn spec."""
    PLATFORM = "platform"  # Built-in authenticator (TouchID, FaceID, Windows Hello)
    CROSS_PLATFORM = "cross-platform"  # External authenticator (YubiKey, etc.)


class ConnectedAccount(Base):
    """
    OAuth provider connections for users.

    Tracks external authentication providers connected to user accounts
    with OAuth tokens for API access and profile data synchronization.
    """
    __tablename__ = "connected_accounts"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Provider information
    provider_type = Column(Enum(ProviderType), nullable=False)
    provider_id = Column(String(255), nullable=False)  # External user ID from provider
    provider_username = Column(String(255), nullable=True)  # Username on provider
    provider_email = Column(String(255), nullable=True)  # Email from provider

    # Profile data
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    profile_url = Column(String(500), nullable=True)
    provider_data = Column(JSON, default=dict)  # Raw profile data from provider

    # OAuth tokens (encrypted)
    access_token_hash = Column(Text, nullable=True)  # Encrypted OAuth access token
    refresh_token_hash = Column(Text, nullable=True)  # Encrypted OAuth refresh token
    token_expires_at = Column(DateTime, nullable=True)
    token_scope = Column(JSON, default=list)  # OAuth scopes granted

    # Security and metadata
    is_primary = Column(Boolean, default=False)  # Primary account for this provider
    is_verified = Column(Boolean, default=False)  # Email verified on provider
    is_active = Column(Boolean, default=True)  # Connection is active

    # Audit trail
    first_connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)  # Last profile sync
    connection_count = Column(JSON, default=dict)  # Usage statistics

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="connected_accounts")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('provider_type', 'provider_id', name='unique_provider_account'),
        UniqueConstraint('user_id', 'provider_type', 'is_primary', name='unique_primary_provider'),
        Index('idx_connected_accounts_user', 'user_id'),
        Index('idx_connected_accounts_provider', 'provider_type', 'provider_id'),
        Index('idx_connected_accounts_active', 'is_active'),
        Index('idx_connected_accounts_last_used', 'last_used_at'),
    )

    def record_usage(self) -> None:
        """Record that this connected account was used for authentication."""
        self.last_used_at = datetime.utcnow()

        # Update usage statistics
        if not self.connection_count:
            self.connection_count = {"total": 0, "this_month": 0}

        self.connection_count["total"] = self.connection_count.get("total", 0) + 1

        # Reset monthly counter if needed
        current_month = datetime.utcnow().strftime("%Y-%m")
        if self.connection_count.get("current_month") != current_month:
            self.connection_count["current_month"] = current_month
            self.connection_count["this_month"] = 1
        else:
            self.connection_count["this_month"] = self.connection_count.get("this_month", 0) + 1

    def sync_profile_data(self, profile_data: Dict[str, Any]) -> None:
        """Update profile data from provider."""
        self.provider_data = profile_data
        self.display_name = profile_data.get("name") or profile_data.get("login")
        self.avatar_url = profile_data.get("avatar_url")
        self.profile_url = profile_data.get("html_url") or profile_data.get("url")
        self.provider_email = profile_data.get("email")
        self.is_verified = profile_data.get("verified", False)
        self.last_sync_at = datetime.utcnow()

    def to_dict(self, include_tokens: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "id": str(self.id),
            "provider_type": self.provider_type.value,
            "provider_id": self.provider_id,
            "provider_username": self.provider_username,
            "provider_email": self.provider_email,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "profile_url": self.profile_url,
            "is_primary": self.is_primary,
            "is_verified": self.is_verified,
            "is_active": self.is_active,
            "first_connected_at": self.first_connected_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "connection_count": self.connection_count,
            "created_at": self.created_at.isoformat(),
        }

        if include_tokens:
            result.update({
                "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
                "token_scope": self.token_scope,
                "has_access_token": bool(self.access_token_hash),
                "has_refresh_token": bool(self.refresh_token_hash),
            })

        return result


class PassKey(Base):
    """
    WebAuthn PassKey credentials for secure user verification.

    Stores PassKey (WebAuthn) credentials for users to enable secure
    two-factor authentication and transaction confirmation.
    """
    __tablename__ = "passkeys"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # WebAuthn credential data
    credential_id = Column(String(1024), nullable=False, unique=True)  # Base64url encoded
    public_key = Column(Text, nullable=False)  # COSE public key
    sign_count = Column(JSON, default={"count": 0, "last_updated": None})  # Anti-replay protection

    # Authenticator information
    authenticator_type = Column(Enum(PassKeyAuthenticatorType), nullable=False)
    aaguid = Column(String(36), nullable=True)  # Authenticator AAGUID
    transport_methods = Column(JSON, default=list)  # ["usb", "nfc", "ble", "internal"]

    # User-defined metadata
    name = Column(String(255), nullable=False)  # User-friendly name
    description = Column(String(500), nullable=True)  # Optional description
    device_info = Column(JSON, default=dict)  # Device/browser info during registration

    # Security and status
    is_active = Column(Boolean, default=True)
    is_backup_eligible = Column(Boolean, default=False)  # Can be used as backup
    is_backup_state = Column(Boolean, default=False)  # Currently in backup state

    # Usage tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(JSON, default={"total": 0, "confirmations": 0, "logins": 0})

    # Security events
    last_challenge_at = Column(DateTime, nullable=True)
    failed_attempts = Column(JSON, default=list)  # Recent failed attempts

    # Relationships
    user = relationship("User", back_populates="passkeys")

    # Indexes
    __table_args__ = (
        Index('idx_passkeys_user', 'user_id'),
        Index('idx_passkeys_credential', 'credential_id'),
        Index('idx_passkeys_active', 'is_active'),
        Index('idx_passkeys_last_used', 'last_used_at'),
        Index('idx_passkeys_type', 'authenticator_type'),
    )

    def record_successful_use(self, operation_type: str = "authentication") -> None:
        """Record successful PassKey usage."""
        self.last_used_at = datetime.utcnow()

        # Update usage counters
        if not self.usage_count:
            self.usage_count = {"total": 0, "confirmations": 0, "logins": 0}

        self.usage_count["total"] = self.usage_count.get("total", 0) + 1

        if operation_type == "confirmation":
            self.usage_count["confirmations"] = self.usage_count.get("confirmations", 0) + 1
        elif operation_type == "login":
            self.usage_count["logins"] = self.usage_count.get("logins", 0) + 1

        # Clear failed attempts on success
        self.failed_attempts = []

    def record_failed_attempt(self, challenge_id: str, error_reason: str) -> None:
        """Record failed PassKey attempt."""
        if not self.failed_attempts:
            self.failed_attempts = []

        self.failed_attempts.append({
            "timestamp": datetime.utcnow().isoformat(),
            "challenge_id": challenge_id,
            "error_reason": error_reason
        })

        # Keep only last 10 failed attempts
        if len(self.failed_attempts) > 10:
            self.failed_attempts = self.failed_attempts[-10:]

    def update_sign_count(self, new_count: int) -> bool:
        """Update sign count for anti-replay protection."""
        current_count = self.sign_count.get("count", 0)

        if new_count <= current_count:
            # Potential replay attack
            return False

        self.sign_count = {
            "count": new_count,
            "last_updated": datetime.utcnow().isoformat()
        }
        return True

    @property
    def recent_failed_attempts(self) -> int:
        """Count failed attempts in the last hour."""
        if not self.failed_attempts:
            return 0

        one_hour_ago = datetime.utcnow().timestamp() - 3600
        recent_count = 0

        for attempt in self.failed_attempts:
            attempt_time = datetime.fromisoformat(attempt["timestamp"]).timestamp()
            if attempt_time > one_hour_ago:
                recent_count += 1

        return recent_count

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "authenticator_type": self.authenticator_type.value,
            "transport_methods": self.transport_methods,
            "is_active": self.is_active,
            "is_backup_eligible": self.is_backup_eligible,
            "is_backup_state": self.is_backup_state,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
            "device_info": self.device_info,
        }

        if include_sensitive:
            result.update({
                "credential_id": self.credential_id,
                "aaguid": self.aaguid,
                "sign_count": self.sign_count,
                "last_challenge_at": self.last_challenge_at.isoformat() if self.last_challenge_at else None,
                "recent_failed_attempts": self.recent_failed_attempts,
            })

        return result


class AuthenticationSession(Base):
    """
    Active and historical authentication sessions.

    Tracks user authentication sessions across different devices and
    locations for security monitoring and session management.
    """
    __tablename__ = "authentication_sessions"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Session identification
    session_token_hash = Column(String(255), nullable=False, unique=True)  # JWT jti hash
    refresh_token_hash = Column(String(255), nullable=True)  # Refresh token hash

    # Device and location
    device_fingerprint = Column(String(255), nullable=True)  # Browser/device fingerprint
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=False)  # IPv6 max length
    location_data = Column(JSON, default=dict)  # GeoIP location data

    # Session metadata
    login_method = Column(String(50), nullable=False)  # password, oauth, passkey
    provider_type = Column(Enum(ProviderType), nullable=True)  # OAuth provider if applicable
    connected_account_id = Column(UUID(as_uuid=True), ForeignKey("connected_accounts.id"), nullable=True)
    passkey_id = Column(UUID(as_uuid=True), ForeignKey("passkeys.id"), nullable=True)

    # Timing information
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    # Session status
    is_active = Column(Boolean, default=True)
    end_reason = Column(String(50), nullable=True)  # logout, timeout, revoked, security

    # Security flags
    is_suspicious = Column(Boolean, default=False)
    security_flags = Column(JSON, default=list)  # Security concerns

    # Activity tracking
    request_count = Column(JSON, default={"total": 0, "api_calls": 0, "page_views": 0})
    activity_summary = Column(JSON, default=dict)  # Activity breakdown

    # Relationships
    user = relationship("User", back_populates="authentication_sessions")
    connected_account = relationship("ConnectedAccount")
    passkey = relationship("PassKey")

    # Indexes
    __table_args__ = (
        Index('idx_auth_sessions_user', 'user_id'),
        Index('idx_auth_sessions_token', 'session_token_hash'),
        Index('idx_auth_sessions_active', 'is_active', 'expires_at'),
        Index('idx_auth_sessions_ip', 'ip_address'),
        Index('idx_auth_sessions_device', 'device_fingerprint'),
        Index('idx_auth_sessions_created', 'created_at'),
        Index('idx_auth_sessions_last_activity', 'last_activity_at'),
        Index('idx_auth_sessions_suspicious', 'is_suspicious'),
    )

    def record_activity(self, activity_type: str = "request") -> None:
        """Record session activity."""
        self.last_activity_at = datetime.utcnow()

        if not self.request_count:
            self.request_count = {"total": 0, "api_calls": 0, "page_views": 0}

        self.request_count["total"] = self.request_count.get("total", 0) + 1

        if activity_type in ["api_calls", "page_views"]:
            self.request_count[activity_type] = self.request_count.get(activity_type, 0) + 1

    def end_session(self, reason: str = "logout") -> None:
        """End the authentication session."""
        self.is_active = False
        self.ended_at = datetime.utcnow()
        self.end_reason = reason

    def add_security_flag(self, flag: str) -> None:
        """Add a security concern flag."""
        if not self.security_flags:
            self.security_flags = []

        if flag not in self.security_flags:
            self.security_flags.append(flag)
            self.is_suspicious = True

    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def duration_minutes(self) -> Optional[int]:
        """Get session duration in minutes."""
        end_time = self.ended_at or datetime.utcnow()
        duration = end_time - self.created_at
        return int(duration.total_seconds() / 60)

    def to_dict(self, include_tokens: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "id": str(self.id),
            "device_fingerprint": self.device_fingerprint,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "location_data": self.location_data,
            "login_method": self.login_method,
            "provider_type": self.provider_type.value if self.provider_type else None,
            "created_at": self.created_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "end_reason": self.end_reason,
            "is_suspicious": self.is_suspicious,
            "security_flags": self.security_flags,
            "request_count": self.request_count,
            "duration_minutes": self.duration_minutes,
        }

        if include_tokens:
            result.update({
                "session_token_hash": self.session_token_hash,
                "has_refresh_token": bool(self.refresh_token_hash),
            })

        return result