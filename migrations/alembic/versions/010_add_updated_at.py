"""Add updated_at column to properties

Revision ID: 010
Revises: 009
Create Date: 2024-02-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None

def upgrade():
    # Add updated_at column
    op.execute("""
        ALTER TABLE properties 
        ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    """)
    
    # Update existing rows to have updated_at same as created_at
    op.execute("""
        UPDATE properties 
        SET updated_at = created_at 
        WHERE updated_at IS NULL;
    """)
    
    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER update_properties_updated_at
            BEFORE UPDATE ON properties
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)

def downgrade():
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_properties_updated_at ON properties;")
    
    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Drop column
    op.execute("ALTER TABLE properties DROP COLUMN IF EXISTS updated_at;") 