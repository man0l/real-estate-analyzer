"""Add property details columns

Revision ID: 003
Revises: 002
Create Date: 2024-03-19 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to construction_info table
    op.add_column('construction_info', sa.Column('is_renovated', sa.Boolean(), nullable=True,
                                               comment='Indicates if the property has been renovated (excluding furniture)'))
    op.add_column('construction_info', sa.Column('is_furnished', sa.Boolean(), nullable=True,
                                               comment='Indicates if the property comes with furniture'))
    op.add_column('construction_info', sa.Column('has_act16', sa.Boolean(), nullable=True,
                                               comment='Indicates if the building has Act 16 (completion certificate)'))


def downgrade():
    # Remove the new columns
    op.drop_column('construction_info', 'is_renovated')
    op.drop_column('construction_info', 'is_furnished')
    op.drop_column('construction_info', 'has_act16') 