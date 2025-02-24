import os
from openai import OpenAI
import psycopg2
from dotenv import load_dotenv
import time
from typing import Tuple

# Load environment variables
load_dotenv()

# Configuration
DB_URL = os.getenv('DATABASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_image(image_url: str) -> Tuple[bool, bool]:
    """
    Analyze a property image using OpenAI's Vision API to determine if it's renovated and furnished.
    Returns a tuple of (is_renovated, is_furnished)
    """
    try:
        print(f"Analyzing image URL: {image_url}")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this property image and determine:
1. Is it renovated? Look for signs of recent renovation like modern finishes, new paint, updated fixtures.
   Exclude furniture from this assessment.
2. Is it furnished? Look for presence of furniture, appliances, and decor.

Respond in this exact format:
RENOVATED: true/false
FURNISHED: true/false
CONFIDENCE: high/medium/low"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],
            max_tokens=100
        )

        # Parse the response
        result = response.choices[0].message.content
        lines = result.strip().split('\n')
        
        is_renovated = False
        is_furnished = False
        confidence = 'low'
        
        for line in lines:
            if line.startswith('RENOVATED:'):
                is_renovated = 'true' in line.lower()
            elif line.startswith('FURNISHED:'):
                is_furnished = 'true' in line.lower()
            elif line.startswith('CONFIDENCE:'):
                confidence = line.split(':')[1].strip().lower()
        
        print(f"Analysis result: renovated={is_renovated}, furnished={is_furnished}, confidence={confidence}")
        
        # Only return results if confidence is medium or high
        if confidence == 'low':
            return None, None
            
        return is_renovated, is_furnished
        
    except Exception as e:
        print(f"Error analyzing image {image_url}: {str(e)}")
        return None, None

def get_properties_to_analyze():
    """Get properties that haven't been analyzed yet"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            WITH FirstImages AS (
                SELECT property_id, url
                FROM (
                    SELECT property_id, url,
                           ROW_NUMBER() OVER (PARTITION BY property_id ORDER BY position) as rn
                    FROM images
                ) ranked
                WHERE rn = 1
            )
            SELECT p.id, i.url
            FROM properties p
            LEFT JOIN construction_info ci ON ci.property_id = p.id
            JOIN FirstImages i ON i.property_id = p.id
            WHERE (ci.is_renovated IS NULL 
               OR ci.is_furnished IS NULL
               OR ci.property_id IS NULL)
            AND p.id != 'metadata'
            ORDER BY p.id
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def update_property_analysis(property_id: str, is_renovated: bool, is_furnished: bool):
    """Update the property with analysis results"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # First ensure the construction_info record exists
        cur.execute("""
            INSERT INTO construction_info (property_id)
            VALUES (%s)
            ON CONFLICT (property_id) DO NOTHING
        """, (property_id,))
        
        # Then update the analysis results
        cur.execute("""
            UPDATE construction_info
            SET is_renovated = %s,
                is_furnished = %s
            WHERE property_id = %s
        """, (is_renovated, is_furnished, property_id))
        conn.commit()
        print(f"Updated property {property_id}: renovated={is_renovated}, furnished={is_furnished}")
    except Exception as e:
        print(f"Error updating property {property_id}: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def main():
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return
        
    print("Starting property analysis...")
    properties = get_properties_to_analyze()
    print(f"Found {len(properties)} properties to analyze")
    
    for property_id, image_url in properties:
        print(f"\nAnalyzing property {property_id}")
        print(f"Image URL: {image_url}")
        is_renovated, is_furnished = analyze_image(image_url)
        
        if is_renovated is not None and is_furnished is not None:
            update_property_analysis(property_id, is_renovated, is_furnished)
        else:
            print(f"Skipping property {property_id} due to low confidence or error")
            
        # Sleep to respect rate limits
        time.sleep(1)
    
    print("\nAnalysis completed!")

if __name__ == "__main__":
    main() 