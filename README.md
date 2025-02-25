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

## Building Status Analysis

The project includes scripts to analyze property descriptions and determine building status (Act 16 completion status):

### OpenAI Version

```bash
python enrich_building_status.py
```

This script uses OpenAI's API to analyze property descriptions. You need to set the following environment variables:
- `DATABASE_URL`: PostgreSQL database connection string
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: (Optional) The model to use (default: gpt-4o-mini)

### Hugging Face Version

```bash
python enrich_building_status_hf.py
```

This script uses Hugging Face Inference Endpoints to analyze property descriptions. You need to set the following environment variables:
- `DATABASE_URL`: PostgreSQL database connection string
- `HF_API_KEY`: Your Hugging Face API key
- `HF_ENDPOINT_URL`: The URL of your Hugging Face Inference Endpoint
- `HF_MODEL`: (Optional) The model to use (default: mistralai/Mistral-7B-Instruct-v0.2)

## Output

The scraper will extract the following information:
- Price
- Location
- Property details
- Description

The data will be saved in JSON format.

The building status analysis will update the database with:
- Whether the building has Act 16 (completion certificate)
- Planned date for Act 16 (if available)
- Details about the building status 