import os
import requests
import psycopg2
from dotenv import load_dotenv
import time
import re
from datetime import datetime
from typing import Tuple, Optional
import random

# Load environment variables
load_dotenv()

# Configuration
DB_URL = os.getenv('DATABASE_URL')
HF_API_KEY = os.getenv('HF_API_KEY')
HF_ENDPOINT_URL = os.getenv('HF_ENDPOINT_URL')  # URL of your Hugging Face Inference Endpoint
HF_MODEL = os.getenv('HF_MODEL', 'mistralai/Mistral-7B-Instruct-v0.2')  # Default model
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))  # Maximum number of retries for API calls

# Provider-specific configurations
PROVIDER = os.getenv('AI_PROVIDER', 'huggingface').lower()  # Default to huggingface

# Provider-specific model mappings
MODEL_MAPPINGS = {
    'huggingface': 'mistralai/Mistral-7B-Instruct-v0.2',  # Default HF model
}

def get_model_for_provider():
    """Get the appropriate model name based on the provider"""
    if HF_MODEL:  # If explicitly set in env, use that
        return HF_MODEL
    return MODEL_MAPPINGS.get(PROVIDER, MODEL_MAPPINGS['huggingface'])

def analyze_building_status(description: str) -> Tuple[bool, Optional[datetime], str]:
    """
    Analyze property description to determine building status.
    Returns (has_act16, act16_plan_date, status_details)
    """
    try:
        # Prepare the prompt
        prompt = f"""
        Ти си екперт в анализите на обяви за недвижими имоти. Следният текст е от обява за апартамент в София.

        Описание: {description}

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

        Използвай днешната дата за да сравняваш бъдещите дати ако са споменати: {datetime.today().strftime('%Y-%m-%d')}
        """

        # For llama.cpp server, we need to use the /completion endpoint with the correct format
        payload = {
            "prompt": prompt,
            "max_tokens": 150,
            "temperature": 0.1,
            "top_p": 0.95
        }

        # Make the API call
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {HF_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Define a function to make the API call with retries
        def query(payload, max_retries=MAX_RETRIES):
            retries = 0
            backoff_time = 1  # Start with 1 second backoff
            
            while retries <= max_retries:
                try:
                    response = requests.post(f"{HF_ENDPOINT_URL}/completion", headers=headers, json=payload, timeout=60)
                    
                    # Handle cold model
                    if response.status_code == 503:
                        print("Model is cold, waiting for it to load...")
                        # Add wait-for-model header and retry
                        headers["x-wait-for-model"] = "true"
                        response = requests.post(f"{HF_ENDPOINT_URL}/completion", headers=headers, json=payload, timeout=120)
                    
                    # Handle rate limits
                    if response.status_code == 429:
                        if retries < max_retries:
                            wait_time = backoff_time + random.uniform(0, 1)
                            print(f"Rate limited. Retrying in {wait_time:.2f} seconds... (Attempt {retries+1}/{max_retries})")
                            time.sleep(wait_time)
                            backoff_time *= 2  # Exponential backoff
                            retries += 1
                            continue
                    
                    # Handle other errors
                    response.raise_for_status()
                    return response.json()
                    
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    if retries < max_retries:
                        wait_time = backoff_time + random.uniform(0, 1)
                        print(f"Error: {str(e)}. Retrying in {wait_time:.2f} seconds... (Attempt {retries+1}/{max_retries})")
                        time.sleep(wait_time)
                        backoff_time *= 2  # Exponential backoff
                        retries += 1
                    else:
                        print(f"Failed after {max_retries} retries: {str(e)}")
                        raise
            
            raise Exception(f"Failed after {max_retries} retries")
        
        # Make the API call
        result = query(payload)
        
        # Extract the generated text from llama.cpp response
        generated_text = result.get("content", "")
        
        print(generated_text)
        
        # Improved parsing logic
        has_act16 = False
        plan_date = None
        status_details = ""
        
        # Use regex to find the first complete set of values
        has_act16_match = re.search(r'HAS_ACT16:\s*(true|false)', generated_text, re.IGNORECASE)
        plan_date_match = re.search(r'PLAN_DATE:\s*(\d{4}-\d{2}-\d{2}|none|\d{4}-\d{2})', generated_text, re.IGNORECASE)
        status_match = re.search(r'STATUS:\s*(completed|in_progress|planned)', generated_text, re.IGNORECASE)
        details_match = re.search(r'DETAILS:\s*(.+?)(?:\n|$)', generated_text, re.IGNORECASE)
        
        if has_act16_match:
            has_act16 = has_act16_match.group(1).lower() == 'true'
        
        if plan_date_match:
            date_str = plan_date_match.group(1).strip()
            if date_str.lower() != 'none':
                try:
                    # Handle different date formats
                    if re.match(r'\d{4}-\d{2}$', date_str):  # Format YYYY-MM
                        date_str = f"{date_str}-15"  # Add a default day
                    
                    # Handle invalid day/month values
                    year, month, day = map(int, date_str.split('-'))
                    if month > 12:
                        month = 12
                    if day > 28:
                        day = 28
                    
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    plan_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError as e:
                    print(f"Warning: Could not parse date {date_str}: {str(e)}")
        
        if details_match:
            status_details = details_match.group(1).strip()
        
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
    if not HF_API_KEY:
        print("Error: HF_API_KEY not found in environment variables")
        return
        
    if not HF_ENDPOINT_URL:
        print("Error: HF_ENDPOINT_URL not found in environment variables")
        return
        
    print("Starting building status analysis with Hugging Face Inference Endpoints...")
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