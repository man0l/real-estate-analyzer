import os
from openai import OpenAI
import psycopg2
from dotenv import load_dotenv
import time
import re
from datetime import datetime
from typing import Tuple, Optional

# Load environment variables
load_dotenv()

# Configuration
DB_URL = os.getenv('DATABASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def analyze_building_status(description: str) -> Tuple[bool, Optional[datetime], str]:
    """
    Analyze property description to determine building status.
    Returns (has_act16, act16_plan_date, status_details)
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "user",
                    "content": """Analyze this property description and determine the building's completion status based on mentions of Act 14, 15, or 16.

Rules:
1. Act 14 means rough construction is complete
2. Act 15 means building systems are complete
3. Act 16 is the final completion certificate
4. Future dates indicate planned completion
5. "пред акт 16" means approaching Act 16
6. Look for payment schemes mentioning these acts
7. Extract any mentioned completion dates (for Act 16)

Respond in this exact format:
HAS_ACT16: true/false
PLAN_DATE: [YYYY-MM-DD or none if not found]
STATUS: [one of: completed/in_progress/planned]
DETAILS: [brief explanation]

Here's the description to analyze:
"""
                    + description
                }
            ],
            max_tokens=150
        )

        # Parse the response
        result = response.choices[0].message.content
        lines = result.strip().split('\n')
        
        has_act16 = False
        plan_date = None
        status_details = ""
        
        for line in lines:
            if line.startswith('HAS_ACT16:'):
                has_act16 = 'true' in line.lower()
            elif line.startswith('PLAN_DATE:'):
                date_str = line.replace('PLAN_DATE:', '').strip()
                if date_str.lower() != 'none':
                    try:
                        plan_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        print(f"Warning: Could not parse date {date_str}")
            elif line.startswith('DETAILS:'):
                status_details = line.replace('DETAILS:', '').strip()
        
        print(f"Analysis result: has_act16={has_act16}, plan_date={plan_date}, details={status_details}")
        return has_act16, plan_date, status_details
        
    except Exception as e:
        print(f"Error analyzing description: {str(e)}")
        return None, None, None

def get_properties_to_analyze():
    """Get properties that haven't been analyzed for building status yet"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT p.id, p.description
            FROM properties p
            LEFT JOIN construction_info ci ON ci.property_id = p.id
            WHERE (ci.has_act16 IS NULL OR ci.property_id IS NULL)
            AND p.id != 'metadata'
            AND p.description IS NOT NULL
            ORDER BY p.id
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def update_building_status(property_id: str, has_act16: bool, act16_plan_date: Optional[datetime], act16_details: str):
    """Update the property with building status results"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # First ensure the construction_info record exists
        cur.execute("""
            INSERT INTO construction_info (property_id)
            VALUES (%s)
            ON CONFLICT (property_id) DO NOTHING
        """, (property_id,))
        
        # Then update the status
        cur.execute("""
            UPDATE construction_info
            SET has_act16 = %s,
                act16_plan_date = %s,
                act16_details = %s
            WHERE property_id = %s
        """, (has_act16, act16_plan_date, act16_details, property_id))
        conn.commit()
        print(f"Updated property {property_id}: has_act16={has_act16}, plan_date={act16_plan_date}, details={act16_details}")
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
        
    print("Starting building status analysis...")
    properties = get_properties_to_analyze()
    print(f"Found {len(properties)} properties to analyze")
    
    for property_id, description in properties:
        print(f"\nAnalyzing property {property_id}")
        has_act16, plan_date, status_details = analyze_building_status(description)
        
        if has_act16 is not None:
            update_building_status(property_id, has_act16, plan_date, status_details)
            print(f"Status details: {status_details}")
        else:
            print(f"Skipping property {property_id} due to error")
            
        # Sleep to respect rate limits
        time.sleep(1)
    
    print("\nAnalysis completed!")

if __name__ == "__main__":
    main() 