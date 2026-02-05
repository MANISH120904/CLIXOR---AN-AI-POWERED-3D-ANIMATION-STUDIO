import bpy
import http.server
import socketserver
import json
import sys
import io
import traceback
import os
import threading
import queue
import time
import contextlib
import urllib.request
import ssl

PORT = 8081

# Ensure render output directory exists
# We use the user's home directory to avoid PermissionDenied errors in Program Files
RENDER_DIR = os.path.join(os.path.expanduser("~"), "GeminiAnimationStudio", "renders")
ASSETS_DIR = os.path.join(RENDER_DIR, "assets")

if not os.path.exists(RENDER_DIR):
    try:
        os.makedirs(RENDER_DIR)
    except OSError:
        RENDER_DIR = os.path.join(os.getenv('TEMP'), "GeminiAnimationStudio_renders")
        os.makedirs(RENDER_DIR, exist_ok=True)

if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR, exist_ok=True)

print(f"Renders will be saved to: {RENDER_DIR}")
print(f"Assets will be saved to: {ASSETS_DIR}")

# Global queue for thread-safe communication
execution_queue = queue.Queue()

def download_polyhaven_asset(search_term, asset_type='hdris'):
    """
    Searches and downloads an asset from Poly Haven.
    Returns the absolute file path of the downloaded asset.
    For models, returns path to the best available format (Blend > GLTF).
    """
    print(f"[PolyHaven] Searching for '{search_term}' in '{asset_type}'...")
    
    # SSL Context (ignore verification for simplicity in some envs)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    headers = {'User-Agent': 'GeminiAnimationStudio/1.0'}
    
    try:
        # 1. Search (Fetch all and filter)
        req = urllib.request.Request(f"https://api.polyhaven.com/assets?t={asset_type}", headers=headers)
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode())
            
        matches = [k for k in data.keys() if search_term.lower() in k.lower() or search_term.lower() in str(data[k].get('tags', [])).lower()]
        
        if not matches:
            print(f"[PolyHaven] No matches found for '{search_term}'.")
            return None
            
        asset_id = matches[0] # Pick first match
        print(f"[PolyHaven] Found match: {asset_id}")
        
        # 2. Get Details
        req_file = urllib.request.Request(f"https://api.polyhaven.com/files/{asset_id}", headers=headers)
        with urllib.request.urlopen(req_file, context=ctx) as response:
            file_data = json.loads(response.read().decode())
            
        # 3. Find Download URL (Priority: Blend > GLTF > HDR/EXR)
        download_url = None
        filename = f"{asset_id}"
        
        if asset_type == 'models' or ('blend' in file_data and 'gltf' in file_data):
            # Models: Prefer Blend files (more control), then GLTF
            # Structure: file_data['blend']['4k']['blend']['url']
            
            # 1. Try Blend - prefer 2k/4k resolutions
            if 'blend' in file_data and isinstance(file_data['blend'], dict):
                for res in ['2k', '4k', '1k', '8k']:
                    if res in file_data['blend']:
                        resolution_data = file_data['blend'][res]
                        if isinstance(resolution_data, dict) and 'blend' in resolution_data:
                            blend_info = resolution_data['blend']
                            if isinstance(blend_info, dict) and 'url' in blend_info:
                                download_url = blend_info['url']
                                filename += ".blend"
                                print(f"[PolyHaven] Using Blend {res}")
                                break

            # 2. Try GLTF/GLB (Better compatibility)
            if not download_url and 'gltf' in file_data and isinstance(file_data['gltf'], dict):
                for res in ['2k', '4k', '1k', '8k']:
                    if res in file_data['gltf']:
                        resolution_data = file_data['gltf'][res]
                        if isinstance(resolution_data, dict) and 'gltf' in resolution_data:
                            gltf_info = resolution_data['gltf']
                            if isinstance(gltf_info, dict) and 'url' in gltf_info:
                                download_url = gltf_info['url']
                                filename += ".gltf"
                                print(f"[PolyHaven] Using GLTF {res}")
                                break

        elif 'hdri' in file_data:
            # HDRI: Try 2k, then 1k, then 4k
            for res in ['2k', '1k', '4k']:
                if res in file_data['hdri']:
                    # Try exr, then hdr
                    if 'exr' in file_data['hdri'][res]:
                        download_url = file_data['hdri'][res]['exr']['url']
                        filename += f"_{res}.exr"
                        print(f"[PolyHaven] Using HDRI {res} EXR format")
                        break
                    elif 'hdr' in file_data['hdri'][res]:
                        download_url = file_data['hdri'][res]['hdr']['url']
                        filename += f"_{res}.hdr"
                        print(f"[PolyHaven] Using HDRI {res} HDR format")
                        break
                if download_url: 
                    break
         
        elif 'texture' in file_data:
             print("[PolyHaven] Texture downloading is experimental. Consider using model-based approach.")
             return None

        if not download_url:
            print(f"[PolyHaven] Could not find suitable download URL. Available formats: {list(file_data.keys())}")
            return None
            
        # 4. Download
        dest_path = os.path.join(ASSETS_DIR, filename)
        if os.path.exists(dest_path):
            print(f"[PolyHaven] Asset already cached: {dest_path}")
            return dest_path
            
        print(f"[PolyHaven] Downloading ({filename})...")
        with urllib.request.urlopen(download_url, context=ctx) as dl_resp, open(dest_path, 'wb') as out_file:
            out_file.write(dl_resp.read())
            
        print(f"[PolyHaven] ✓ Saved to {dest_path}")
        return dest_path

    except Exception as e:
        print(f"[PolyHaven] Error: {e}")
        traceback.print_exc()
        return None

