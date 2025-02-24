import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
supabase_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
supabase: Client = create_client(supabase_url, supabase_key)

def main():
    try:
        # List all buckets
        buckets = supabase.storage.list_buckets()
        print("Existing buckets:", [b.name for b in buckets])
        
        # Check if properties bucket exists
        properties_bucket_exists = any(b.name == 'properties' for b in buckets)
        
        if not properties_bucket_exists:
            print("Creating 'properties' bucket...")
            result = supabase.storage.create_bucket(
                'properties',
                options={'public': True}  # Make the bucket public
            )
            print("Bucket created successfully!")
        else:
            print("'properties' bucket already exists")
            
        # Update bucket to be public if it exists
        if properties_bucket_exists:
            result = supabase.storage.update_bucket(
                'properties',
                options={'public': True}
            )
            print("Updated 'properties' bucket to be public")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 