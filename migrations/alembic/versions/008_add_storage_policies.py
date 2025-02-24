"""Add storage policies

Revision ID: 008
Revises: 007
Create Date: 2024-03-19 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Create storage policies
    op.execute("""
        -- Enable RLS for storage.objects
        ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

        -- Drop existing policies if they exist
        DROP POLICY IF EXISTS "Enable read access for all users" ON storage.objects;
        DROP POLICY IF EXISTS "Enable insert access for all users" ON storage.objects;
        DROP POLICY IF EXISTS "Enable update access for all users" ON storage.objects;
        DROP POLICY IF EXISTS "Enable delete access for all users" ON storage.objects;

        -- Create policies for the properties bucket
        CREATE POLICY "Enable read access for all users"
        ON storage.objects FOR SELECT
        USING (bucket_id = 'properties');

        CREATE POLICY "Enable insert access for all users"
        ON storage.objects FOR INSERT
        WITH CHECK (bucket_id = 'properties');

        CREATE POLICY "Enable update access for all users"
        ON storage.objects FOR UPDATE
        USING (bucket_id = 'properties')
        WITH CHECK (bucket_id = 'properties');

        CREATE POLICY "Enable delete access for all users"
        ON storage.objects FOR DELETE
        USING (bucket_id = 'properties');

        -- Grant access to authenticated and anon users
        GRANT ALL ON storage.objects TO authenticated, anon;
        GRANT ALL ON storage.buckets TO authenticated, anon;
    """)


def downgrade():
    # Remove storage policies
    op.execute("""
        -- Drop policies
        DROP POLICY IF EXISTS "Enable read access for all users" ON storage.objects;
        DROP POLICY IF EXISTS "Enable insert access for all users" ON storage.objects;
        DROP POLICY IF EXISTS "Enable update access for all users" ON storage.objects;
        DROP POLICY IF EXISTS "Enable delete access for all users" ON storage.objects;

        -- Revoke access
        REVOKE ALL ON storage.objects FROM authenticated, anon;
        REVOKE ALL ON storage.buckets FROM authenticated, anon;

        -- Disable RLS
        ALTER TABLE storage.objects DISABLE ROW LEVEL SECURITY;
    """) 