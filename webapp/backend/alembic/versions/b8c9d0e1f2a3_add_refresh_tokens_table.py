"""add_refresh_tokens_table

Revision ID: b8c9d0e1f2a3
Revises: a7b2c3d4e5f6
Create Date: 2025-12-08

This migration adds the refresh_tokens table for JWT token refresh functionality.
Features:
- Secure token storage (hashed, not plain text)
- Token family tracking for rotation security
- Session context (user agent, IP) for security monitoring
- Revocation support with reason tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create refresh_tokens table."""
    op.create_table(
        'refresh_tokens',
        # Primary identification
        sa.Column('id', UUID(as_uuid=True), primary_key=True),

        # Token value (hashed for security)
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),

        # Token family for rotation tracking
        sa.Column('family_id', UUID(as_uuid=True), nullable=False),

        # User association
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),

        # Session context
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv6 max length
        sa.Column('device_info', sa.String(255), nullable=True),

        # Token lifecycle
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('rotated_at', sa.DateTime(), nullable=True),

        # Revocation
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_reason', sa.String(100), nullable=True),
    )

    # Create indexes for efficient queries
    op.create_index('idx_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'], unique=True)
    op.create_index('idx_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('idx_refresh_tokens_family_id', 'refresh_tokens', ['family_id'])
    op.create_index('idx_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])
    op.create_index('idx_refresh_tokens_is_revoked', 'refresh_tokens', ['is_revoked'])


def downgrade() -> None:
    """Drop refresh_tokens table."""
    op.drop_index('idx_refresh_tokens_is_revoked', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_expires_at', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_family_id', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_token_hash', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
