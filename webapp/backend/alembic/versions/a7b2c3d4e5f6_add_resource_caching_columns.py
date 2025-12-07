"""add_resource_caching_columns

Revision ID: a7b2c3d4e5f6
Revises: 578df18d7457
Create Date: 2025-12-06

This migration adds columns to managed_resources for:
1. vultr_credential_id - Links resource to credential used for API access
2. cached_vultr_data - Stores full Vultr API response for richer display
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = 'a7b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '578df18d7457'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add caching columns to managed_resources."""
    # Add vultr_credential_id column with foreign key
    op.add_column(
        'managed_resources',
        sa.Column('vultr_credential_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_managed_resources_vultr_credential_id',
        'managed_resources',
        'vultr_credentials',
        ['vultr_credential_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index(
        'idx_managed_resources_credential_id',
        'managed_resources',
        ['vultr_credential_id']
    )

    # Add cached_vultr_data column for storing full API responses
    op.add_column(
        'managed_resources',
        sa.Column('cached_vultr_data', JSON, nullable=True, server_default='{}')
    )


def downgrade() -> None:
    """Remove caching columns from managed_resources."""
    # Drop cached_vultr_data column
    op.drop_column('managed_resources', 'cached_vultr_data')

    # Drop vultr_credential_id column and its foreign key
    op.drop_index('idx_managed_resources_credential_id', table_name='managed_resources')
    op.drop_constraint('fk_managed_resources_vultr_credential_id', 'managed_resources', type_='foreignkey')
    op.drop_column('managed_resources', 'vultr_credential_id')
