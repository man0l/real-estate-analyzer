import os
import sys
from dotenv import load_dotenv
import traceback

# Load environment variables from .env file
if not load_dotenv():
    print("Error: Could not load .env file")
    sys.exit(1)

# Check required environment variables
required_vars = ['NEXT_PUBLIC_SUPABASE_URL', 'NEXT_PUBLIC_SUPABASE_ANON_KEY', 'DATABASE_URL']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import json
import time
import re
import requests
import signal
from urllib.parse import urljoin
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
from imot_scraper.image_utils import process_property_image

# Load environment variables
DB_URL = os.getenv('DATABASE_URL', "postgresql://postgres.mbqpxqpvjpimntzjthcc:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres")

def init_database():
    """Initialize database connection and verify it's working"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # Test the connection
        cur.execute("SELECT 1")
        print("Database connection verified successfully")
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
    finally:
        cur.close()
        conn.close()

def save_property(property_data):
    """Save a single property to the database using normalized tables"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # Start transaction
        cur.execute("BEGIN")
        
        # Handle metadata separately
        if property_data.get('id') == 'metadata':
            # Insert or update metadata
            cur.execute("""
                INSERT INTO metadata (key, value, updated_at)
                VALUES ('search_results', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
            """, (Json(property_data['data']),))
            
            conn.commit()
            return

        # First check if property exists and get its current URL
        cur.execute("""
            SELECT url FROM properties WHERE id = %s
        """, (property_data['id'],))
        existing_url = cur.fetchone()

        # Regular property insert/update
        cur.execute("""
            INSERT INTO properties (
                id, type, url, price_value, price_currency, includes_vat,
                area_m2, views, last_modified, image_count, description,
                is_private_seller, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            ) ON CONFLICT (id) DO UPDATE SET
                type = EXCLUDED.type,
                url = COALESCE(EXCLUDED.url, properties.url),
                price_value = EXCLUDED.price_value,
                price_currency = EXCLUDED.price_currency,
                includes_vat = EXCLUDED.includes_vat,
                area_m2 = EXCLUDED.area_m2,
                views = EXCLUDED.views,
                last_modified = EXCLUDED.last_modified,
                image_count = EXCLUDED.image_count,
                description = EXCLUDED.description,
                is_private_seller = EXCLUDED.is_private_seller,
                updated_at = CURRENT_TIMESTAMP
            RETURNING url
        """, (
            property_data['id'],
            property_data.get('type'),
            property_data.get('url'),
            property_data.get('price', {}).get('value'),
            property_data.get('price', {}).get('currency'),
            property_data.get('price', {}).get('includes_vat'),
            property_data.get('area_m2'),
            property_data.get('views'),
            property_data.get('last_modified'),
            property_data.get('image_count'),
            property_data.get('description'),
            property_data.get('is_private_seller')
        ))
        
        updated_url = cur.fetchone()[0]
        
        # If URL has changed, log it in a separate table for tracking
        if existing_url and existing_url[0] != updated_url:
            cur.execute("""
                INSERT INTO url_history (
                    property_id, old_url, new_url, changed_at
                ) VALUES (
                    %s, %s, %s, CURRENT_TIMESTAMP
                )
            """, (
                property_data['id'],
                existing_url[0],
                updated_url
            ))

        # Insert into locations table
        if property_data.get('location'):
            cur.execute("""
                INSERT INTO locations (
                    property_id, city, district
                ) VALUES (%s, %s, %s)
                ON CONFLICT (property_id) DO UPDATE SET
                    city = EXCLUDED.city,
                    district = EXCLUDED.district
            """, (
                property_data['id'],
                property_data['location'].get('city'),
                property_data['location'].get('district')
            ))

        # Insert into floor_info table
        if property_data.get('floor_info'):
            cur.execute("""
                INSERT INTO floor_info (
                    property_id, current_floor, total_floors
                ) VALUES (%s, %s, %s)
                ON CONFLICT (property_id) DO UPDATE SET
                    current_floor = EXCLUDED.current_floor,
                    total_floors = EXCLUDED.total_floors
            """, (
                property_data['id'],
                property_data['floor_info'].get('current_floor'),
                property_data['floor_info'].get('total_floors')
            ))

        # Insert into construction_info table
        if property_data.get('construction_info'):
            cur.execute("""
                INSERT INTO construction_info (
                    property_id, type, year, has_central_heating,
                    is_renovated, is_furnished, has_act16, is_interior,
                    confidence, act16_plan_date, act16_details
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (property_id) DO UPDATE SET
                    type = EXCLUDED.type,
                    year = EXCLUDED.year,
                    has_central_heating = EXCLUDED.has_central_heating,
                    is_renovated = EXCLUDED.is_renovated,
                    is_furnished = EXCLUDED.is_furnished,
                    has_act16 = EXCLUDED.has_act16,
                    is_interior = EXCLUDED.is_interior,
                    confidence = EXCLUDED.confidence,
                    act16_plan_date = EXCLUDED.act16_plan_date,
                    act16_details = EXCLUDED.act16_details
            """, (
                property_data['id'],
                property_data['construction_info'].get('type'),
                property_data['construction_info'].get('year'),
                property_data['construction_info'].get('has_central_heating'),
                property_data['construction_info'].get('is_renovated'),
                property_data['construction_info'].get('is_furnished'),
                property_data['construction_info'].get('has_act16'),
                property_data['construction_info'].get('is_interior'),
                property_data['construction_info'].get('confidence'),
                property_data['construction_info'].get('act16_plan_date'),
                property_data['construction_info'].get('act16_details')
            ))

        # Insert into contact_info table
        if property_data.get('contact_info'):
            cur.execute("""
                INSERT INTO contact_info (
                    property_id, broker_name, phone
                ) VALUES (%s, %s, %s)
                ON CONFLICT (property_id) DO UPDATE SET
                    broker_name = EXCLUDED.broker_name,
                    phone = EXCLUDED.phone
            """, (
                property_data['id'],
                property_data['contact_info'].get('broker_name'),
                property_data['contact_info'].get('phone')
            ))

        # Insert into monthly_payments table
        if property_data.get('monthly_payment'):
            cur.execute("""
                INSERT INTO monthly_payments (
                    property_id, value, currency
                ) VALUES (%s, %s, %s)
                ON CONFLICT (property_id) DO UPDATE SET
                    value = EXCLUDED.value,
                    currency = EXCLUDED.currency
            """, (
                property_data['id'],
                property_data['monthly_payment'].get('value'),
                property_data['monthly_payment'].get('currency')
            ))

        # Insert into features table
        if property_data.get('features'):
            # First delete existing features
            cur.execute("""
                DELETE FROM features
                WHERE property_id = %s
            """, (property_data['id'],))
            
            # Insert new features
            for feature in property_data['features']:
                cur.execute("""
                    INSERT INTO features (property_id, feature)
                    VALUES (%s, %s)
                    ON CONFLICT (property_id, feature) DO NOTHING
                """, (property_data['id'], feature))

        # Handle images
        if property_data.get('images'):
            # Get existing images with their storage URLs
            cur.execute("""
                SELECT url, storage_url, position
                FROM images
                WHERE property_id = %s
            """, (property_data['id'],))
            existing_images = {row[0]: {'storage_url': row[1], 'position': row[2]} 
                             for row in cur.fetchall()}
            
            # Process and insert/update images
            for idx, image_url in enumerate(property_data['images']):
                try:
                    # If image exists and has a storage URL, reuse it
                    if image_url in existing_images and existing_images[image_url]['storage_url']:
                        storage_url = existing_images[image_url]['storage_url']
                        # Update only if position changed
                        if existing_images[image_url]['position'] != idx:
                            cur.execute("""
                                UPDATE images
                                SET position = %s
                                WHERE property_id = %s AND url = %s
                            """, (idx, property_data['id'], image_url))
                    else:
                        # Process new image
                        storage_url = process_property_image(property_data['id'], image_url)
                        
                        # Insert new image record
                        cur.execute("""
                            INSERT INTO images (property_id, url, storage_url, position)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (property_id, url) DO UPDATE SET
                                storage_url = EXCLUDED.storage_url,
                                position = EXCLUDED.position
                        """, (property_data['id'], image_url, storage_url, idx))
                    
                    conn.commit()  # Commit each image operation separately
                except Exception as e:
                    print(f"Error processing image {image_url}: {str(e)}")
                    conn.rollback()  # Rollback only the failed image
                    continue
        
        conn.commit()
    except Exception as e:
        print(f"Error saving property: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

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
        location_elem = soup.find('div', class_='location')
        if location_elem:
            location_text = location_elem.get_text(strip=True)
            if 'град София' in location_text:
                # Extract district - it's between "град София," and the first comma after that
                sofia_idx = location_text.index('град София,')
                remaining_text = location_text[sofia_idx + len('град София,'):].strip()
                district = remaining_text.split(',')[0].strip()
                property_data['location'] = {
                    'city': 'град София',
                    'district': district
                }
        
        # Price information - using proper price selector
        price_elem = soup.find('div', id='cena')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_match = re.search(r'(\d+(?:[\s,]\d+)*)\s*EUR', price_text)
            if price_match:
                price = price_match.group(1).replace(' ', '')
                
                # Check for VAT inclusion
                price_container = soup.find('div', class_='price')
                if price_container:
                    vat_text = price_container.find(string=lambda x: x and ('ДДС' in x if x else False))
                    includes_vat = vat_text and 'без ДДС' not in vat_text.lower()
                
                property_data['price'] = {
                    'value': int(price),
                    'currency': 'EUR',
                    'includes_vat': includes_vat
                }
        
        # Price per square meter - using proper selector
        price_per_sqm_elem = soup.find('span', id='cenakv')
        if price_per_sqm_elem:
            match = re.search(r'(\d+(?:\.\d+)?)\s*EUR/m', price_per_sqm_elem.get_text())
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
        construction_label = soup.find(string=lambda text: text and text.strip() == 'Строителство:')
        if construction_label and construction_label.parent:
            construction_text = construction_label.parent.get_text().strip()
            
            # Parse using the format "Строителство: TYPE, YEAR г."
            type_match = re.search(r'Строителство:\s*(.*?),\s*(\d{4})\s*г\.?', construction_text)
            if type_match:
                construction_type = type_match.group(1).strip()
                construction_year = int(type_match.group(2))
                
                property_data['details']['construction'] = {
                    'type': construction_type,
                    'year': construction_year
                }
            else:
                # Try alternative format without "г." suffix
                type_match = re.search(r'Строителство:\s*(.*?)(?:,\s*(\d{4}))?', construction_text)
                if type_match:
                    construction_type = type_match.group(1).strip() if type_match.group(1) else None
                    construction_year = int(type_match.group(2)) if type_match.group(2) else None
                    
                    if construction_type or construction_year:
                        property_data['details']['construction'] = {
                            'type': construction_type,
                            'year': construction_year
                        }
        
        # Heating
        heating_elem = soup.find(string=re.compile(r'ТЕЦ:'))
        if heating_elem:
            has_central_heating = 'ДА' in heating_elem
            property_data['details']['central_heating'] = has_central_heating
            print(f"Found heating element: '{heating_elem}', setting central_heating to: {has_central_heating}")
        
        # Description
        try:
            # Try to find and click the "show more" link
            show_more = page.query_selector('#dots_link_more')
            if show_more:
                show_more.click()
                # Wait a moment for the content to update
                page.wait_for_timeout(500)
        except Exception as e:
            print(f"Note: Could not expand description: {str(e)}")
        
        # Get updated content after potential expansion
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        description_elem = soup.find(id='description_div')
        if description_elem:
            property_data['description'] = description_elem.get_text(strip=True)
        
        # Features and Private Seller Status
        features = []
        is_private_seller = False
        
        # Check description for private seller indication
        if property_data.get('description'):
            if any(phrase in property_data['description'].lower() for phrase in [
                'частно лице',
                'продава се от физическо лице',
                'собственик продава',
                'директно от собственик'
            ]):
                is_private_seller = True
                features.append('Частно лице')

        # Check features section
        features_elem = soup.find('div', string=re.compile(r'Особености:'))
        if features_elem:
            feature_text = features_elem.parent.get_text().replace('Особености:', '')
            extracted_features = [f.strip() for f in feature_text.split(',')]
            
            # Add unique features
            for feature in extracted_features:
                if feature and feature not in features:
                    features.append(feature)
                    # Check if any feature indicates private seller
                    if any(phrase in feature.lower() for phrase in ['частно лице', 'собственик']):
                        is_private_seller = True
                        if 'Частно лице' not in features:
                            features.append('Частно лице')

        property_data['features'] = features
        property_data['is_private_seller'] = is_private_seller
        
        # Contact information
        contact_info = {}
        broker_elem = soup.find(string=re.compile(r'Брокер:'))
        if broker_elem:
            contact_info['broker_name'] = broker_elem.parent.get_text().replace('Брокер:', '').strip()
            # If no broker name or contains private seller indicators, mark as private seller
            if not contact_info['broker_name'] or any(phrase in contact_info['broker_name'].lower() for phrase in ['собственик', 'частно лице']):
                is_private_seller = True
                if 'Частно лице' not in features:
                    features.append('Частно лице')
        
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

def parse_properties(page, base_url):
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
                            save_property(property_data)
                            
                except Exception as e:
                    print(f"Error processing listing: {str(e)}")
                    continue
            
            # Add a delay between pages
            #time.sleep(3)
    
    except Exception as e:
        print(f"Error parsing properties: {str(e)}")
    
    return metadata

def main():
    base_url = "https://www.imot.bg/pcgi/imot.cgi?act=3&slink=bqn294"
    browser = None
    
    try:
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
            
            # Navigate to the initial page
            print("Accessing the website...")
            page.goto(f"{base_url}&f1=1")
            
            # Parse properties and metadata
            print("Parsing property listings...")
            metadata = parse_properties(page, base_url)
            
            # Save different types of metadata separately
            if metadata:
                # Save search results metadata
                save_property({
                    'id': 'metadata',
                    'data': {
                        'total_listings': metadata.get('total_listings'),
                        'search_criteria': metadata.get('search_criteria', {}),
                        'last_updated': datetime.now().isoformat()
                    }
                })
                
                # Save price statistics metadata
                if 'avg_price_per_sqm' in metadata:
                    conn = psycopg2.connect(DB_URL)
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            INSERT INTO metadata (key, value, updated_at)
                            VALUES ('price_stats', %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (key) DO UPDATE SET
                                value = EXCLUDED.value,
                                updated_at = CURRENT_TIMESTAMP
                        """, (Json({
                            'avg_price_per_sqm': metadata['avg_price_per_sqm'],
                            'currency': 'EUR',
                            'last_updated': datetime.now().isoformat()
                        }),))
                        conn.commit()
                    finally:
                        cur.close()
                        conn.close()
            
            print("Scraping completed successfully")
            
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
    finally:
        if browser:
            try:
                browser.close()
            except:
                pass

if __name__ == "__main__":
    main() 