import sys
import requests
import json

BLENDER_SERVER_URL = "http://localhost:8081/execute"

def execute_in_blender(code):
    try:
        response = requests.post(BLENDER_SERVER_URL, json={"code": code}, timeout=30)
        if response.status_code == 200:
            res = response.json()
            if res.get("success"):
                print("SUCCESS")
                print("Output:\n", res.get("output"))
            else:
                print("FAILED")
                print("Error:\n", res.get("error"))
                print("Output:\n", res.get("output"))
        else:
            print(f"Server Error: {response.status_code}")
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python mcp_tool.py 'your_blender_python_code'")
        sys.exit(1)
    
    code_to_run = sys.argv[1]
    execute_in_blender(code_to_run)

