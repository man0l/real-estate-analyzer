from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import json
import time
import re
import os
import requests
import signal
import sys
from urllib.parse import urljoin
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global flags for graceful shutdown
should_exit = False
is_shutting_down = False

# Database configuration
DB_URL = os.getenv('DATABASE_URL', "postgresql://postgres.mbqpxqpvjpimntzjthcc:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres")

def init_database():
    """Initialize database tables if they don't exist"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # Create versions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crawl_versions (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSONB,
                total_properties INTEGER,
                is_complete BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Create properties table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id VARCHAR(50),
                version_id INTEGER REFERENCES crawl_versions(id),
                data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id, version_id)
            )
        """)
        
        conn.commit()
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def create_new_version(metadata):
    """Create a new crawl version and return its ID"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO crawl_versions (metadata, total_properties, is_complete)
            VALUES (%s, 0, FALSE)
            RETURNING id
        """, (Json(metadata),))
        
        version_id = cur.fetchone()[0]
        conn.commit()
        return version_id
    except Exception as e:
        print(f"Error creating new version: {str(e)}")
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()

def save_property(property_data, version_id):
    """Save a single property to the database"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO properties (id, version_id, data)
            VALUES (%s, %s, %s)
            ON CONFLICT (id, version_id) DO UPDATE
            SET data = EXCLUDED.data
        """, (property_data['id'], version_id, Json(property_data)))
        
        # Update total properties count
        cur.execute("""
            UPDATE crawl_versions
            SET total_properties = (
                SELECT COUNT(*) FROM properties
                WHERE version_id = %s
            )
            WHERE id = %s
        """, (version_id, version_id))
        
        conn.commit()
    except Exception as e:
        print(f"Error saving property: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def complete_version(version_id):
    """Mark a crawl version as complete"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE crawl_versions
            SET is_complete = TRUE
            WHERE id = %s
        """, (version_id,))
        
        conn.commit()
    except Exception as e:
        print(f"Error completing version: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def signal_handler(signum, frame):
    global should_exit, is_shutting_down
    if is_shutting_down:
        print("\nForce quitting...")
        sys.exit(1)
    else:
        print("\nReceived interrupt signal. Finishing current property and saving results...")
        should_exit = True

signal.signal(signal.SIGINT, signal_handler)

def save_partial_results(properties, metadata, filename='property_data.json'):
    """Save current results to file"""
    global is_shutting_down
    
    try:
        is_shutting_down = True
        result = {
            'metadata': metadata,
            'properties': properties,
            'is_complete': False,
            'total_scraped': len(properties)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to {filename}")
    finally:
        is_shutting_down = False

def download_image(url, property_id, image_index, save_dir):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Create directory if it doesn't exist
            os.makedirs(save_dir, exist_ok=True)
            
            # Save the image
            filename = f"{property_id}_{image_index}.jpg"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return filename
    except Exception as e:
        print(f"Error downloading image {url}: {str(e)}")
    return None

def extract_metadata(soup):
    metadata = {}
    try:
        # Extract average price per square meter
        price_info = soup.find(string=lambda text: text and "Средна цена на кв.м" in text)
        if price_info:
            price_match = re.search(r'(\d+)\s*euro', price_info)
            if price_match:
                metadata['avg_price_per_sqm'] = int(price_match.group(1))
        
        # Extract total number of listings
        total_listings = soup.find(string=lambda text: text and "от общо" in text)
        if total_listings:
            match = re.search(r'от общо (\d+)', total_listings)
            if match:
                metadata['total_listings'] = int(match.group(1))
        
        # Extract search criteria
        search_criteria = {}
        criteria_section = soup.find(string=lambda text: text and "Резултат от Вашето търсене" in text)
        if criteria_section:
            parent = criteria_section.parent
            if parent:
                criteria_text = parent.get_text()
                # Extract property types
                if "Вид имот:" in criteria_text:
                    types = re.findall(r'(\d-СТАЕН)', criteria_text)
                    search_criteria['property_types'] = types
                
                # Extract location
                location_match = re.search(r'Местоположение:\s*([^,]+)', criteria_text)
                if location_match:
                    search_criteria['location'] = location_match.group(1).strip()
                
                # Extract district
                district_match = re.search(r'Под район:\s*([^,]+)', criteria_text)
                if district_match:
                    search_criteria['district'] = district_match.group(1).strip()
        
        metadata['search_criteria'] = search_criteria
        
    except Exception as e:
        print(f"Error extracting metadata: {str(e)}")
    
    return metadata

def parse_detail_page(page, property_id):
    if should_exit:
        return None
        
    property_data = {}
    
    try:
        # Wait for any table to appear
        try:
            page.wait_for_selector('table', timeout=10000)
        except PlaywrightTimeout:
            print(f"Timeout waiting for content on property {property_id}")
            return None
        
        # Get the page content
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Basic property information
        property_data['type'] = soup.find('h1').get_text(strip=True) if soup.find('h1') else None
        
        # Location
        location_elem = soup.find('h2')
        if location_elem:
            district_text = location_elem.get_text(strip=True)
            if 'град София' in district_text:
                district = district_text.replace('град София,', '').strip()
                property_data['location'] = {
                    'city': 'град София',
                    'district': district
                }
        
        # Price information
        price_elem = soup.find(string=re.compile(r'\d+\s*EUR'))
        if price_elem:
            price_match = re.search(r'(\d+(?:[\s,]\d+)*)\s*EUR', price_elem)
            if price_match:
                price = price_match.group(1).replace(' ', '')
                property_data['price'] = {
                    'value': int(price),
                    'currency': 'EUR',
                    'includes_vat': True
                }
        
        # Price per square meter
        price_per_sqm_elem = soup.find(string=re.compile(r'(\d+(?:\.\d+)?)\s*EUR/m2'))
        if price_per_sqm_elem:
            match = re.search(r'(\d+(?:\.\d+)?)\s*EUR/m2', price_per_sqm_elem)
            if match:
                property_data['price_per_sqm'] = float(match.group(1))
        
        # Property details
        property_data['details'] = {}
        
        # Area
        area_elem = soup.find(string=re.compile(r'Площ:.*?(\d+)', re.DOTALL))
        if area_elem:
            area_match = re.search(r'Площ:.*?(\d+)', area_elem, re.DOTALL)
            if area_match:
                property_data['details']['area'] = int(area_match.group(1))
        
        # Alternative area parsing from the price per sqm section
        if 'area' not in property_data['details'] and property_data.get('price_per_sqm'):
            price_elem = soup.find(string=lambda x: x and 'EUR/m2' in x)
            if price_elem:
                # Try to find area by dividing total price by price per sqm
                try:
                    price = property_data['price']['value']
                    price_per_sqm = property_data['price_per_sqm']
                    if price and price_per_sqm:
                        area = round(price / price_per_sqm)
                        property_data['details']['area'] = area
                        property_data['details']['area_calculated'] = True
                except Exception:
                    pass
        
        # Floor
        floor_elem = soup.find(string=re.compile(r'Етаж:\s*\d+-ти от \d+'))
        if floor_elem:
            floor_match = re.search(r'(\d+)-ти от (\d+)', floor_elem)
            if floor_match:
                property_data['details']['floor'] = {
                    'current': int(floor_match.group(1)),
                    'total': int(floor_match.group(2))
                }
        
        # Construction type and year
        construction_elem = soup.find(string=re.compile(r'Строителство:.*\d{4}'))
        if construction_elem:
            type_match = re.search(r'Строителство:\s*(.*?),\s*(\d{4})', construction_elem)
            if type_match:
                property_data['details']['construction'] = {
                    'type': type_match.group(1),
                    'year': int(type_match.group(2))
                }
        
        # Heating
        heating_elem = soup.find(string=re.compile(r'ТЕЦ:'))
        if heating_elem:
            property_data['details']['central_heating'] = 'ДА' in heating_elem
        
        # Description
        description_elem = soup.find('div', class_='description')
        if description_elem:
            property_data['description'] = description_elem.get_text(strip=True)
        
        # Features
        features_elem = soup.find('div', string=re.compile(r'Особености:'))
        if features_elem:
            features = [f.strip() for f in features_elem.parent.get_text().replace('Особености:', '').split(',')]
            property_data['features'] = features
        
        # Contact information
        contact_info = {}
        broker_elem = soup.find(string=re.compile(r'Брокер:'))
        if broker_elem:
            contact_info['broker_name'] = broker_elem.parent.get_text().replace('Брокер:', '').strip()
        
        phone_elem = soup.find(string=re.compile(r'Телефон:'))
        if phone_elem:
            contact_info['phone'] = phone_elem.parent.get_text().replace('Телефон:', '').strip()
        
        property_data['contact'] = contact_info
        
        # Views count
        views_elem = soup.find(string=re.compile(r'Обявата е посетена \d+ пъти'))
        if views_elem:
            views_match = re.search(r'(\d+) пъти', views_elem)
            if views_match:
                property_data['views'] = int(views_match.group(1))
        
        # Last modified
        modified_elem = soup.find(string=re.compile(r'Коригирана в \d+:\d+ на \d+ \w+, \d{4}'))
        if modified_elem:
            property_data['last_modified'] = modified_elem.strip()
        
        # Images
        images = []
        img_elements = soup.find_all('img', src=re.compile(r'photos.*\.jpg'))
        for img in img_elements:
            if should_exit:
                break
            img_url = urljoin('https://www.imot.bg/', img['src'])
            images.append(img_url)
        
        property_data['images'] = images
        property_data['image_count'] = len(images)
        
        # Monthly payment
        payment_elem = soup.find(string=re.compile(r'Купи само за \d+ €/месец'))
        if payment_elem:
            payment_match = re.search(r'(\d+) €/месец', payment_elem)
            if payment_match:
                property_data['monthly_payment'] = {
                    'value': int(payment_match.group(1)),
                    'currency': 'EUR'
                }
        
    except Exception as e:
        print(f"Error parsing detail page: {str(e)}")
        return None
    
    return property_data

def get_total_pages(soup):
    try:
        pagination = soup.find_all('a', href=lambda x: x and 'f1=' in x)
        if pagination:
            page_numbers = [int(a.text) for a in pagination if a.text.isdigit()]
            return max(page_numbers) if page_numbers else 1
    except Exception as e:
        print(f"Error getting total pages: {str(e)}")
    return 1

def get_existing_properties(version_id):
    """Get list of already processed property IDs for this version"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT id FROM properties
            WHERE version_id = %s
        """, (version_id,))
        
        existing_ids = {row[0] for row in cur.fetchall()}
        return existing_ids
    except Exception as e:
        print(f"Error getting existing properties: {str(e)}")
        return set()
    finally:
        cur.close()
        conn.close()

def parse_properties(page, base_url, version_id):
    metadata = {}
    
    try:
        # Get the initial page content
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Get metadata from the first page
        metadata = extract_metadata(soup)
        
        # Get total number of pages
        total_pages = get_total_pages(soup)
        print(f"Found {total_pages} pages to scrape")
        
        # Process each page
        for page_num in range(1, total_pages + 1):
            if should_exit:
                print("\nSaving results and exiting...")
                break
                
            if page_num > 1:
                # Navigate to the next page
                next_url = f"{base_url}&f1={page_num}"
                print(f"Navigating to page {page_num}: {next_url}")
                page.goto(next_url)
                try:
                    page.wait_for_selector('table', timeout=10000)
                except PlaywrightTimeout:
                    print(f"Timeout waiting for page {page_num}")
                    continue
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
            
            # Find all property listings on the current page
            listings = soup.find_all('table', {'width': '660'})
            print(f"Processing page {page_num}/{total_pages} - Found {len(listings)} listings")
            
            for listing in listings:
                if should_exit:
                    break
                    
                try:
                    # Find the detail page link
                    detail_link = listing.find('a', href=lambda x: x and 'act=5' in x)
                    if detail_link:
                        detail_url = urljoin('https://www.imot.bg/', detail_link['href'])
                        property_id = re.search(r'adv=([^&]+)', detail_url).group(1)
                        
                        # Navigate to detail page
                        print(f"Processing property {property_id}")
                        page.goto(detail_url)
                        property_data = parse_detail_page(page, property_id)
                        
                        if property_data:
                            property_data['id'] = property_id
                            property_data['url'] = detail_url
                            
                            # Save property to database
                            save_property(property_data, version_id)
                            
                except Exception as e:
                    print(f"Error processing listing: {str(e)}")
                    continue
            
            # Add a delay between pages
            if not should_exit:
                time.sleep(3)
    
    except Exception as e:
        print(f"Error parsing properties: {str(e)}")
    
    return metadata

def main():
    base_url = "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bqn294"
    
    # Initialize database
    print("Initializing database...")
    init_database()
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = context.new_page()
        
        try:
            # Navigate to the initial page
            print("Accessing the website...")
            page.goto(f"{base_url}&f1=1")
            
            # Create new version for this crawl
            version_id = create_new_version({})
            if not version_id:
                raise Exception("Failed to create new crawl version")
            
            print(f"Starting crawl version {version_id}")
            
            # Parse properties and metadata
            print("Parsing property listings...")
            metadata = parse_properties(page, base_url, version_id)
            
            if not should_exit:
                # Update version with metadata and mark as complete
                save_property({'id': 'metadata', 'data': metadata}, version_id)
                complete_version(version_id)
                print(f"Crawl version {version_id} completed successfully")
            
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
        
        finally:
            browser.close()

if __name__ == "__main__":
    main() 