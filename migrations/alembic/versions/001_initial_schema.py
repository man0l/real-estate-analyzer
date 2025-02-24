"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-03-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing tables if they exist
    op.execute('DROP TABLE IF EXISTS images CASCADE')
    op.execute('DROP TABLE IF EXISTS features CASCADE')
    op.execute('DROP TABLE IF EXISTS monthly_payments CASCADE')
    op.execute('DROP TABLE IF EXISTS contact_info CASCADE')
    op.execute('DROP TABLE IF EXISTS construction_info CASCADE')
    op.execute('DROP TABLE IF EXISTS floor_info CASCADE')
    op.execute('DROP TABLE IF EXISTS locations CASCADE')
    op.execute('DROP TABLE IF EXISTS properties CASCADE')

    # Create tables
    op.create_table(
        'properties',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('price_value', sa.Numeric(), nullable=True),
        sa.Column('price_currency', sa.String(), nullable=True),
        sa.Column('includes_vat', sa.Boolean(), nullable=True),
        sa.Column('area_m2', sa.Integer(), nullable=True),
        sa.Column('views', sa.Integer(), nullable=True),
        sa.Column('last_modified', sa.String(), nullable=True),
        sa.Column('image_count', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_private_seller', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'locations',
        sa.Column('property_id', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('district', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('property_id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE')
    )

    op.create_table(
        'floor_info',
        sa.Column('property_id', sa.String(), nullable=False),
        sa.Column('current_floor', sa.Integer(), nullable=True),
        sa.Column('total_floors', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('property_id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE')
    )

    op.create_table(
        'construction_info',
        sa.Column('property_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('has_central_heating', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('property_id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE')
    )

    op.create_table(
        'contact_info',
        sa.Column('property_id', sa.String(), nullable=False),
        sa.Column('broker_name', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('property_id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE')
    )

    op.create_table(
        'monthly_payments',
        sa.Column('property_id', sa.String(), nullable=False),
        sa.Column('value', sa.Numeric(), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('property_id'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE')
    )

    op.create_table(
        'features',
        sa.Column('property_id', sa.String(), nullable=False),
        sa.Column('feature', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('property_id', 'feature'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE')
    )

    op.create_table(
        'images',
        sa.Column('property_id', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('property_id', 'url'),
        sa.ForeignKeyConstraint(['property_id'], ['properties.id'], ondelete='CASCADE')
    )


def downgrade():
    op.drop_table('images')
    op.drop_table('features')
    op.drop_table('monthly_payments')
    op.drop_table('contact_info')
    op.drop_table('construction_info')
    op.drop_table('floor_info')
    op.drop_table('locations')
    op.drop_table('properties') 