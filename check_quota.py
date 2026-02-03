import os
from google import genai
from google.genai import errors

api_key = "AIzaSyAlyz30NKmpKu5uSSuyAMpCc-wLs4RJI_s"
client = genai.Client(api_key=api_key)

print(f"Testing API Key: {api_key[:10]}...")

try:
    # Test 1: List models to see if key is valid
    print("Test 1: Listing models...")
    models = client.models.list()
    print("Successfully listed models.")
    
    # Test 2: Generate small content to check quota
    print("Test 2: Generating small content (checking quota)...")
    response = client.models.generate_content(
        model="gemini-pro-latest", # Using a common model for testing
        contents="hi"
    )
    print("Successfully generated content.")
    print(f"Response: {response.text}")

except errors.ClientError as e:
    print("\n--- API ERROR DETECTED ---")
    print(f"Status Code: {e.status_code}")
    print(f"Message: {e}")
except Exception as e:
    print(f"\n--- UNEXPECTED ERROR ---\n{e}")
