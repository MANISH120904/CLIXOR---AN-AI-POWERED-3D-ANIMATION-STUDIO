import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

model_id = "gemini-pro-latest"

print(f"Testing Model: {model_id}...")
try:
    response = client.models.generate_content(
        model=model_id,
        contents="Hello, describe yourself briefly."
    )
    print(f"✅ SUCCESS: {model_id} is working.")
    print(f"   Response: {response.text.strip()}")
except Exception as e:
    print(f"❌ FAILED: {model_id}")
    print(f"   Error: {e}")
