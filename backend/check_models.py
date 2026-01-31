import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("No API key found in .env")
    exit()

client = genai.Client(api_key=api_key)

print("Checking available Gemini models for your API key...")

try:
    # Just list the first 20 models to see what's available
    count = 0
    for model in client.models.list():
        # Depending on SDK version, it might be model.name or model.display_name
        # We will try to print the name
        try:
            print(f"- {model.name}")
        except:
            print(f"- {model}")
        
        count += 1
        if count >= 20: 
            break
            
except Exception as e:
    print(f"Error listing models: {e}")
