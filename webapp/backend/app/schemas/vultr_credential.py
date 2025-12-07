"""Pydantic schemas for Vultr credential management."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Vultr Credential Schemas
# ============================================================================

class VultrCredentialCreate(BaseModel):
    """Schema for creating a new Vultr credential."""

    label: str = Field(..., min_length=1, max_length=255, description="Human-readable label (e.g., 'Production Account')")
    description: Optional[str] = Field(None, description="Optional description of this credential's purpose")
    api_key: str = Field(..., min_length=20, description="Vultr API key to encrypt and store")

    @field_validator('label')
    @classmethod
    def validate_label(cls, v: str) -> str:
        """Validate label is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Label cannot be empty")
        return v.strip()

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Basic validation that API key looks reasonable."""
        if not v or not v.strip():
            raise ValueError("API key cannot be empty")

        # Basic format validation - Vultr API keys are typically long alphanumeric strings
        if len(v.strip()) < 20:
            raise ValueError("API key seems too short to be valid")

        return v.strip()


class VultrCredentialUpdate(BaseModel):
    """Schema for updating Vultr credential metadata."""

    label: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    api_key: Optional[str] = Field(None, min_length=20, description="New Vultr API key to encrypt and store")

    @field_validator('label')
    @classmethod
    def validate_label(cls, v: Optional[str]) -> Optional[str]:
        """Validate label if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError("Label cannot be empty")
            return v.strip()
        return v

    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Basic validation that API key looks reasonable."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError("API key cannot be empty")

            # Basic format validation - Vultr API keys are typically long alphanumeric strings
            if len(v.strip()) < 20:
                raise ValueError("API key seems too short to be valid")

            return v.strip()
        return v


class VultrCredentialResponse(BaseModel):
    """Schema for Vultr credential response (without sensitive data)."""

    id: UUID
    user_id: UUID
    label: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    created_by: str
    last_used_at: Optional[datetime] = None
    usage_count: int
    encryption_key_id: str  # Show which key was used for rotation tracking

    model_config = {"from_attributes": True}


class VultrCredentialListResponse(BaseModel):
    """Schema for paginated credential list."""

    items: list[VultrCredentialResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


# ============================================================================
# Ephemeral Token Schemas
# ============================================================================

class EphemeralTokenRequest(BaseModel):
    """Schema for requesting an ephemeral token."""

    credential_id: UUID = Field(..., description="Credential to access")
    collection_id: Optional[UUID] = Field(None, description="Optional: scope token to specific collection")
    ttl_minutes: int = Field(default=5, ge=1, le=60, description="Token time-to-live in minutes (1-60)")

    @field_validator('ttl_minutes')
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        """Enforce reasonable TTL bounds."""
        if v < 1:
            return 1
        if v > 60:
            return 60
        return v


class EphemeralTokenResponse(BaseModel):
    """Schema for ephemeral token response."""

    token: str = Field(..., description="Ephemeral token (share this with client)")
    token_id: UUID = Field(..., description="Token identifier for tracking")
    credential_id: UUID = Field(..., description="Credential this token grants access to")
    expires_at: datetime = Field(..., description="When this token expires")
    ttl_seconds: int = Field(..., description="Seconds until expiration")

    model_config = {"from_attributes": True}


class TokenExchangeRequest(BaseModel):
    """Schema for exchanging ephemeral token for real API key."""

    token: str = Field(..., min_length=10, description="Ephemeral token to exchange")
    collection_id: Optional[UUID] = Field(None, description="Collection context for RBAC validation")

    @field_validator('token')
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Validate token format."""
        if not v or not v.strip():
            raise ValueError("Token cannot be empty")

        # Tokens should start with 'ept_' prefix
        if not v.strip().startswith('ept_'):
            raise ValueError("Invalid token format")

        return v.strip()


class TokenExchangeResponse(BaseModel):
    """Schema for token exchange response (contains sensitive data!)."""

    api_key: str = Field(..., description="Decrypted Vultr API key (SENSITIVE!)")
    credential_id: UUID = Field(..., description="Credential that owns this API key")
    label: str = Field(..., description="Credential label for reference")
    expires_in_seconds: int = Field(..., description="Recommended: discard API key after this duration")

    class Config:
        json_schema_extra = {
            "example": {
                "api_key": "VULTR_API_KEY_HERE",
                "credential_id": "123e4567-e89b-12d3-a456-426614174000",
                "label": "Production Account",
                "expires_in_seconds": 300
            }
        }


# ============================================================================
# Token Validation Schema
# ============================================================================

class EphemeralTokenValidation(BaseModel):
    """Schema for token validation response."""

    is_valid: bool
    is_used: bool
    is_expired: bool
    expires_at: Optional[datetime] = None
    credential_id: Optional[UUID] = None
    user_id: Optional[UUID] = None

    model_config = {"from_attributes": True}


# ============================================================================
# Credential Statistics Schema
# ============================================================================

class CredentialStatistics(BaseModel):
    """Schema for credential usage statistics."""

    credential_id: UUID
    label: str
    total_tokens_issued: int = Field(..., description="Total ephemeral tokens ever issued")
    total_tokens_used: int = Field(..., description="Tokens that were successfully exchanged")
    total_tokens_expired: int = Field(..., description="Tokens that expired without use")
    last_token_issued_at: Optional[datetime] = None
    last_token_used_at: Optional[datetime] = None
    api_key_usage_count: int = Field(..., description="Direct API key decryptions")

    model_config = {"from_attributes": True}
