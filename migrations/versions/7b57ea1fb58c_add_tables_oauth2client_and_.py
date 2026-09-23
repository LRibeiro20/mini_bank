"""add tables oauth2client and authorizationCode

Revision ID: 7b57ea1fb58c
Revises: b9cf913d1bb3
Create Date: 2026-09-21 16:02:03.353389

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7b57ea1fb58c'
down_revision: Union[str, None] = 'b9cf913d1bb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create the oauth2_clients and authorization_codes tables.

    Order matters:
      1. oauth2_clients first — authorization_codes has a FK pointing to it.
      2. authorization_codes second — references oauth2_clients.client_id.
    """
    op.create_table(
        'oauth2_clients',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.VARCHAR(length=100), nullable=False),
        sa.Column('client_secret', sa.VARCHAR(length=255), nullable=True),
        sa.Column('client_name', sa.VARCHAR(length=100), nullable=False),
        sa.Column('redirect_uris', sa.VARCHAR(length=1000), nullable=False),
        sa.Column('is_active', sa.BOOLEAN(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='oauth2_clients_pkey'),
    )
    # Unique index on client_id — used as the FK target by authorization_codes.
    op.create_index('ix_oauth2_clients_client_id', 'oauth2_clients', ['client_id'], unique=True)

    op.create_table(
        'authorization_codes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('code', sa.VARCHAR(length=100), nullable=False),
        sa.Column('client_id', sa.VARCHAR(length=100), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('redirect_uri', sa.VARCHAR(length=255), nullable=False),
        sa.Column('code_challenge', sa.VARCHAR(length=255), nullable=False),
        sa.Column('code_challenge_method', sa.VARCHAR(length=50), nullable=False),
        sa.Column('expires_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False),
        # FK to oauth2_clients.client_id (the indexed column, not the PK)
        sa.ForeignKeyConstraint(['client_id'], ['oauth2_clients.client_id'], name='authorization_codes_client_id_fkey'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='authorization_codes_user_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='authorization_codes_pkey'),
    )
    op.create_index('ix_authorization_codes_code', 'authorization_codes', ['code'], unique=True)


def downgrade() -> None:
    """
    Drop authorization_codes before oauth2_clients — FK dependency requires this order.
    Drop the FK-dependent table first, then its index, then the parent table.
    """
    # 1. Drop the child table first (it references oauth2_clients)
    op.drop_index('ix_authorization_codes_code', table_name='authorization_codes')
    op.drop_table('authorization_codes')

    # 2. Now safe to drop the index and parent table
    op.drop_index('ix_oauth2_clients_client_id', table_name='oauth2_clients')
    op.drop_table('oauth2_clients')
