import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=api_key)

print(f"Checking available models for API Key: {api_key[:10]}...")

try:
    count = 0
    for model in client.models.list():
        try:
            print(f"- {model.name}")
        except:
            print(f"- {model}")
        
        count += 1
        if count >= 30: 
            break
            
except Exception as e:
    print(f"Error listing models: {e}")
