"""Add url_history table

Revision ID: 011
Revises: 010
Create Date: 2024-02-25 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None

def upgrade():
    # Create url_history table
    op.execute("""
        CREATE TABLE url_history (
            id SERIAL PRIMARY KEY,
            property_id VARCHAR NOT NULL,
            old_url TEXT NOT NULL,
            new_url TEXT NOT NULL,
            changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
        );
        
        -- Create index for faster lookups
        CREATE INDEX idx_url_history_property_id ON url_history(property_id);
        CREATE INDEX idx_url_history_changed_at ON url_history(changed_at);
    """)

def downgrade():
    # Drop url_history table and its indexes
    op.execute("""
        DROP TABLE IF EXISTS url_history CASCADE;
    """) 