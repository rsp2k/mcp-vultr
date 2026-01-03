"""Refresh token model for JWT authentication."""

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
import secrets
import hashlib

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# Token configuration
REFRESH_TOKEN_EXPIRE_DAYS = 30  # Refresh tokens valid for 30 days
REFRESH_TOKEN_ROTATE_AFTER_DAYS = 7  # Issue new refresh token after 7 days


class RefreshToken(Base):
    """
    Refresh token for extending user sessions without re-authentication.

    Security features:
    - Tokens are hashed before storage (like passwords)
    - Token rotation: new tokens issued after REFRESH_TOKEN_ROTATE_AFTER_DAYS
    - Device/session binding via user_agent and ip_address
    - Explicit revocation support
    - Family-based revocation for detecting token theft
    """
    __tablename__ = "refresh_tokens"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Token value (hashed for security)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)

    # Token family for rotation tracking
    # When a token is refreshed, the new token keeps the same family_id
    # If a token from the same family is used after being rotated,
    # it indicates potential token theft - revoke entire family
    family_id = Column(UUID(as_uuid=True), nullable=False, default=uuid4, index=True)

    # User association
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Session context (for security tracking)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    device_info = Column(String(255), nullable=True)  # Browser/OS fingerprint

    # Token lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    rotated_at = Column(DateTime, nullable=True)  # When this token was replaced

    # Revocation
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(100), nullable=True)  # logout, security, rotation, etc.

    # Relationship
    user = relationship("User", backref="refresh_tokens")

    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_refresh_tokens_user_id', 'user_id'),
        Index('idx_refresh_tokens_family_id', 'family_id'),
        Index('idx_refresh_tokens_expires_at', 'expires_at'),
        Index('idx_refresh_tokens_is_revoked', 'is_revoked'),
    )

    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure random token."""
        return f"vrt_{secrets.token_urlsafe(48)}"  # vrt = vultr refresh token

    @classmethod
    def hash_token(cls, token: str) -> str:
        """Hash a token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def create(
        cls,
        user_id,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
        family_id: Optional[str] = None,
        expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS
    ) -> tuple["RefreshToken", str]:
        """
        Create a new refresh token.

        Returns:
            Tuple of (RefreshToken instance, raw token string)
            The raw token must be returned to the client immediately
            as it cannot be recovered from the hash.
        """
        raw_token = cls.generate_token()
        token_hash = cls.hash_token(raw_token)

        token = cls(
            token_hash=token_hash,
            family_id=family_id or uuid4(),
            user_id=user_id,
            user_agent=user_agent[:500] if user_agent else None,
            ip_address=ip_address,
            device_info=device_info[:255] if device_info else None,
            expires_at=datetime.utcnow() + timedelta(days=expires_days)
        )

        return token, raw_token

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired, not revoked)."""
        return not self.is_expired and not self.is_revoked

    @property
    def should_rotate(self) -> bool:
        """Check if token should be rotated (for enhanced security)."""
        if not self.is_valid:
            return False

        # Rotate if token is older than REFRESH_TOKEN_ROTATE_AFTER_DAYS
        age = datetime.utcnow() - self.created_at
        return age.days >= REFRESH_TOKEN_ROTATE_AFTER_DAYS

    def revoke(self, reason: str = "manual") -> None:
        """Revoke this token."""
        self.is_revoked = True
        self.revoked_at = datetime.utcnow()
        self.revoked_reason = reason

    def record_use(self) -> None:
        """Record token usage."""
        self.last_used_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses (excluding sensitive data)."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "device_info": self.device_info,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_revoked": self.is_revoked,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoked_reason": self.revoked_reason,
            "is_valid": self.is_valid,
            "is_expired": self.is_expired
        }
