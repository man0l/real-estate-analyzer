"""Add act16 details

Revision ID: 006
Revises: 005
Create Date: 2024-03-19 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Add new column to construction_info table
    op.add_column('construction_info', sa.Column('act16_details', sa.Text(), nullable=True,
                                               comment='Detailed explanation of the building completion status'))


def downgrade():
    # Remove the new column
    op.drop_column('construction_info', 'act16_details') 