# Imot.bg Property Scraper

This is a simple web scraper for imot.bg property listings using the crawl4ai library.

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the scraper:
```bash
python imot_scraper.py
```

The script will scrape the property listing and save the results to `property_data.json`.

## Output

The scraper will extract the following information:
- Price
- Location
- Property details
- Description

The data will be saved in JSON format. 