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
MODEL_ID = "gemini-3-flash-preview" # Use gemini-3-flash-preview as requested

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
        'settings.scale =': 'settings.particle_size =', # Safer fix for ParticleSettings
        'WORLD_ORIGIN': 'WORLD',   # Fix hallucinated enum value for object alignment
        'rotation_mode = "NORMAL"': 'rotation_mode = "NOR"', # Fix Particle rotation enum
        "rotation_mode = 'NORMAL'": "rotation_mode = 'NOR'",  # Fix Particle rotation enum (single quotes)
        "type='EXTRUDE'": "type='SOLIDIFY'", # Fix hallucinated EXTRUDE modifier
        'type="EXTRUDE"': 'type="SOLIDIFY"',  # Fix hallucinated EXTRUDE modifier
        '.fcurves': '.keyframe_insert',  # Action.fcurves does not exist in Blender 5.0.1, use keyframe_insert() instead
        '.use_contact_shadow': '# contact shadow removed in Blender 5.0+',  # Remove deprecated attribute
        'use_contact_shadow =': '# contact shadow removed in Blender 5.0+:',  # Remove deprecated attribute assignments
        'ShaderNodeTexMusgrave': 'ShaderNodeTexNoise',  # Musgrave noise doesn't exist, use Noise texture instead
        'ShaderNodeTexCellular': 'ShaderNodeTexNoise',  # Cellular noise replaced with generic Noise
        'rigidbody_world.animation_data': 'None # rigidbody_world.animation_data is not accessible',  # Cannot access animation_data on RigidBody World
        '.animation_data' : '.animation_data if hasattr(self, "animation_data") else None',  # Safe access to animation_data
    }
    for old, new in replacements.items():
        code = code.replace(old, new)
    
    # Additional fixes for common iterator issues
    # Fix: for x in obj.indices -> for x in obj.users_collection (safer iteration)
    code = code.replace('for x in obj.indices', 'for x in obj.users_collection')
    
    # Fix: for x in obj.locations -> use location directly
    import re
    code = re.sub(r'for\s+\w+\s+in\s+\w+\.locations', 'for _ in [obj.location]', code)
    
    # Fix rigidbody_world attribute access - wrap in safety checks
    if 'rigidbody_world' in code and 'animation_data' in code:
        code = code.replace(
            'bpy.context.scene.rigidbody_world.animation_data',
            '(bpy.context.scene.rigidbody_world.animation_data if bpy.context.scene.rigidbody_world and hasattr(bpy.context.scene.rigidbody_world, "animation_data") else None)'
        )
    
    return code

