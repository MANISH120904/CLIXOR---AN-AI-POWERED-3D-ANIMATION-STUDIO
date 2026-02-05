import os
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

# Using exact names from your check_models.py output
models_to_test = ["gemini-3-flash-preview", "gemini-pro-latest", "gemini-2.0-flash-lite"]

print(f"--- Diagnosing API Key: {api_key[:10]}... ---")

for model_id in models_to_test:
    print(f"\nTesting Model: {model_id}...")
    try:
        response = client.models.generate_content(
            model=model_id,
            contents="say test"
        )
        print(f"✅ SUCCESS: {model_id} is working.")
        print(f"   Response: {response.text.strip()}")
    except errors.ClientError as e:
        print(f"❌ FAILED: {model_id}")
        if "429" in str(e):
            print("   Reason: 429 Rate Limit/Quota Reached.")
            if "limit:" in str(e):
                # Try to extract the limit value
                parts = str(e).split("limit:")
                if len(parts) > 1:
                    limit_val = parts[1].split(",")[0].strip()
                    print(f"   Reported Limit: {limit_val}")
        else:
            print(f"   Reason: {e}")
    except Exception as e:
        print(f"   Unexpected Error: {e}")

print("\n--- Diagnosis Complete ---")
