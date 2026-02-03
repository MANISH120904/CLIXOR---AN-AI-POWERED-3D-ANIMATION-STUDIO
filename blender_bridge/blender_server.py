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

PORT = 8081

# Ensure render output directory exists
# We use the user's home directory to avoid PermissionDenied errors in Program Files
RENDER_DIR = os.path.join(os.path.expanduser("~"), "GeminiAnimationStudio", "renders")
if not os.path.exists(RENDER_DIR):
    try:
        os.makedirs(RENDER_DIR)
    except OSError:
        # Fallback to a temp dir if for some reason that fails
        RENDER_DIR = os.path.join(os.getenv('TEMP'), "GeminiAnimationStudio_renders")
        os.makedirs(RENDER_DIR, exist_ok=True)

print(f"Renders will be saved to: {RENDER_DIR}")

# Global queue for thread-safe communication
execution_queue = queue.Queue()

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

                # Wait for Main Thread to finish execution (timeout 60s)
                completed = done_event.wait(timeout=60)

                if not completed:
                    response = {"success": False, "error": "Execution timed out (Main thread didn't process task)", "output": ""}
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
                # 1. Execute Code
                exec(code, {'bpy': bpy, 'render_dir': RENDER_DIR})
                
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