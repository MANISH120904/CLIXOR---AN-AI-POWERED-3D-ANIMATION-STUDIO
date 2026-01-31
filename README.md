# Gemini Animation Studio 🎬

A collaborative AI studio where **Director**, **Tech Artist**, and **Vision QA** agents work together to create 3D animations in Blender using the Gemini 3 API.

## 🏗️ Architecture
- **Frontend:** React + Vite (Dashboard)
- **Backend:** FastAPI (Orchestrator)
- **Blender Bridge:** Python MCP Server (Runs inside Blender)

## 🚀 Setup & Installation

### 1. Configure API Key
Open `backend/.env` and paste your Google Gemini API Key:
```
GOOGLE_API_KEY=your_api_key_here
```

### 2. Dependencies
The system requires:
- **Node.js** (for Frontend)
- **Python** (for Backend)
- **Blender** (Add it to your system PATH or update the script)

### 3. Running the Studio

Double-click **`start_studio.bat`** to launch everything!

**Or run manually:**

**Terminal 1 (Backend):**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

**Terminal 3 (Blender Server):**
```bash
# Ensure 'blender' is in your PATH
blender --background --python blender_bridge/blender_server.py
```
*Note: The Blender server listens on port 8081.*

## 🎮 Usage
1. Open the frontend (http://localhost:5173).
2. Enter a prompt (e.g., "A spinning red cube with a blue light").
3. Watch the agents plan, code, and execute the animation!
