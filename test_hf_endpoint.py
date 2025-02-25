import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key and endpoint URL from environment variables
HF_API_KEY = os.getenv('HF_API_KEY')
HF_ENDPOINT_URL = os.getenv('HF_ENDPOINT_URL')

# Set up headers
headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {HF_API_KEY}",
    "Content-Type": "application/json"
}

# Define a simple query function
def query(payload):
    print(f"Sending request to: {HF_ENDPOINT_URL}")
    print(f"Payload: {payload}")
    
    try:
        # For llama.cpp server, we need to use the /completion endpoint
        response = requests.post(f"{HF_ENDPOINT_URL}/completion", headers=headers, json=payload)
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 503:
            print("Model is cold, waiting for it to load...")
            # Add wait-for-model header and retry
            headers["x-wait-for-model"] = "true"
            response = requests.post(f"{HF_ENDPOINT_URL}/completion", headers=headers, json=payload)
            print(f"New status code: {response.status_code}")
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error: {str(e)}")
        if hasattr(response, 'text'):
            print(f"Response text: {response.text}")
        return None

# Test with a simple prompt - format for llama.cpp
payload = {
    "prompt": "Hello, how are you?",
    "max_tokens": 50,
    "temperature": 0.7,
    "top_p": 0.95
}

print("Testing Hugging Face Inference Endpoint (llama.cpp)...")
result = query(payload)

if result:
    print("\nSuccess! Response:")
    print(result)
else:
    print("\nFailed to get a valid response.") 