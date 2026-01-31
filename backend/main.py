from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
import json

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For prototyping, allow all. In prod, specify ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BLENDER_SERVER_URL = "http://localhost:8081/execute"
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("WARNING: GOOGLE_API_KEY not found in .env file.")

client = genai.Client(api_key=API_KEY)

class UserRequest(BaseModel):
    prompt: str

class AgentResponse(BaseModel):
    plan: str
    code: str
    execution_result: dict
    qa_feedback: str = None

@app.post("/generate", response_model=AgentResponse)
async def generate_animation(request: UserRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is missing.")

    # --- 1. Director Agent ---
    print(f"Director receiving prompt: {request.prompt}")
    director_prompt = f"""
    You are the **Director Agent** for a 3D animation studio.
    Your goal is to break down the user's request into a detailed technical plan for a Blender animation.
    
    User Request: "{request.prompt}"
    
    Output a structured plan including:
    - Scene setup (lighting, camera).
    - Objects/Characters to create.
    - Animation details (movement, timing).
    - Mood/Style.
    
    Keep it concise but technical enough for a Tech Artist to understand.
    """
    
    try:
        director_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=director_prompt
        )
        plan = director_response.text
        print(f"Director Plan:\n{plan}")
    except Exception as e:
        print(f"Director Agent Error: {e}")
        raise HTTPException(status_code=500, detail=f"Director Agent failed: {str(e)}")

    # --- 2. Tech Artist Agent ---
    print("Tech Artist generating code...")
    artist_prompt = f"""
    You are the **Tech Artist Agent**. You write Python code for Blender (bpy).
    
    Director's Plan:
    {plan}
    
    **Instructions:**
    - Write a complete, executable Python script for Blender.
    - Start with `import bpy`.
    - Clear existing objects at the start:
      ```python
      bpy.ops.object.select_all(action='DESELECT')
      # Use valid types for Blender 4.x: 'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'ARMATURE', 'LATTICE', 'EMPTY', 'LIGHT', 'CAMERA', 'SPEAKER', 'GREASEPENCIL' (NOT 'GPENCIL')
      for obj_type in ['MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'ARMATURE', 'LATTICE', 'EMPTY', 'LIGHT', 'CAMERA', 'SPEAKER', 'GREASEPENCIL']:
          bpy.ops.object.select_by_type(type=obj_type)
      bpy.ops.object.delete()
      ```
    - Setup the scene, objects, and animation based on the plan.
    - Ensure the camera is positioned to see the action.
    - **CRITICAL**: Do NOT use infinite loops or modal operators that block execution.
    - **CRITICAL**: When setting colors, ALWAYS use a tuple of 4 floats `(R, G, B, A)`.
    - **CRITICAL**: When setting vectors, use tuples of 3 floats `(x, y, z)`.
    - **CRITICAL**: Before accessing `.use_nodes`, ensure the material or world object exists.
        - **NEVER** assume a material exists. **ALWAYS** create it: `mat = bpy.data.materials.new(name="MyMaterial")`.
        - **ALWAYS** check if an object is not None before accessing attributes like `.use_nodes`.
        - Example: `if mat: mat.use_nodes = True`
    - **CRITICAL**: Object Linking:
        - **Do NOT** manually link objects created with `bpy.ops` (e.g., `bpy.ops.mesh.primitive_cube_add()`). They are linked automatically. attempting to link them again will CRASH the script.
        - **ONLY** manually link objects created via `bpy.data.objects.new(...)`.
    - **CRITICAL**: Blender 4.0+ API Changes:
        - In the **Principled BSDF** node:
            - "Transmission" is now **"Transmission Weight"**.
            - "Clearcoat" is now **"Coat Weight"**.
            - "Specular" is now **"Specular IOR Level"**.
        - Always use the new socket names to avoid `KeyError`.
    - **CRITICAL**: **DO NOT** use `if __name__ == "__main__":`.
        - The script is executed via `exec()`, so `__name__` will NOT be "__main__".
        - Call your functions directly at the end of the script.
        - Example:
          ```python
          setup_scene()
          create_objects()
          animate()
          ```
    - **CRITICAL**: Add `print("Created: <Object Name>")` after creating each major object.
    - Output ONLY the raw Python code. Do not include markdown backticks (```python ... ```).
    """
    
    try:
        artist_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=artist_prompt
        )
        
        # Clean up code format if Gemini adds markdown
        code = artist_response.text.strip()
        if code.startswith("```"):
            code = code.split("\n", 1)[1]
        if code.endswith("```"):
            code = code.rsplit("\n", 1)[0]
        
        print(f"Generated Code (first 100 chars): {code[:100]}...")
    except Exception as e:
        print(f"Tech Artist Agent Error: {e}")
        raise HTTPException(status_code=500, detail=f"Tech Artist Agent failed: {str(e)}")

    # --- 3. Execution (Blender MCP) ---
    print("Sending to Blender...")
    execution_result = {}
    try:
        response = requests.post(BLENDER_SERVER_URL, json={"code": code})
        execution_result = response.json()
    except Exception as e:
        execution_result = {"success": False, "error": f"Failed to connect to Blender: {str(e)}", "output": ""}
        print(f"Blender Connection Error: {e}")

    # --- 4. Vision QA Agent ---
    # In a full version, we would send the rendered image. 
    # For now, we analyze the execution output and the plan.
    print("Vision QA analyzing result...")
    
    qa_context = f"""
    You are the **Vision QA Agent**. Analyze the execution of the 3D generation.
    
    Director's Plan: {plan}
    
    Execution Output: {execution_result.get('output', '')}
    Execution Error: {execution_result.get('error', '')}
    Success Status: {execution_result.get('success', False)}
    
    Provide a brief critique. Did it crash? Did it seem to generate the objects requested?
    """
    
    try:
        qa_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=qa_context
        )
        qa_feedback = qa_response.text
        print(f"QA Feedback: {qa_feedback}")
    except Exception as e:
        print(f"QA Agent Error: {e}")
        qa_feedback = "QA Agent unavailable."

    return {
        "plan": plan,
        "code": code,
        "execution_result": execution_result,
        "qa_feedback": qa_feedback
    }

@app.get("/health")
def health_check():
    return {"status": "running"}
