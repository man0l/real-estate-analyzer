import os
import requests
from supabase import create_client, Client
from urllib.parse import urlparse
import hashlib
from typing import Optional
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client with error handling
supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
supabase_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')

if not supabase_url or not supabase_key:
    raise ValueError("Missing required environment variables: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set")

print(f"Initializing Supabase client with URL: {supabase_url}")
supabase: Client = create_client(supabase_url, supabase_key)

def get_image_hash(url: str) -> str:
    """Generate a unique hash for the image URL"""
    return hashlib.md5(url.encode()).hexdigest()

def download_image(url: str) -> Optional[bytes]:
    """Download image from URL"""
    try:
        print(f"Downloading image from {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print(f"Successfully downloaded {len(response.content)} bytes")
        return response.content
    except Exception as e:
        print(f"Error downloading image {url}: {str(e)}")
        traceback.print_exc()
        return None

def get_file_extension(url: str) -> str:
    """Get file extension from URL"""
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    return ext if ext else '.jpg'  # Default to .jpg if no extension found

def upload_to_supabase(image_data: bytes, property_id: str, image_url: str) -> Optional[str]:
    """Upload image to Supabase Storage and return the public URL"""
    try:
        # Generate a unique filename using property ID and image hash
        image_hash = get_image_hash(image_url)
        ext = get_file_extension(image_url)
        filename = f"{property_id}/{image_hash}{ext}"
        print(f"Generated filename: {filename}")

        try:
            # Check if file exists
            print(f"Checking if file exists: {filename}")
            supabase.storage.from_('properties').download(filename)
            print(f"File exists, returning public URL")
            return supabase.storage.from_('properties').get_public_url(filename)
        except Exception as e:
            print(f"File doesn't exist (expected): {str(e)}")
            # File doesn't exist, proceed with upload
            pass

        # Upload to 'properties' bucket
        print(f"Uploading file to Supabase Storage: {filename}")
        result = supabase.storage.from_('properties').upload(
            path=filename,
            file=image_data,
            file_options={"content-type": f"image/{ext[1:]}"}
        )
        print(f"Upload result: {result}")

        # Get public URL
        public_url = supabase.storage.from_('properties').get_public_url(filename)
        print(f"Generated public URL: {public_url}")
        return public_url
    except Exception as e:
        print(f"Error uploading to Supabase: {str(e)}")
        traceback.print_exc()
        return None

def process_property_image(property_id: str, image_url: str) -> Optional[str]:
    """Download an image and upload it to Supabase Storage"""
    try:
        print(f"\nProcessing image for property {property_id}")
        print(f"Image URL: {image_url}")

        # Download the image
        image_data = download_image(image_url)
        if not image_data:
            print("Failed to download image")
            return None

        # Upload to Supabase Storage
        storage_url = upload_to_supabase(image_data, property_id, image_url)
        if not storage_url:
            print("Failed to upload image to Supabase Storage")
            return None

        print(f"Successfully processed image: {storage_url}")
        return storage_url

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        traceback.print_exc()
        return None 