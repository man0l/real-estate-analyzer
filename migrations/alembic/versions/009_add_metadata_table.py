"""Add metadata table

Revision ID: 009
Revises: 008
Create Date: 2024-02-24 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None

def upgrade():
    # Create metadata table
    op.create_table(
        'metadata',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', JSONB, nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('key')
    )

    # Check if data column exists before trying to drop it
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [col['name'] for col in inspector.get_columns('properties')]
    if 'data' in columns:
        op.drop_column('properties', 'data')

def downgrade():
    # Add back the data column to properties table
    op.add_column('properties',
        sa.Column('data', JSONB, nullable=True)
    )
    
    # Drop metadata table
    op.drop_table('metadata') 