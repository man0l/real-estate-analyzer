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

# Database configuration
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
        # Insert into properties table
        cur.execute("""
            INSERT INTO properties (
                id, type, url, price_value, price_currency, 
                includes_vat, area_m2, views, last_modified, image_count, description,
                is_private_seller
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                type = EXCLUDED.type,
                url = EXCLUDED.url,
                price_value = EXCLUDED.price_value,
                price_currency = EXCLUDED.price_currency,
                includes_vat = EXCLUDED.includes_vat,
                area_m2 = EXCLUDED.area_m2,
                views = EXCLUDED.views,
                last_modified = EXCLUDED.last_modified,
                image_count = EXCLUDED.image_count,
                description = EXCLUDED.description,
                is_private_seller = EXCLUDED.is_private_seller
        """, (
            property_data.get('id'),
            property_data.get('type'),
            property_data.get('url'),
            property_data.get('price', {}).get('value'),
            property_data.get('price', {}).get('currency'),
            property_data.get('price', {}).get('includes_vat'),
            property_data.get('details', {}).get('area'),
            property_data.get('views'),
            property_data.get('last_modified'),
            property_data.get('image_count'),
            property_data.get('description'),
            property_data.get('is_private_seller')
        ))

        # Insert into locations table
        if property_data.get('location'):
            cur.execute("""
                INSERT INTO locations (property_id, city, district)
                VALUES (%s, %s, %s)
                ON CONFLICT (property_id) DO UPDATE SET
                    city = EXCLUDED.city,
                    district = EXCLUDED.district
            """, (
                property_data['id'],
                property_data['location'].get('city'),
                property_data['location'].get('district')
            ))

        # Insert into floor_info table
        if property_data.get('details', {}).get('floor'):
            cur.execute("""
                INSERT INTO floor_info (property_id, current_floor, total_floors)
                VALUES (%s, %s, %s)
                ON CONFLICT (property_id) DO UPDATE SET
                    current_floor = EXCLUDED.current_floor,
                    total_floors = EXCLUDED.total_floors
            """, (
                property_data['id'],
                property_data['details']['floor'].get('current'),
                property_data['details']['floor'].get('total')
            ))

        # Insert into construction_info table
        if property_data.get('details', {}).get('construction') or property_data.get('details', {}).get('central_heating') is not None:
            construction = property_data.get('details', {}).get('construction', {})
            central_heating = property_data.get('details', {}).get('central_heating')
            print(f"Saving construction info with central_heating: {central_heating}")
            cur.execute("""
                INSERT INTO construction_info (
                    property_id, type, year, has_central_heating
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (property_id) DO UPDATE SET
                    type = EXCLUDED.type,
                    year = EXCLUDED.year,
                    has_central_heating = EXCLUDED.has_central_heating
            """, (
                property_data['id'],
                construction.get('type'),
                construction.get('year'),
                central_heating
            ))
            print(f"Construction info saved successfully for property {property_data['id']}")

        # Insert into contact_info table
        if property_data.get('contact'):
            cur.execute("""
                INSERT INTO contact_info (property_id, broker_name, phone)
                VALUES (%s, %s, %s)
                ON CONFLICT (property_id) DO UPDATE SET
                    broker_name = EXCLUDED.broker_name,
                    phone = EXCLUDED.phone
            """, (
                property_data['id'],
                property_data['contact'].get('broker_name'),
                property_data['contact'].get('phone')
            ))

        # Insert into monthly_payments table
        if property_data.get('monthly_payment'):
            cur.execute("""
                INSERT INTO monthly_payments (property_id, value, currency)
                VALUES (%s, %s, %s)
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
            conn.commit()  # Commit the delete
            
            # Insert new features in a new transaction
            for feature in property_data['features']:
                try:
                    cur.execute("""
                        INSERT INTO features (property_id, feature)
                        VALUES (%s, %s)
                        ON CONFLICT (property_id, feature) DO NOTHING
                    """, (property_data['id'], feature))
                    conn.commit()  # Commit each feature insert separately
                except Exception as e:
                    print(f"Error inserting feature {feature}: {str(e)}")
                    conn.rollback()  # Rollback only the failed feature
                    continue

        # Insert into images table
        if property_data.get('images'):
            # First delete existing images
            cur.execute("""
                DELETE FROM images
                WHERE property_id = %s
            """, (property_data['id'],))
            conn.commit()  # Commit the delete
            
            # Insert new images in a new transaction
            for idx, image_url in enumerate(property_data['images']):
                try:
                    cur.execute("""
                        INSERT INTO images (property_id, url, position)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (property_id, url) DO UPDATE SET
                            position = EXCLUDED.position
                    """, (property_data['id'], image_url, idx))
                    conn.commit()  # Commit each image insert separately
                except Exception as e:
                    print(f"Error inserting image {image_url}: {str(e)}")
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
                
                # Check for VAT inclusion
                includes_vat = False
                cenakv_elem = soup.find('span', id='cenakv')
                if cenakv_elem and cenakv_elem.find_next_sibling():
                    next_div = cenakv_elem.find_next_sibling()
                    if next_div and "Цената е с включено ДДС" in next_div.get_text():
                        includes_vat = True
                
                property_data['price'] = {
                    'value': int(price),
                    'currency': 'EUR',
                    'includes_vat': includes_vat
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
            
            # Save metadata
            save_property({'id': 'metadata', 'data': metadata})
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