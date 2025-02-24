"""Add interior and confidence columns

Revision ID: 004
Revises: 003
Create Date: 2024-03-19 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to construction_info table
    op.add_column('construction_info', sa.Column('is_interior', sa.Boolean(), nullable=True,
                                               comment='Indicates if the first image shows interior of the property'))
    op.add_column('construction_info', sa.Column('confidence', sa.String(), nullable=True,
                                               comment='Confidence level of the AI analysis (high/medium/low)'))


def downgrade():
    # Remove the new columns
    op.drop_column('construction_info', 'is_interior')
    op.drop_column('construction_info', 'confidence') 