@app.post("/interact")
async def blender_agent_interact(request: ToolRequest):
    # 1. Observe (The 'Agent Context' phase)
    context = await get_scene_context()
    
    # 2. Reason & Action (The 'Agent Thought' phase)
    agent_prompt = f"""
    You are a Blender 5.0.1 Python Agent with direct access to a Python execution tool.
    
    **BLENDER VERSION: 5.0.1** (You MUST use Blender 5.0.1 API, NOT older versions)
    
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
    
    - **CRITICAL BLENDER 5.0.1 API CHANGES** (These are REQUIRED, not optional):
        - **Principled BSDF Socket Names**: "Transmission" -> "Transmission Weight", "Clearcoat" -> "Coat Weight", "Specular" -> "Specular IOR Level", "Emission" -> "Emission Color".
        - **SoftBodySettings**: ".spring" is REMOVED. Use **".stiff"** (edge stiffness) or **".bend"** (bending stiffness) instead.
        - **Animation/Keyframes**: DO NOT use `Action.fcurves` or `Action.curves`. Instead use `obj.keyframe_insert(data_path='rotation_euler', frame=10)` or `obj.keyframe_insert(data_path='location', frame=10)` for direct keyframing.
        - **Particles**: `psys.settings.scale` is WRONG. Use `psys.settings.particle_size`. Rotation mode 'NORMAL' -> 'NOR'.
        - **RigidBody Physics**: `.use_initial_velocity` DOES NOT EXIST. Use keyframes on location to simulate initial momentum.
        - **RigidBody World**: DO NOT access `.animation_data` on `rigidbody_world`. It DOES NOT EXIST. If you need to animate rigid body physics, use keyframes on object locations/rotations instead.
        - **Object Attributes**: NEVER try to iterate over `.indices`, `.locations`, or other method-like attributes. Always check if an attribute is callable before trying to iterate.
        - **Shader Nodes**: NEVER use `ShaderNodeTexMusgrave` or `ShaderNodeTexCellular` - these don't exist. Use `ShaderNodeTexNoise` instead for procedural noise textures.
        - **Object Alignment**: Use `align='WORLD'`, NOT `align='WORLD_ORIGIN'`.
        - **Modifiers**: 'EXTRUDE' is NOT a modifier. Use 'SOLIDIFY' for thickness.
        - **World Lighting**: ALWAYS check that `bpy.context.scene.world` is not None before accessing it. If None, create a new world: `world = bpy.data.worlds.new("World"); bpy.context.scene.world = world;`. Then enable nodes: `world.use_nodes = True`.
        - **Shader Nodes**: Always ensure `material.use_nodes = True` before creating shader nodes. For world lighting, also ensure `world.use_nodes = True`. Check that objects are not None before accessing their properties.
        - **SAFE ATTRIBUTE ACCESS**: Always use `hasattr()` or try/except blocks when accessing non-standard attributes. Example: `if hasattr(obj, 'animation_data') and obj.animation_data:`.
        - **ITERATOR SAFETY**: Before iterating over an attribute, verify it's iterable. Never try to iterate over methods or built-in functions. Always check `callable()` first.
    
    - **MERCURY LOOK**: High Metallic (1.0), Low Roughness (0.05), Color: (0.8, 0.8, 0.8, 1.0).
    - **NODE SAFETY**: When accessing nodes, iterate and check type (e.g., `[n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'][0]`) rather than relying on node names. Ensure `mat` is not None and `mat.use_nodes` is True before access.
    
    - **POLY HAVEN ASSETS (HIGHLY RECOMMENDED FOR QUALITY MODELS)**:
        - You have access to `download_polyhaven_asset(search_term, asset_type)` which downloads professional-quality 3D assets.
        - You have access to `import_polyhaven_model(model_path)` which imports downloaded models into the scene automatically.
        - **MUST USE FOR**: Objects, furniture, plants, buildings, props, landscapes, HDRIs.
        - **Asset Types Available**:
            - `hdris`: Environment lighting (e.g., "forest", "studio", "outdoor", "urban")
            - `models`: 3D models (e.g., "tree", "rock", "chair", "building", "plant", "grass", "fence", "car", "house")
            - `textures`: PBR textures (limited support)
        - **BEST PRACTICES FOR MODELS**:
            1. Download: `model_path = download_polyhaven_asset("tree", "models")`
            2. Check: `if model_path: imported_objs = import_polyhaven_model(model_path)`
            3. Arrange: Position/scale/duplicate imported objects as needed
            4. **DON'T CODE SIMPLE OBJECTS** - Use Poly Haven instead! A downloaded tree/rock/chair is far better than procedural.
        - **HDRI WORKFLOW** (for professional lighting):
            1. Download: `hdri_path = download_polyhaven_asset("studio", "hdris")`
            2. Load:
               ```python
               if hdri_path:
                   world = bpy.context.scene.world
                   world.use_nodes = True
                   bpy.ops.image.open(filepath=hdri_path)
                   img = bpy.data.images[-1]
                   env_tex = world.node_tree.nodes.new(type='ShaderNodeTexEnvironment')
                   env_tex.image = img
                   world.node_tree.links.new(env_tex.outputs['Color'], 
                                            world.node_tree.nodes['Background'].inputs['Background'])
               ```
        - **PRACTICAL EXAMPLES**:
            - **Forest scene**: `download("forest", "hdris")` → `download("tree", "models")` → duplicate & scatter
            - **Interior room**: `download("building", "models")` → `download("chair", "models")` → arrange furniture
            - **Urban scene**: Multiple `download("building", "models")` → arrange in grid → add appropriate HDRI
        - **CRITICAL**: Always check `if model_path:` before use. Use `import_polyhaven_model()` to import.
        - **WHEN TO USE PROCEDURAL**: Only when Poly Haven doesn't have the asset or needs custom variations.
        - **COMMON SEARCHES TO TRY**: "tree", "rock", "grass", "building", "chair", "plant", "fence", "car", "house", "sofa", "desk", "door", "window", "floor", "wall", "forest", "studio", "outdoor", "urban", "desert", "beach"
    
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
        exec_response = requests.post(BLENDER_SERVER_URL, json={"code": agent_data['code']}, timeout=200)
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