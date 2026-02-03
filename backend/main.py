from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors
import json
import asyncio
from typing import List, Optional, Dict
import base64

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BLENDER_SERVER_URL = "http://localhost:8081/execute"
BLENDER_VERSION = "5.0"
API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_ID = "gemini-2.0-flash" # Use flash for multimodal capabilities

client = genai.Client(api_key=API_KEY)

class ToolRequest(BaseModel):
    message: str
    session_history: List[str] = [] # List of previously executed code snippets
    image: Optional[str] = None # Base64 image string

async def safe_generate(contents):
    max_api_retries = 5
    for attempt in range(max_api_retries):
        try:
            return client.models.generate_content(model=MODEL_ID, contents=contents)
        except errors.ClientError as e:
            print(f"Gemini API Error: {str(e)}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait_time = (attempt * 10) + 15
                print(f"Rate limit hit. Waiting {wait_time}s before retry (Attempt {attempt+1}/{max_api_retries})...")
                await asyncio.sleep(wait_time)
            else:
                raise e
    raise Exception("API Limit Reached")

async def get_scene_context():
    context_code = """
import bpy
import json
scene_data = {
    "objects": [{"name": o.name, "type": o.type, "location": list(o.location)} for o in bpy.data.objects],
    "active_object": bpy.context.active_object.name if bpy.context.active_object else None
}
print("CONTEXT_START" + json.dumps(scene_data) + "CONTEXT_END")
    """
    try:
        response = requests.post(BLENDER_SERVER_URL, json={"code": context_code}, timeout=5)
        out = response.json().get("output", "")
        if "CONTEXT_START" in out:
            return json.loads(out.split("CONTEXT_START")[1].split("CONTEXT_END")[0])
    except: pass
    return {"objects": []}

def repair_code(code: str) -> str:
    # Fix common Blender 5.0 renames that agents often miss
    replacements = {
        'inputs["Transmission"]': 'inputs["Transmission Weight"]',
        "inputs['Transmission']": "inputs['Transmission Weight']",
        'inputs["Clearcoat"]': 'inputs["Coat Weight"]',
        "inputs['Clearcoat']": "inputs['Coat Weight']",
        'inputs["Specular"]': 'inputs["Specular IOR Level"]',
        "inputs['Specular']": "inputs['Specular IOR Level']",
        'inputs["Emission"]': 'inputs["Emission Color"]',
        "inputs['Emission']": "inputs['Emission Color']",
        '.spring =': '.stiff =',  # Map deprecated SoftBodySettings.spring to .stiff
        '.fcurves': '.curves',    # Attempt to fix Action.fcurves -> Action.curves for new Anim system
        'settings.scale =': 'settings.particle_size =', # Safer fix for ParticleSettings
        'WORLD_ORIGIN': 'WORLD',   # Fix hallucinated enum value for object alignment
        'rotation_mode = "NORMAL"': 'rotation_mode = "NOR"', # Fix Particle rotation enum
        "rotation_mode = 'NORMAL'": "rotation_mode = 'NOR'",  # Fix Particle rotation enum (single quotes)
        "type='EXTRUDE'": "type='SOLIDIFY'", # Fix hallucinated EXTRUDE modifier
        'type="EXTRUDE"': 'type="SOLIDIFY"'  # Fix hallucinated EXTRUDE modifier
    }
    for old, new in replacements.items():
        code = code.replace(old, new)
    return code

@app.post("/interact")
async def blender_agent_interact(request: ToolRequest):
    # 1. Observe (The 'Agent Context' phase)
    context = await get_scene_context()
    
    # 2. Reason & Action (The 'Agent Thought' phase)
    agent_prompt = f"""
    You are a Blender Agent with direct access to a Python Tool.
    
    User Goal: "{request.message}"
    
    **CURRENT SCENE CONTEXT:**
    {json.dumps(context)}
    
    **PREVIOUSLY EXECUTED IN THIS SESSION:**
    {chr(10).join(request.session_history[-5:]) if request.session_history else "No previous commands."}
    
    **TASK:**
    Reason about the user's request (and image if provided) and output a JSON object with your thought and the python code.
    If an image is provided, analyze its visual features (shape, color, composition) and try to recreate them in Blender using Python.
    
    **OUTPUT FORMAT (MANDATORY):**
    {{
        "thought": "your reasoning here",
        "code": "your blender python code here"
    }}
    
    - **INCREMENTAL**: Do NOT clear the scene unless asked.
    - **COMPLEXITY**: UNLEASH full creativity. Do NOT simplify. Use complex geometry, loops, modifiers (Subsurf, Bevel, Array, Boolean), and detailed procedural materials to achieve professional results.
    - **ORGANIC MODELING STRATEGY**: For complex organic characters (like animals, monsters, dragons):
        - **Metaballs**: Use `bpy.ops.object.metaball_add()` to "sculpt" with blobs. It is the best way to code organic shapes.
        - **Blocking**: Assemble the shape using scaled spheres/cylinders/cones, then join them (`bpy.ops.object.join()`) and Remesh (`bpy.ops.object.modifier_add(type='REMESH')`).
        - **Displacement**: Use Noise textures in a Displace modifier to add detail to skin/scales.
    - **CRITICAL BLENDER 5.0 API RENAMES**:
        - **Principled BSDF**: "Transmission" -> "Transmission Weight", "Clearcoat" -> "Coat Weight", "Specular" -> "Specular IOR Level", "Emission" -> "Emission Color".
        - **SoftBodySettings**: ".spring" is removed. Use **".stiff"** (edge stiffness) or **".bend"** (bending stiffness).
        - **Animation**: `Action.fcurves` DOES NOT EXIST. Use `action.curves` or prefer `obj.keyframe_insert()` which handles curves automatically.
        - **Particles**: `psys.settings.scale` is WRONG. Use `psys.settings.particle_size`. Rotation mode 'NORMAL' is WRONG. Use 'NOR'.
        - **Object Creation**: Use `align='WORLD'` instead of `align='WORLD_ORIGIN'`.
        - **Modifiers**: 'EXTRUDE' is NOT a modifier. Use 'SOLIDIFY' to give thickness.
        - ALWAYS check socket/attribute existence before access.
    - **MERCURY LOOK**: High Metallic (1.0), Low Roughness (0.05), Color: (0.8, 0.8, 0.8, 1.0).
    - **NODE SAFETY**: When accessing nodes, it is safer to iterate and check type (e.g., `[n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]`) than using names like 'Principled BSDF'.
    
    Output ONLY the JSON. No conversational text outside the block.
    """    
    request_contents = [agent_prompt]
    
    if request.image:
        try:
            # Handle base64 string (remove data URI scheme if present)
            if "base64," in request.image:
                base64_data = request.image.split("base64,")[1]
            else:
                base64_data = request.image
                
            image_bytes = base64.b64decode(base64_data)
            
            # Create a Part object for the image
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg") # Defaulting to jpeg, sdk handles most common
            request_contents.append(image_part)
            print("Image attached to request.")
        except Exception as e:
            print(f"Error processing image: {e}")

    res = await safe_generate(request_contents)
    text = res.text.strip()
    
    # Robust JSON extraction
    try:
        # 1. Try standard markdown block
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text: # Maybe they forgot 'json' tag
            json_str = text.split("```")[1].strip()
        else:
            # 2. Try finding the outer braces
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                json_str = text[start:end]
            else:
                json_str = text # Hope for the best
            
        agent_data = json.loads(json_str)
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        print(f"RAW TEXT RECEIVED:\n{text}\n----------------")
        
        # Extreme fallback: try to find any python block if JSON failed
        if "```python" in text:
            python_code = text.split("```python")[1].split("```")[0].strip()
            agent_data = {"thought": "Recovered from python block. JSON parsing failed.", "code": python_code}
        else:
            agent_data = {"thought": "Failed to parse agent output. See console for raw text.", "code": "print('Error: Agent output was not valid JSON')"}

    # Fix code for Blender 5.0
    agent_data['code'] = repair_code(agent_data['code'])

    # 3. Tool Execution (The 'MCP Call')
    print(f"Tool Call: {agent_data['thought']}")
    try:
        exec_response = requests.post(BLENDER_SERVER_URL, json={"code": agent_data['code']}, timeout=120)
        exec_data = exec_response.json()
    except Exception as e:
        exec_data = {"success": False, "error": str(e), "output": ""}

    return {
        "thought": agent_data['thought'],
        "code": agent_data['code'],
        "execution": exec_data,
        "new_context": await get_scene_context()
    }

@app.post("/reset")
async def reset_scene():
    reset_code = "import bpy; bpy.ops.wm.read_factory_settings(use_empty=True)"
    try:
        requests.post(BLENDER_SERVER_URL, json={"code": reset_code}, timeout=10)
        return {"status": "success"}
    except:
        return {"status": "failed"}

@app.get("/health")
def health(): return {"status": "ok"}