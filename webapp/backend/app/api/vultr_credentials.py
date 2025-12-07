"""
API endpoints for Vultr credential management.

Implements secure, user-owned Vultr API key storage with:
- Fernet encryption at rest
- Ephemeral token-based access control
- RBAC permission validation
- Comprehensive audit logging
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.database import get_db
from app.middleware.rbac import require_auth
from app.models.user import User
from app.models.vultr_credential import VultrCredential, EphemeralToken
from app.models.service_collection import ServiceCollection
from app.schemas.vultr_credential import (
    VultrCredentialCreate,
    VultrCredentialUpdate,
    VultrCredentialResponse,
    VultrCredentialListResponse,
    EphemeralTokenRequest,
    EphemeralTokenResponse,
    TokenExchangeRequest,
    TokenExchangeResponse,
    EphemeralTokenValidation,
    CredentialStatistics
)
from app.core.encryption import EncryptionError, DecryptionError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/vultr-credentials", tags=["Vultr Credentials"])


# ============================================================================
# Helper Functions
# ============================================================================

async def get_user_credential(
    credential_id: UUID,
    user: User,
    db: AsyncSession
) -> VultrCredential:
    """
    Get a credential owned by the user.

    Args:
        credential_id: Credential UUID
        user: Current user
        db: Database session

    Returns:
        VultrCredential instance

    Raises:
        HTTPException: If credential not found or not owned by user
    """
    result = await db.execute(
        select(VultrCredential).where(
            and_(
                VultrCredential.id == credential_id,
                VultrCredential.user_id == user.id
            )
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        logger.warning("Credential not found or unauthorized",
                      credential_id=credential_id,
                      user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found or you don't have access"
        )

    return credential


async def validate_collection_access(
    collection_id: UUID,
    user: User,
    db: AsyncSession,
    required_operation: str = "view"
) -> ServiceCollection:
    """
    Validate user has access to a collection.

    Args:
        collection_id: Collection UUID
        user: Current user
        db: Database session
        required_operation: Required permission level

    Returns:
        ServiceCollection instance

    Raises:
        HTTPException: If collection not found or insufficient permissions
    """
    result = await db.execute(
        select(ServiceCollection).where(ServiceCollection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )

    # Check RBAC permissions
    if not collection.can_user_access(user.email, required_operation):
        logger.warning("Insufficient collection permissions",
                      collection_id=collection_id,
                      user_email=user.email,
                      required_operation=required_operation)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for '{required_operation}' on this collection"
        )

    return collection


# ============================================================================
# Credential CRUD Operations
# ============================================================================

@router.post("", response_model=VultrCredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    credential_data: VultrCredentialCreate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new Vultr API credential.

    The API key is encrypted with Fernet before storage. Only the credential
    owner can decrypt it, and then only via ephemeral token exchange.

    **Security**: API key is encrypted at rest and never returned in responses.
    """
    try:
        # Create credential model
        credential = VultrCredential(
            user_id=current_user.id,
            label=credential_data.label,
            description=credential_data.description,
            created_by=current_user.email
        )

        # Encrypt and store API key
        credential.set_api_key(credential_data.api_key)

        db.add(credential)
        await db.commit()
        await db.refresh(credential)

        logger.info("Vultr credential created",
                   credential_id=credential.id,
                   user_id=current_user.id,
                   label=credential_data.label)

        return credential

    except EncryptionError as e:
        logger.error("Failed to encrypt API key", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to encrypt API key: {str(e)}"
        )
    except Exception as e:
        logger.error("Failed to create credential", error=str(e), exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create credential: {str(e)}"
        )


@router.get("", response_model=VultrCredentialListResponse)
async def list_credentials(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_inactive: bool = Query(default=False, description="Include deactivated credentials")
):
    """
    List all Vultr credentials owned by the current user.

    **Note**: API keys are never returned in list responses. Use ephemeral
    token exchange to access the actual API keys.
    """
    # Build query
    query = select(VultrCredential).where(VultrCredential.user_id == current_user.id)

    if not include_inactive:
        query = query.where(VultrCredential.is_active == True)

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Get paginated results
    query = query.order_by(VultrCredential.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    credentials = result.scalars().all()

    logger.debug("Listed credentials",
                user_id=current_user.id,
                count=len(credentials),
                total=total)

    return VultrCredentialListResponse(
        items=credentials,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(credentials)) < total
    )


