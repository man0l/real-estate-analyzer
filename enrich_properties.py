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
OPENAI_VISION_API_KEY = os.getenv('OPENAI_VISION_API_KEY')
OPENAI_VISION_BASE_URL = os.getenv('OPENAI_VISION_BASE_URL')

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_VISION_API_KEY, base_url=OPENAI_VISION_BASE_URL)
model = "qwen/qwen-vl-plus:free" # "gpt-4o-mini"


def analyze_image(image_url: str) -> Tuple[bool, bool, bool, str]:
    """
    Analyze a property image using OpenAI's Vision API to determine if it's renovated and furnished.
    Returns a tuple of (is_renovated, is_furnished, is_interior, confidence)
    """
    try:
        print(f"Analyzing image URL: {image_url}")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """First, determine if this image shows the interior of an apartment/flat:
1. Is this an interior shot (showing actual rooms inside the property)?
   Answer NO if the image shows:
   - Building exterior, facade, or surroundings
   - Architectural floor plans or drawings
   - Construction plans or sketches
   - Any type of 2D layout or blueprint
   - Stairs, corridors, or other non-interior spaces
   
   Answer YES only if it shows actual photographs of interior rooms (living room, bedroom, kitchen, etc)

If it IS an interior photograph, then carefully analyze:

2. Is it renovated? Look for ANY of these signs of unfinished work or needed renovation:
   - Exposed bricks or concrete
   - Missing or unfinished doors/windows
   - Rough/unfinished plaster
   - Missing paint or bare walls
   - Exposed pipes or wiring
   - Unfinished flooring
   - Construction debris
   - Missing bathroom fixtures
   - Missing kitchen elements
   If ANY of these are visible, mark as NOT renovated, even if parts of the room look finished.
   Only mark as renovated if the space is COMPLETELY finished with no visible construction work needed.

3. Is it furnished? Look for:
   - Furniture (beds, sofas, tables, chairs)
   - Major appliances (fridge, stove, washing machine)
   - Decor items
   Must have multiple pieces of furniture to be considered furnished.

Respond in this exact format:
INTERIOR: yes/no
[Only if INTERIOR is yes, include these:]
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
        
        is_interior = False
        is_renovated = False
        is_furnished = False
        confidence = 'low'
        
        for line in lines:
            if line.startswith('INTERIOR:'):
                is_interior = 'yes' in line.lower()
            elif line.startswith('RENOVATED:'):
                is_renovated = 'true' in line.lower()
            elif line.startswith('FURNISHED:'):
                is_furnished = 'true' in line.lower()
            elif line.startswith('CONFIDENCE:'):
                confidence = line.split(':')[1].strip().lower()
        
        print(f"Analysis result: interior={is_interior}, confidence={confidence}")
        if is_interior:
            print(f"Interior analysis: renovated={is_renovated}, furnished={is_furnished}")
            if not is_renovated:
                print("Not renovated: Image shows signs of unfinished work or needed renovation")
        else:
            print("Not interior: Exterior shot, floor plan, or blueprint")
            
        # Return all values regardless of confidence level
        return is_renovated, is_furnished, is_interior, confidence
        
    except Exception as e:
        print(f"Error analyzing image {image_url}: {str(e)}")
        return None, None, None, None

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
            WHERE ci.property_id IS NULL
            AND p.id != 'metadata'
            ORDER BY p.id
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def update_property_analysis(property_id: str, is_renovated: bool, is_furnished: bool, is_interior: bool, confidence: str):
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
                is_furnished = %s,
                is_interior = %s,
                confidence = %s
            WHERE property_id = %s
        """, (is_renovated, is_furnished, is_interior, confidence, property_id))
        conn.commit()
        print(f"Updated property {property_id}: renovated={is_renovated}, furnished={is_furnished}, interior={is_interior}, confidence={confidence}")
    except Exception as e:
        print(f"Error updating property {property_id}: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def main():
    if not OPENAI_VISION_API_KEY:
        print("Error: OPENAI_VISION_API_KEY not found in environment variables")
        return
        
    print("Starting property analysis...")
    properties = get_properties_to_analyze()
    print(f"Found {len(properties)} properties to analyze")
    
    for property_id, image_url in properties:
        print(f"\nAnalyzing property {property_id}")
        print(f"Image URL: {image_url}")
        is_renovated, is_furnished, is_interior, confidence = analyze_image(image_url)
        
        if is_renovated is not None and is_furnished is not None:
            update_property_analysis(property_id, is_renovated, is_furnished, is_interior, confidence)
        else:
            print(f"Skipping property {property_id} due to error in analysis")
            
        # Sleep to respect rate limits
        time.sleep(1)
    
    print("\nAnalysis completed!")

if __name__ == "__main__":
    main() 