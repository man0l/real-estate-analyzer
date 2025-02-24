"""Add act16 plan date

Revision ID: 005
Revises: 004
Create Date: 2024-03-19 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Add new column to construction_info table
    op.add_column('construction_info', sa.Column('act16_plan_date', sa.Date(), nullable=True,
                                               comment='Planned date for receiving Act 16'))


def downgrade():
    # Remove the new column
    op.drop_column('construction_info', 'act16_plan_date') 