@router.get("/{credential_id}", response_model=VultrCredentialResponse)
async def get_credential(
    credential_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific Vultr credential.

    **Note**: The API key is not included in the response. Use ephemeral
    token exchange to access the actual API key.
    """
    credential = await get_user_credential(credential_id, current_user, db)
    return credential


@router.patch("/{credential_id}", response_model=VultrCredentialResponse)
async def update_credential(
    credential_id: UUID,
    credential_update: VultrCredentialUpdate,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Update Vultr credential metadata and optionally the API key.

    Can update label, description, active status, and API key.
    If API key is updated, it will be re-encrypted using the current encryption key.
    """
    credential = await get_user_credential(credential_id, current_user, db)

    # Update fields
    if credential_update.label is not None:
        credential.label = credential_update.label
    if credential_update.description is not None:
        credential.description = credential_update.description
    if credential_update.is_active is not None:
        credential.is_active = credential_update.is_active

    # Update API key if provided (re-encrypt with current encryption key)
    if credential_update.api_key is not None:
        credential.set_api_key(credential_update.api_key)
        logger.info("API key updated for credential",
                   credential_id=credential_id,
                   user_id=current_user.id)

    await db.commit()
    await db.refresh(credential)

    logger.info("Credential updated",
               credential_id=credential_id,
               user_id=current_user.id)

    return credential


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (deactivate) a Vultr credential.

    This is a soft delete - the credential is marked inactive but not removed
    from the database. This preserves audit trails and prevents breaking
    existing ephemeral tokens.
    """
    credential = await get_user_credential(credential_id, current_user, db)

    credential.deactivate()
    await db.commit()

    logger.info("Credential deleted",
               credential_id=credential_id,
               user_id=current_user.id)

    return None


# ============================================================================
# Ephemeral Token Operations
# ============================================================================

@router.post("/{credential_id}/token", response_model=EphemeralTokenResponse)
async def request_ephemeral_token(
    credential_id: UUID,
    token_request: EphemeralTokenRequest,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Request an ephemeral token for accessing a Vultr API key.

    **Token Lifecycle**:
    1. Client requests ephemeral token
    2. Token is issued with short TTL (default: 5 minutes)
    3. Client exchanges token for real API key (one-time use)
    4. Token is marked as used and cannot be reused

    **Optional Collection Scope**: If `collection_id` is provided, the token
    can only be used when the user has appropriate RBAC permissions for that
    collection.
    """
    # Verify credential exists and user owns it
    credential = await get_user_credential(credential_id, current_user, db)

    # Verify credential is active
    if not credential.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot issue token for inactive credential"
        )

    # If collection scope requested, validate access
    collection = None
    if token_request.collection_id:
        collection = await validate_collection_access(
            token_request.collection_id,
            current_user,
            db,
            required_operation="manage"  # Need manage permission to use Vultr API
        )

    # Create ephemeral token
    token_model, plain_token = EphemeralToken.create_token(
        credential_id=credential_id,
        user_id=current_user.id,
        collection_id=token_request.collection_id,
        ttl_minutes=token_request.ttl_minutes
    )

    db.add(token_model)
    await db.commit()
    await db.refresh(token_model)

    # Calculate TTL in seconds
    ttl_seconds = int((token_model.expires_at - datetime.utcnow()).total_seconds())

    logger.info("Ephemeral token issued",
               credential_id=credential_id,
               token_id=token_model.id,
               user_id=current_user.id,
               collection_id=token_request.collection_id,
               ttl_minutes=token_request.ttl_minutes)

    return EphemeralTokenResponse(
        token=plain_token,
        token_id=token_model.id,
        credential_id=credential_id,
        expires_at=token_model.expires_at,
        ttl_seconds=ttl_seconds
    )


