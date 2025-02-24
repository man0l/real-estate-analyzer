"""Add is_private_seller column

Revision ID: 002
Revises: 001
Create Date: 2024-03-19 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Add is_private_seller column to properties table
    op.add_column('properties', sa.Column('is_private_seller', sa.Boolean(), nullable=True))


def downgrade():
    # Remove is_private_seller column from properties table
    op.drop_column('properties', 'is_private_seller') 