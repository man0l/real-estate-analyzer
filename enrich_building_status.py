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
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')  # Default to OpenAI
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')  # Default model

# Provider-specific configurations
PROVIDER = os.getenv('AI_PROVIDER', 'openai').lower()  # Can be 'openai', 'ollama', or others

# Provider-specific model mappings
MODEL_MAPPINGS = {
    'ollama': 'todorov/bggpt:2B-IT-v1.0.Q4_K_M',  # Default Ollama model
    'openai': 'gpt-4o-mini',  # Default OpenAI model
}

# Initialize OpenAI client with appropriate configuration
def get_ai_client():
    client_kwargs = {
        'api_key': OPENAI_API_KEY,
    }
    
    if PROVIDER != 'openai':
        client_kwargs['base_url'] = OPENAI_BASE_URL
    
    return OpenAI(**client_kwargs)

# Initialize OpenAI client
client = get_ai_client()

def get_model_for_provider():
    """Get the appropriate model name based on the provider"""
    if OPENAI_MODEL:  # If explicitly set in env, use that
        return OPENAI_MODEL
    return MODEL_MAPPINGS.get(PROVIDER, MODEL_MAPPINGS['openai'])

def analyze_building_status(description: str) -> Tuple[bool, Optional[datetime], str]:
    """
    Analyze property description to determine building status.
    Returns (has_act16, act16_plan_date, status_details)
    """
    try:
        response = client.chat.completions.create(
            model=get_model_for_provider(),
            messages=[
                {
                    "role": "user",
                    "content": """
                            Ти си екперт в анализите на обяви за недвижими имоти. Следният текст е от обява за апартамент в София.

                            Описание: """ + description + """

                            Анализирай описанието на този имот и разбнери дали сградата е на в строеж или е въведена в експлоатация. Това става като се споменава акт 14, акт 15 и акт 16.

                            Rules:
                            1. Бъдещи дати означава, че се планира завършване на сградата, например "ще бъде завършена през март 2025", "очкава се акт 16 през март". Това значи, че сградата не е въведена в експлоатация и няма получен акт 16.
                            2. "пред акт 16" означава, че се очаква акт 16 скоро. Това значи, че има акт 15 и няма акт 16. Същото важи и за "С акт 15".
                            3. разрешение за ползване означава, че има разрешение за ползване на сградата и сградата има акт 16 и е въведена в експлоатация.                           
                            4. Извлечи всички споменати дати за Акт 16 ако има такива и има акт 14 или акт 15.
                            5. фаза Акт 14 оазначава, че има получен акт 14 и няма акт 16.
                           
                            Задължително отговаряй с този формат без да коментираш излишно и не добявай излишни полета и символи:
                            HAS_ACT16: true/false
                            PLAN_DATE: [YYYY-MM-DD or none if not found]
                            STATUS: [едно от: completed/in_progress/planned]
                            DETAILS: [кратко описание]

                            Не може да има акт 14 и акт 16 или акт 14 и акт 15, те са един след друг. Ако в текста е споменато, че има акт 14 и се очаква акт 16, тогава има акт 14 и няма акт 16.

                            Използвай днешната дата за да сравняваш бъдещите дати ако са споменати: """ + datetime.today().strftime('%Y-%m-%d')
                }
            ],
            max_tokens=150
        )

        # Parse the response
        print(response.choices[0].message.content)
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