@router.post("/exchange", response_model=TokenExchangeResponse)
async def exchange_token(
    exchange_request: TokenExchangeRequest,
    request: Request,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange an ephemeral token for the real Vultr API key.

    **SECURITY CRITICAL ENDPOINT**

    This endpoint validates:
    1. Token exists and is valid (not expired, not used)
    2. User owns the credential
    3. RBAC permissions (if collection scope was specified)
    4. Token is marked as used after successful exchange

    **One-Time Use**: Tokens can only be exchanged once.

    **Returns**: The decrypted Vultr API key (SENSITIVE!)
    """
    # Hash the token for lookup
    token_hash = EphemeralToken.hash_token(exchange_request.token)

    # Find token
    result = await db.execute(
        select(EphemeralToken)
        .where(EphemeralToken.token_hash == token_hash)
    )
    token = result.scalar_one_or_none()

    if not token:
        logger.warning("Token exchange failed - token not found",
                      user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid token"
        )

    # Validate token
    if not token.is_valid():
        logger.warning("Token exchange failed - token invalid",
                      token_id=token.id,
                      user_id=current_user.id,
                      is_used=token.is_used,
                      expires_at=token.expires_at)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token is expired or already used"
        )

    # Verify user owns the token
    if token.user_id != current_user.id:
        logger.warning("Token exchange failed - user mismatch",
                      token_id=token.id,
                      token_user_id=token.user_id,
                      current_user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not belong to you"
        )

    # If token has collection scope, validate RBAC permissions
    if token.collection_id:
        await validate_collection_access(
            token.collection_id,
            current_user,
            db,
            required_operation="manage"
        )

    # Get credential
    result = await db.execute(
        select(VultrCredential).where(VultrCredential.id == token.credential_id)
    )
    credential = result.scalar_one_or_none()

    if not credential or not credential.is_active:
        logger.warning("Token exchange failed - credential inactive or missing",
                      credential_id=token.credential_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found or inactive"
        )

    # Decrypt API key
    try:
        api_key = credential.get_api_key()
    except DecryptionError as e:
        logger.error("Token exchange failed - decryption error",
                    credential_id=credential.id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API key"
        )

    # Mark token as used
    client_ip = request.client.host if request.client else None
    token.mark_used(client_ip)

    await db.commit()

    # Calculate recommended expiry (match original token TTL)
    expires_in = int((token.expires_at - datetime.utcnow()).total_seconds())

    logger.info("Token exchanged successfully",
               token_id=token.id,
               credential_id=credential.id,
               user_id=current_user.id,
               collection_id=token.collection_id,
               client_ip=client_ip)

    return TokenExchangeResponse(
        api_key=api_key,
        credential_id=credential.id,
        label=credential.label,
        expires_in_seconds=max(expires_in, 0)
    )


# ============================================================================
# Token Management
# ============================================================================

@router.get("/tokens/validate/{token}", response_model=EphemeralTokenValidation)
async def validate_token(
    token: str,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate an ephemeral token without exchanging it.

    Useful for checking token status before attempting exchange.
    """
    token_hash = EphemeralToken.hash_token(token)

    result = await db.execute(
        select(EphemeralToken).where(EphemeralToken.token_hash == token_hash)
    )
    token_model = result.scalar_one_or_none()

    if not token_model:
        return EphemeralTokenValidation(
            is_valid=False,
            is_used=False,
            is_expired=False
        )

    # Check ownership
    if token_model.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not belong to you"
        )

    is_expired = datetime.utcnow() > token_model.expires_at

    return EphemeralTokenValidation(
        is_valid=token_model.is_valid(),
        is_used=token_model.is_used,
        is_expired=is_expired,
        expires_at=token_model.expires_at,
        credential_id=token_model.credential_id,
        user_id=token_model.user_id
    )


# ============================================================================
# Statistics & Monitoring
# ============================================================================

@router.get("/{credential_id}/statistics", response_model=CredentialStatistics)
async def get_credential_statistics(
    credential_id: UUID,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Get usage statistics for a credential.

    Shows how many tokens have been issued and used.
    """
    credential = await get_user_credential(credential_id, current_user, db)

    # Count tokens
    total_tokens_result = await db.execute(
        select(func.count())
        .select_from(EphemeralToken)
        .where(EphemeralToken.credential_id == credential_id)
    )
    total_tokens = total_tokens_result.scalar()

    used_tokens_result = await db.execute(
        select(func.count())
        .select_from(EphemeralToken)
        .where(
            and_(
                EphemeralToken.credential_id == credential_id,
                EphemeralToken.is_used == True
            )
        )
    )
    used_tokens = used_tokens_result.scalar()

    expired_tokens_result = await db.execute(
        select(func.count())
        .select_from(EphemeralToken)
        .where(
            and_(
                EphemeralToken.credential_id == credential_id,
                EphemeralToken.is_used == False,
                EphemeralToken.expires_at < datetime.utcnow()
            )
        )
    )
    expired_tokens = expired_tokens_result.scalar()

    # Get last token times
    last_issued_result = await db.execute(
        select(EphemeralToken.created_at)
        .where(EphemeralToken.credential_id == credential_id)
        .order_by(EphemeralToken.created_at.desc())
        .limit(1)
    )
    last_issued = last_issued_result.scalar_one_or_none()

    last_used_result = await db.execute(
        select(EphemeralToken.used_at)
        .where(
            and_(
                EphemeralToken.credential_id == credential_id,
                EphemeralToken.used_at.isnot(None)
            )
        )
        .order_by(EphemeralToken.used_at.desc())
        .limit(1)
    )
    last_used = last_used_result.scalar_one_or_none()

    return CredentialStatistics(
        credential_id=credential_id,
        label=credential.label,
        total_tokens_issued=total_tokens,
        total_tokens_used=used_tokens,
        total_tokens_expired=expired_tokens,
        last_token_issued_at=last_issued,
        last_token_used_at=last_used,
        api_key_usage_count=credential.usage_count
    )