def import_polyhaven_model(model_path):
    """
    Imports a downloaded Poly Haven model (Blend or GLTF) into the scene.
    Returns the imported object(s).
    """
    if not model_path or not os.path.exists(model_path):
        print(f"[PolyHaven] Model path invalid: {model_path}")
        return None
        
    try:
        if model_path.endswith('.blend'):
            # Import from Blend file - try to import all objects
            print(f"[PolyHaven] Importing Blend model...")
            with bpy.data.libraries.load(model_path, link=False) as (data_from, data_to):
                data_to.objects = data_from.objects
            imported_objs = data_to.objects
            for obj in imported_objs:
                if obj is not None:
                    bpy.context.collection.objects.link(obj)
            print(f"[PolyHaven] ✓ Imported {len(imported_objs)} object(s) from Blend file")
            return imported_objs if imported_objs else None
            
        elif model_path.endswith(('.glb', '.gltf')):
            # Import GLTF/GLB
            print(f"[PolyHaven] Importing GLTF model...")
            bpy.ops.import_scene.gltf(filepath=model_path)
            # Get the last imported objects
            imported_objs = [obj for obj in bpy.context.selected_objects]
            print(f"[PolyHaven] ✓ Imported GLTF model ({len(imported_objs)} objects)")
            return imported_objs if imported_objs else None
        else:
            print(f"[PolyHaven] Unsupported file format: {model_path}")
            return None
            
    except Exception as e:
        print(f"[PolyHaven] Import error: {e}")
        traceback.print_exc()
        return None


# Ensure helpers are available in the __main__ module for any code that tries to import it
import __main__
__main__.download_polyhaven_asset = download_polyhaven_asset
__main__.import_polyhaven_model = import_polyhaven_model
__main__.bpy = bpy
__main__.render_dir = RENDER_DIR

class BlenderRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/execute':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                code = data.get('code', '')

                print(f"[DEBUG] Received code ({len(code)} chars). Queuing...")

                # Create a result container and event to wait for completion
                result_container = {}
                done_event = threading.Event()

                # Put task in queue for the Main Thread
                execution_queue.put((code, result_container, done_event))

                # Wait for Main Thread to finish execution (timeout 180s for complex operations)
                completed = done_event.wait(timeout=180)

                if not completed:
                    response = {"success": False, "error": "Execution timed out (Main thread didn't process task within 180s)", "output": ""}
                else:
                    response = result_container

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                print(f"Server Error: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))

def execute_queued_tasks():
    """Checked by Blender's timer every 0.1s to run tasks on Main Thread"""
    while not execution_queue.empty():
        try:
            code, result_container, done_event = execution_queue.get_nowait()
        except queue.Empty:
            break

        print(f"[DEBUG] Executing on Main Thread...")
        # print(f"Code Preview: {code[:50]}...") 

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        success = False

        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            try:
                # Validate code before execution
                _validate_and_fix_code(code)
                
                # 1. Execute Code
                exec(code, {
                    'bpy': bpy, 
                    'render_dir': RENDER_DIR, 
                    'download_polyhaven_asset': download_polyhaven_asset,
                    'import_polyhaven_model': import_polyhaven_model,
                    '__name__': '__main__'
                })
                
                # 2. Force Global Viewport & UI Update
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        area.tag_redraw()
                        if area.type == 'VIEW_3D':
                            # Force shading mode to Material Preview to see colors/lights
                            for space in area.spaces:
                                if space.type == 'VIEW_3D':
                                    space.shading.type = 'MATERIAL'
                
                success = True
            except TypeError as e:
                if "'builtin_function_or_method' object is not iterable" in str(e):
                    print(f"[ERROR] Iterator Error: Attempted to iterate over a method/function instead of a collection.")
                    print(f"[HINT] Check your code for: for x in obj.indices, for x in obj.locations, etc.")
                    print(f"[HINT] These are method calls, not collections. Check Blender API for correct attributes.")
                    traceback.print_exc()
                else:
                    traceback.print_exc()
                success = False
            except RuntimeError as e:
                if "Node type" in str(e) and "undefined" in str(e):
                    print(f"[ERROR] Shader Node Error: {e}")
                    print(f"[HINT] This node type doesn't exist in this Blender version.")
                    print(f"[HINT] Common replacements:")
                    print(f"       - ShaderNodeTexMusgrave -> ShaderNodeTexNoise")
                    print(f"       - ShaderNodeTexCellular -> ShaderNodeTexNoise")
                    traceback.print_exc()
                else:
                    traceback.print_exc()
                success = False
            except AttributeError as e:
                if "animation_data" in str(e):
                    print(f"[ERROR] Animation Data Error: {e}")
                    print(f"[HINT] 'RigidBodyWorld' doesn't have 'animation_data' attribute.")
                    print(f"[HINT] For rigid body physics, use keyframes on object locations/rotations instead.")
                    traceback.print_exc()
                else:
                    traceback.print_exc()
                success = False
            except Exception:
                traceback.print_exc()
                success = False

        # Store result
        result_container.update({
            "success": success,
            "output": stdout_capture.getvalue(),
            "error": stderr_capture.getvalue()
        })
        
        # Signal the server thread that we are done
        done_event.set()
        
    return 0.1  # Run this function again in 0.1 seconds

def _validate_and_fix_code(code: str):
    """Pre-execution validation to catch common Blender API issues"""
    # Check for problematic patterns
    problematic_patterns = [
        (r'for\s+\w+\s+in\s+\w+\.indices', 'for x in obj.indices - indices is not iterable'),
        (r'for\s+\w+\s+in\s+\w+\.locations(?!\s*=)', 'for x in obj.locations - locations is not iterable, use obj.location'),
        (r'ShaderNodeTexMusgrave', 'ShaderNodeTexMusgrave - this node type does not exist, use ShaderNodeTexNoise'),
        (r'ShaderNodeTexCellular', 'ShaderNodeTexCellular - this node type does not exist, use ShaderNodeTexNoise'),
    ]
    
    import re
    for pattern, hint in problematic_patterns:
        if re.search(pattern, code):
            print(f"[WARNING] Potential issue detected: {hint}")
            print(f"[WARNING] Code may fail during execution")
    
    # Verify rigidbody_world animation_data access is safe
    if 'rigidbody_world' in code and 'animation_data' in code:
        if 'hasattr' not in code and 'if bpy.context.scene.rigidbody_world' not in code:
            print(f"[WARNING] Unsafe rigidbody_world.animation_data access detected")
            print(f"[WARNING] This attribute may not exist on RigidBodyWorld objects")


def start_server():
    """Runs the HTTP server in a separate thread"""
    try:
        with socketserver.TCPServer(("", PORT), BlenderRequestHandler) as httpd:
            print(f"Blender MCP Server running on port {PORT} (Threaded)...")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 10048:
            print(f"\n[ERROR] Port {PORT} is already in use!")
            print("This means the server is already running from a previous session.")
            print("PLEASE RESTART BLENDER to fix this.\n")
        else:
            print(f"Server Error: {e}")

if __name__ == "__main__":
    # 1. Clear default cube startup
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 2. Register the task runner with Blender's Timer system
    bpy.app.timers.register(execute_queued_tasks)

    # 3. Start the Server Thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print("Blender Bridge Initialized. UI is responsive.")