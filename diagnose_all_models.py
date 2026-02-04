import os
from google import genai
from google.genai import errors

api_key = "AIzaSyAlyz30NKmpKu5uSSuyAMpCc-wLs4RJI_s"
client = genai.Client(api_key=api_key)

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
        # The actual error details are in the 'message' or 'args'
        if "429" in str(e):
            print("   Reason: 429 Rate Limit/Quota Reached.")
            # Try to extract the specific limit mentioned
            if "limit:" in str(e):
                limit_info = str(e).split("limit:")[1].split(",")[0].strip()
                print(f"   Reported Limit: {limit_info}")
        else:
            print(f"   Reason: {e}")
    except Exception as e:
        print(f"   Unexpected Error: {e}")

print("\n--- Diagnosis Complete ---")
