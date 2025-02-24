"""Add storage_url to images table

Revision ID: 007
Revises: 006
Create Date: 2024-03-19 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # Add storage_url column to images table
    op.add_column('images', sa.Column('storage_url', sa.String(), nullable=True))
    
    # Create index for faster lookups
    op.create_index('idx_images_storage_url', 'images', ['storage_url'])


def downgrade():
    # Remove index
    op.drop_index('idx_images_storage_url')
    
    # Remove storage_url column
    op.drop_column('images', 'storage_url') 