"""
Database models for Vultr credential management.

This module implements secure, user-owned Vultr API credential storage
with Fernet encryption and ephemeral token-based access control.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4, UUID
import secrets

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
import structlog

from app.core.database import Base
from app.core.encryption import encrypt_value, decrypt_value, DecryptionError

logger = structlog.get_logger(__name__)


class VultrCredential(Base):
    """
    User-owned Vultr API credentials with Fernet encryption.

    Each user can store multiple Vultr API keys (e.g., for different accounts,
    environments, or purposes). Keys are encrypted at rest using Fernet symmetric
    encryption with support for key rotation.

    Access to credentials is controlled via ephemeral tokens and RBAC permissions.
    """

    __tablename__ = "vultr_credentials"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Owner
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Human-readable identifier
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Encrypted API key
    encrypted_api_key = Column(Text, nullable=False)  # Fernet-encrypted Vultr API key
    encryption_key_id = Column(String(50), nullable=False, default="default")  # For key rotation

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=False)  # Email of creator
    last_used_at = Column(DateTime, nullable=True)  # When credential was last used via token exchange
    usage_count = Column(Integer, default=0, nullable=False)  # Track how many times it's been used

    # Relationships
    owner = relationship("User", back_populates="vultr_credentials")
    ephemeral_tokens = relationship("EphemeralToken", back_populates="credential", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<VultrCredential {self.label} (owner={self.created_by})>"

    def set_api_key(self, api_key: str, key_id: str = "default") -> None:
        """
        Encrypt and store a Vultr API key.

        Args:
            api_key: Plain text Vultr API key
            key_id: Encryption key identifier for key rotation support
        """
        encrypted, key_id_used = encrypt_value(api_key, key_id)
        self.encrypted_api_key = encrypted
        self.encryption_key_id = key_id_used
        logger.info("API key encrypted and stored", credential_id=self.id, key_id=key_id_used)

    def get_api_key(self) -> str:
        """
        Decrypt and return the Vultr API key.

        Returns:
            Plain text Vultr API key

        Raises:
            DecryptionError: If decryption fails
        """
        try:
            api_key = decrypt_value(self.encrypted_api_key, self.encryption_key_id)
            # Update usage tracking
            self.last_used_at = datetime.utcnow()
            self.usage_count += 1
            logger.debug("API key decrypted", credential_id=self.id, usage_count=self.usage_count)
            return api_key
        except DecryptionError as e:
            logger.error("Failed to decrypt API key",
                        credential_id=self.id,
                        encryption_key_id=self.encryption_key_id,
                        error=str(e))
            raise

    def rotate_encryption_key(self, new_key_id: str = "default") -> None:
        """
        Rotate to a new encryption key.

        This re-encrypts the API key with a new Fernet key, useful for
        periodic key rotation or security incidents.

        Args:
            new_key_id: New encryption key identifier
        """
        from app.core.encryption import rotate_encryption

        old_key_id = self.encryption_key_id
        new_encrypted, new_key_id = rotate_encryption(
            self.encrypted_api_key,
            old_key_id,
            new_key_id
        )

        self.encrypted_api_key = new_encrypted
        self.encryption_key_id = new_key_id

        logger.info("Encryption key rotated",
                   credential_id=self.id,
                   old_key_id=old_key_id,
                   new_key_id=new_key_id)

    def deactivate(self) -> None:
        """Soft delete - deactivate the credential."""
        self.is_active = False
        logger.info("Credential deactivated", credential_id=self.id)

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert to dictionary representation.

        Args:
            include_sensitive: If True, includes the decrypted API key (dangerous!)

        Returns:
            Dictionary representation
        """
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "label": self.label,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
        }

        if include_sensitive:
            # WARNING: Only use this for authorized API key retrieval
            try:
                data["api_key"] = self.get_api_key()
            except DecryptionError:
                data["api_key"] = None
                data["decryption_error"] = True

        return data


class EphemeralToken(Base):
    """
    Short-lived tokens for RBAC-controlled credential access.

    Instead of directly accessing Vultr API keys, clients request ephemeral
    tokens that grant time-limited access to specific credentials. The API
    validates RBAC permissions before exchanging tokens for real API keys.

    This architecture provides:
    - Audit trail of credential access
    - Time-limited credential exposure
    - RBAC-based access control
    - Ability to revoke tokens
    """

    __tablename__ = "ephemeral_tokens"

    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Token value (hashed for security)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)

    # Associated credential
    credential_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("vultr_credentials.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Requester
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Optional scope: limit token to specific collection
    collection_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("service_collections.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Time constraints
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    # Usage tracking
    is_used = Column(Boolean, default=False, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    used_from_ip = Column(String(45), nullable=True)  # IPv4 or IPv6

    # Relationships
    credential = relationship("VultrCredential", back_populates="ephemeral_tokens")
    user = relationship("User")
    collection = relationship("ServiceCollection")

    def __repr__(self) -> str:
        return f"<EphemeralToken {self.id} (credential={self.credential_id}, expires={self.expires_at})>"

    @staticmethod
    def generate_token() -> str:
        """
        Generate a cryptographically secure random token.

        Returns:
            URL-safe token string
        """
        return f"ept_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_token(token: str) -> str:
        """
        Hash a token for secure storage.

        We hash tokens to prevent database compromise from exposing valid tokens.

        Args:
            token: Plain text token

        Returns:
            Hashed token
        """
        import hashlib
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    @classmethod
    def create_token(
        cls,
        credential_id: UUID,
        user_id: UUID,
        collection_id: Optional[UUID] = None,
        ttl_minutes: int = 5
    ) -> tuple["EphemeralToken", str]:
        """
        Create a new ephemeral token.

        Args:
            credential_id: Credential to grant access to
            user_id: User requesting access
            collection_id: Optional collection scope
            ttl_minutes: Time-to-live in minutes (default: 5)

        Returns:
            Tuple of (token_model, plain_text_token)
        """
        # Generate token
        plain_token = cls.generate_token()
        token_hash = cls.hash_token(plain_token)

        # Create model
        token = cls(
            token_hash=token_hash,
            credential_id=credential_id,
            user_id=user_id,
            collection_id=collection_id,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes)
        )

        logger.info("Ephemeral token created",
                   credential_id=credential_id,
                   user_id=user_id,
                   collection_id=collection_id,
                   ttl_minutes=ttl_minutes)

        return token, plain_token

    def is_valid(self) -> bool:
        """
        Check if token is still valid.

        Returns:
            True if token can be used, False otherwise
        """
        if self.is_used:
            logger.debug("Token already used", token_id=self.id)
            return False

        if datetime.utcnow() > self.expires_at:
            logger.debug("Token expired", token_id=self.id, expires_at=self.expires_at)
            return False

        return True

    def mark_used(self, ip_address: Optional[str] = None) -> None:
        """
        Mark token as used.

        Args:
            ip_address: IP address the token was used from
        """
        self.is_used = True
        self.used_at = datetime.utcnow()
        self.used_from_ip = ip_address
        logger.info("Token marked as used",
                   token_id=self.id,
                   credential_id=self.credential_id,
                   ip_address=ip_address)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "credential_id": str(self.credential_id),
            "user_id": str(self.user_id),
            "collection_id": str(self.collection_id) if self.collection_id else None,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "is_used": self.is_used,
            "used_at": self.used_at.isoformat() if self.used_at else None,
            "is_valid": self.is_valid(),
        }
