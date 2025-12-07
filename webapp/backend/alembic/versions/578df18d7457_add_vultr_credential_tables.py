"""add_vultr_credential_tables

Revision ID: 578df18d7457
Revises: e3d1ec6b7c6a
Create Date: 2025-10-06 21:50:44.998428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '578df18d7457'
down_revision: Union[str, Sequence[str], None] = 'e3d1ec6b7c6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create vultr_credentials table
    op.create_table(
        'vultr_credentials',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('encrypted_api_key', sa.Text(), nullable=False),
        sa.Column('encryption_key_id', sa.String(length=50), nullable=False, server_default='default'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', sa.String(length=255), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_vultr_credentials_user_id', 'vultr_credentials', ['user_id'])
    op.create_index('ix_vultr_credentials_is_active', 'vultr_credentials', ['is_active'])

    # Create ephemeral_tokens table
    op.create_table(
        'ephemeral_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('credential_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('collection_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('used_from_ip', sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(['credential_id'], ['vultr_credentials.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['collection_id'], ['service_collections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ephemeral_tokens_token_hash', 'ephemeral_tokens', ['token_hash'], unique=True)
    op.create_index('ix_ephemeral_tokens_credential_id', 'ephemeral_tokens', ['credential_id'])
    op.create_index('ix_ephemeral_tokens_user_id', 'ephemeral_tokens', ['user_id'])
    op.create_index('ix_ephemeral_tokens_collection_id', 'ephemeral_tokens', ['collection_id'])
    op.create_index('ix_ephemeral_tokens_expires_at', 'ephemeral_tokens', ['expires_at'])
    op.create_index('ix_ephemeral_tokens_is_used', 'ephemeral_tokens', ['is_used'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_index('ix_ephemeral_tokens_is_used', table_name='ephemeral_tokens')
    op.drop_index('ix_ephemeral_tokens_expires_at', table_name='ephemeral_tokens')
    op.drop_index('ix_ephemeral_tokens_collection_id', table_name='ephemeral_tokens')
    op.drop_index('ix_ephemeral_tokens_user_id', table_name='ephemeral_tokens')
    op.drop_index('ix_ephemeral_tokens_credential_id', table_name='ephemeral_tokens')
    op.drop_index('ix_ephemeral_tokens_token_hash', table_name='ephemeral_tokens')
    op.drop_table('ephemeral_tokens')

    op.drop_index('ix_vultr_credentials_is_active', table_name='vultr_credentials')
    op.drop_index('ix_vultr_credentials_user_id', table_name='vultr_credentials')
    op.drop_table('vultr_credentials')
