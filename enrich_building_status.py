import os
from openai import OpenAI
import psycopg2
from dotenv import load_dotenv
import time
import re
from datetime import datetime
from typing import Tuple, Optional
import argparse
from openai._exceptions import APIError
import backoff
import logging
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Custom exceptions
class RateLimitExhausted(Exception):
    """Raised when the daily rate limit is exhausted"""
    pass

# Load environment variables
load_dotenv()

# Configuration
DB_URL = os.getenv('DATABASE_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_FALLBACK_KEY = os.getenv('OPENAI_FALLBACK_KEY')  # Fallback OpenAI API key
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')  # Default to OpenAI
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')  # Default model
OPENAI_FALLBACK_MODEL = os.getenv('OPENAI_FALLBACK_MODEL', 'gpt-3.5-turbo')  # Fallback model for OpenAI

# Provider-specific configurations
PROVIDER = os.getenv('AI_PROVIDER', 'openai').lower()  # Default to OpenAI since we hit OpenRouter's rate limit

# Provider-specific base URLs
PROVIDER_BASE_URLS = {
    'openai': 'https://api.openai.com/v1',
    'openrouter': 'https://openrouter.ai/api/v1',
}

# Provider-specific model mappings
MODEL_MAPPINGS = {
    'ollama': 'todorov/bggpt:2B-IT-v1.0.Q4_K_M',  # Default Ollama model
    'openai': 'gpt-3.5-turbo',  # Default OpenAI model
    'openrouter': 'google/gemini-2.0-pro-exp-02-05:free',  # Default OpenRouter model
}

def log_backoff_attempt(details):
    """Log information about the backoff attempt"""
    logger.warning(
        f"Backing off {details['wait']:0.1f} seconds after {details['tries']} tries "
        f"calling function {details['target'].__name__} with args {details['args']} "
        f"and kwargs {details['kwargs']}"
    )

def log_giveup(details):
    """Log information about giving up"""
    logger.error(
        f"Giving up after {details['tries']} tries calling function {details['target'].__name__} "
        f"with args {details['args']} and kwargs {details['kwargs']}"
    )

def should_abort_request(e):
    """Determine if we should abort retrying based on the error"""
    error_msg = str(e).lower()
    
    # Check for daily quota exhaustion indicators
    daily_quota_indicators = [
        'free-models-per-day',
        'daily limit exceeded',
        'quota exceeded',
        'rate limit exceeded: free'
    ]
    
    if any(indicator in error_msg for indicator in daily_quota_indicators):
        logger.error("Daily rate limit has been exhausted. Stopping processing.")
        raise RateLimitExhausted("Daily rate limit exhausted")
    
    return False

# Initialize OpenAI client with appropriate configuration
def get_ai_client():
    client_kwargs = {
        'api_key': OPENAI_API_KEY,
    }
    
    if PROVIDER != 'openai':
        # Use provider-specific base URL if available, otherwise use the one from env
        base_url = PROVIDER_BASE_URLS.get(PROVIDER, OPENAI_BASE_URL)
        client_kwargs['base_url'] = base_url
        
        # Add OpenRouter-specific headers if needed
        if PROVIDER == 'openrouter':
            client_kwargs['default_headers'] = {
                'HTTP-Referer': os.getenv('OPENROUTER_REFERER', 'https://github.com/imotbg/'),
                'X-Title': os.getenv('OPENROUTER_TITLE', 'ImotBG Property Analysis')
            }
    
    logger.info(f"Initializing AI client for provider: {PROVIDER}")
    logger.debug(f"Client configuration: {json.dumps({k: v for k, v in client_kwargs.items() if k != 'api_key'})}")
    return OpenAI(**client_kwargs)

def get_model_for_provider():
    """Get the appropriate model name based on the provider"""
    if OPENAI_MODEL:  # If explicitly set in env, use that
        logger.info(f"Using explicitly set model: {OPENAI_MODEL}")
        return OPENAI_MODEL
    model = MODEL_MAPPINGS.get(PROVIDER, MODEL_MAPPINGS['openai'])
    logger.info(f"Using default model for provider {PROVIDER}: {model}")
    return model

class AIClient:
    def __init__(self):
        self.primary_client = get_ai_client()
        self.fallback_client = None
        self.current_model = get_model_for_provider()
        self.retry_count = 0
        self.max_retries = 3
        logger.info(f"AIClient initialized with model: {self.current_model}")

    def _get_fallback_client(self):
        """Initialize and return fallback OpenAI client"""
        if not self.fallback_client and OPENAI_FALLBACK_KEY:
            logger.info("Initializing fallback OpenAI client")
            self.fallback_client = OpenAI(
                api_key=OPENAI_FALLBACK_KEY,
                base_url='https://api.openai.com/v1'
            )
        return self.fallback_client

    @backoff.on_exception(
        backoff.expo,
        (APIError),  # Only catch APIError, let RateLimitExhausted propagate
        max_tries=5,
        on_backoff=log_backoff_attempt,
        on_giveup=log_giveup,
        base=3,
        factor=2,
        max_time=300,
        giveup=should_abort_request
    )
    def create_chat_completion(self, messages, **kwargs):
        """Create chat completion with automatic fallback and retries"""
        try:
            logger.info(f"Attempting chat completion with model: {self.current_model}")
            logger.debug(f"Request parameters: {json.dumps(kwargs)}")
            
            # Add temperature and presence_penalty to reduce hallucination
            kwargs.setdefault('temperature', 0.3)
            kwargs.setdefault('presence_penalty', 0.1)
            
            response = self.primary_client.chat.completions.create(
                model=self.current_model,
                messages=messages,
                **kwargs
            )
            
            if not response:
                logger.error("Received empty response from API")
                raise Exception("Empty response from API")
                
            if not response.choices:
                error = getattr(response, 'error', {}) or {}
                error_msg = error.get('message', 'Unknown error')
                logger.error(f"No choices in response. Error: {error_msg}")
                
                # Check if this is a rate limit error
                if 'rate limit' in error_msg.lower():
                    should_abort_request(error_msg)
                
                raise Exception(f"No choices in API response: {error_msg}")
                
            logger.info("Successfully received API response")
            logger.debug(f"Response: {response}")
            return response
            
        except RateLimitExhausted:
            # Let RateLimitExhausted propagate up
            raise
            
        except APIError as e:
            error_msg = str(e).lower()
            logger.error(f"API Error: {error_msg}")
            
            # Check if we should abort due to rate limit
            should_abort_request(e)
            
            # Enhanced rate limit detection
            rate_limit_indicators = [
                'rate_limit', 'capacity', 'throttled', 'overloaded',
                'too many requests', '429', 'try again',
                'server is busy', 'please slow down'
            ]
            
            is_rate_limited = any(msg in error_msg for msg in rate_limit_indicators)
            
            # Handle rate limits and model availability issues
            if is_rate_limited:
                logger.warning(f"Primary model throttled ({self.current_model})")
                
                # If using OpenRouter, try falling back to OpenAI
                if PROVIDER == 'openrouter' and self._get_fallback_client():
                    logger.info(f"Falling back to OpenAI model: {OPENAI_FALLBACK_MODEL}")
                    try:
                        # Add exponential delay before fallback
                        delay = min(300, 2 ** self.retry_count)  # Cap at 5 minutes
                        logger.info(f"Waiting {delay} seconds before fallback attempt")
                        time.sleep(delay)
                        
                        self.current_model = OPENAI_FALLBACK_MODEL
                        response = self.fallback_client.chat.completions.create(
                            model=OPENAI_FALLBACK_MODEL,
                            messages=messages,
                            temperature=0.3,  # Add consistent temperature
                            presence_penalty=0.1,
                            **kwargs
                        )
                        if response and response.choices:
                            return response
                        logger.error("Empty response from fallback API")
                    except Exception as fallback_error:
                        logger.error(f"Fallback to OpenAI failed: {str(fallback_error)}")
                        # Check if fallback also hit rate limit
                        should_abort_request(fallback_error)
                        raise
                
                # If already using OpenAI, try the fallback model
                elif PROVIDER == 'openai' and OPENAI_FALLBACK_MODEL:
                    logger.info(f"Falling back to model: {OPENAI_FALLBACK_MODEL}")
                    try:
                        # Add exponential delay before fallback
                        delay = min(300, 2 ** self.retry_count)  # Cap at 5 minutes
                        logger.info(f"Waiting {delay} seconds before fallback attempt")
                        time.sleep(delay)
                        
                        self.current_model = OPENAI_FALLBACK_MODEL
                        response = self.primary_client.chat.completions.create(
                            model=OPENAI_FALLBACK_MODEL,
                            messages=messages,
                            temperature=0.3,  # Add consistent temperature
                            presence_penalty=0.1,
                            **kwargs
                        )
                        if response and response.choices:
                            return response
                        logger.error("Empty response from fallback model")
                    except Exception as fallback_error:
                        logger.error(f"Fallback to alternate model failed: {str(fallback_error)}")
                        # Check if fallback also hit rate limit
                        should_abort_request(fallback_error)
                        raise
            
            # Increment retry count for exponential backoff
            self.retry_count += 1
            
            # Re-raise the error if we can't handle it
            raise
        except Exception as e:
            logger.error(f"Unexpected error in API call: {str(e)}", exc_info=True)
            # Check if we should abort due to rate limit
            should_abort_request(e)
            raise

# Initialize AI client
ai_client = AIClient()

def analyze_building_status(description: str) -> Tuple[bool, Optional[datetime], str]:
    """
    Analyze property description to determine building status.
    Returns (has_act16, act16_plan_date, status_details)
    """
    if not description:
        logger.warning("Empty description provided")
        return None, None, None

    try:
        logger.info("Starting analysis of building status")
        logger.debug(f"Description length: {len(description)} chars")
        
        response = ai_client.create_chat_completion(
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

        if not response or not response.choices:
            logger.warning("Invalid response format from API")
            return None, None, None

        # Parse the response
        logger.debug(f"Raw response: {response.choices[0].message.content}")
        result = response.choices[0].message.content
        if not result:
            logger.warning("Empty response content")
            return None, None, None

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
                        logger.warning(f"Could not parse date: {date_str}")
            elif line.startswith('DETAILS:'):
                status_details = line.replace('DETAILS:', '').strip()
        
        logger.info(f"Analysis result: has_act16={has_act16}, plan_date={plan_date}, details={status_details}")
        return has_act16, plan_date, status_details
        
    except RateLimitExhausted:
        # Let RateLimitExhausted propagate up
        raise
        
    except Exception as e:
        logger.error(f"Error analyzing description: {str(e)}", exc_info=True)
        if description:
            logger.error(f"Description that caused error: {description[:100]}...")
        return None, None, None

def get_properties_to_analyze(force: bool = False):
    """Get properties that haven't been analyzed for building status yet"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        if force:
            logger.info("Fetching all properties (force mode)")
            cur.execute("""
                SELECT p.id, p.description
                FROM properties p
                WHERE p.id != 'metadata'
                AND p.description IS NOT NULL
                ORDER BY p.id
            """)
        else:
            logger.info("Fetching only unanalyzed properties")
            cur.execute("""
                SELECT p.id, p.description
                FROM properties p
                LEFT JOIN construction_info ci ON ci.property_id = p.id
                WHERE (ci.has_act16 IS NULL OR ci.property_id IS NULL)
                AND p.id != 'metadata'
                AND p.description IS NOT NULL
                ORDER BY p.id
            """)
        results = cur.fetchall()
        logger.info(f"Found {len(results)} properties to analyze")
        return results
    except Exception as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise
    finally:
        cur.close()
        conn.close()

def update_building_status(property_id: str, has_act16: bool, act16_plan_date: Optional[datetime], act16_details: str):
    """Update the property with building status results"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # First ensure the construction_info record exists
        logger.debug(f"Ensuring construction_info record exists for property {property_id}")
        cur.execute("""
            INSERT INTO construction_info (property_id)
            VALUES (%s)
            ON CONFLICT (property_id) DO NOTHING
        """, (property_id,))
        
        # Then update the status
        logger.info(f"Updating status for property {property_id}")
        cur.execute("""
            UPDATE construction_info
            SET has_act16 = %s,
                act16_plan_date = %s,
                act16_details = %s
            WHERE property_id = %s
        """, (has_act16, act16_plan_date, act16_details, property_id))
        conn.commit()
        logger.info(f"Successfully updated property {property_id}: has_act16={has_act16}, plan_date={act16_plan_date}")
        logger.debug(f"Details: {act16_details}")
    except Exception as e:
        logger.error(f"Error updating property {property_id}: {str(e)}", exc_info=True)
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def main():
    parser = argparse.ArgumentParser(description='Analyze building status from property descriptions')
    parser.add_argument('--force', action='store_true', help='Force reprocessing of all properties')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not found in environment variables")
        return
        
    logger.info("Starting building status analysis...")
    try:
        properties = get_properties_to_analyze(force=args.force)
        total_properties = len(properties)
        logger.info(f"Found {total_properties} properties to analyze")
        
        # Initialize variables for dynamic rate limiting
        consecutive_failures = 0
        base_sleep_time = 1
        max_sleep_time = 60
        success_count = 0
        processed_count = 0
        
        for property_id, description in properties:
            try:
                logger.info(f"\nAnalyzing property {property_id} ({processed_count + 1}/{total_properties})")
                has_act16, plan_date, status_details = analyze_building_status(description)
                
                if has_act16 is not None:
                    update_building_status(property_id, has_act16, plan_date, status_details)
                    # Reset failure count and adjust sleep time on success
                    consecutive_failures = 0
                    success_count += 1
                    # Gradually reduce sleep time after consistent successes
                    if success_count > 5 and base_sleep_time > 1:
                        base_sleep_time = max(1, base_sleep_time * 0.8)
                else:
                    logger.warning(f"Skipping property {property_id} due to error")
                    consecutive_failures += 1
                
            except RateLimitExhausted as e:
                logger.error(f"\n{'='*80}\nDaily rate limit exhausted. Stopping processing.\n"
                           f"Processed {processed_count} out of {total_properties} properties.\n"
                           f"Please try again when the rate limit resets.\n{'='*80}")
                return
                
            except Exception as e:
                logger.error(f"Error processing property {property_id}: {str(e)}")
                consecutive_failures += 1
                success_count = 0
            
            processed_count += 1
            
            # Dynamic sleep time based on consecutive failures
            sleep_time = min(max_sleep_time, base_sleep_time * (2 ** consecutive_failures))
            logger.info(f"Sleeping for {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
        
        logger.info(f"Analysis completed successfully! Processed {processed_count} properties.")
    except Exception as e:
        logger.error("Fatal error during analysis", exc_info=True)
        raise

if __name__ == "__main__":
    main() 