@echo off
title Gemini Animation Studio Launcher

echo ===================================================
echo   Gemini Animation Studio - AI 3D Pipeline
echo ===================================================

:: 1. Start Backend
echo Starting Backend Orchestrator...
start "Gemini Backend" cmd /k "cd backend && uvicorn main:app --reload --port 8000"

:: 2. Start Frontend
echo Starting Frontend Dashboard...
start "Gemini Frontend" cmd /k "cd frontend && npm run dev"

:: 3. Start Blender Bridge
echo Attempting to start Blender Bridge...
echo Using Blender at: "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
start "Blender MCP Server" cmd /k ""C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --python blender_bridge\blender_server.py"

echo.
echo All services launched!
echo Access the dashboard at: http://localhost:5173
echo.
pause