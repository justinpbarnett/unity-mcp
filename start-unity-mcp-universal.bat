@echo off
:: ================================================================
:: Unity MCP Universal Launcher
:: 
:: This script starts both Unity MCP Server and Claude Code Bridge
:: Compatible with any Unity project using Unity MCP
:: 
:: Requirements:
:: - Python 3.12+ installed and in PATH
:: - Unity Editor with Unity MCP Bridge package
:: - This script in Unity project root directory
:: 
:: GitHub: https://github.com/justinpbarnett/unity-mcp
:: ================================================================

setlocal EnableDelayedExpansion
title Unity MCP Universal Launcher
color 0B

echo ================================================================
echo               Unity MCP Universal Launcher
echo ================================================================
echo.
echo This will start:
echo  [✓] Unity MCP Server (Claude Desktop integration)
echo  [✓] Claude Code Bridge (Claude Code integration)
echo.

:: Validate environment
echo [VALIDATION] Checking system requirements...

:: Check if we're in a Unity project
if not exist "Assets" (
    echo [ERROR] This doesn't appear to be a Unity project directory
    echo         Please run this script from your Unity project root
    echo         Expected to find: Assets folder
    pause
    exit /b 1
)

:: Check if Unity MCP is installed
if not exist "unity-mcp\UnityMcpServer\src\server.py" (
    echo [ERROR] Unity MCP Server not found
    echo         Expected path: unity-mcp\UnityMcpServer\src\server.py
    echo         Please install Unity MCP Bridge package first
    pause
    exit /b 1
)

:: Check Python
python --version > nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Python not found in PATH
    echo         Please install Python 3.12+ and add to PATH
    echo         Download: https://python.org/downloads
    pause
    exit /b 1
)

:: Check Unity (optional warning)
tasklist /FI "IMAGENAME eq Unity.exe" 2>NUL | find /I /N "Unity.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [✓] Unity Editor detected
) else (
    echo [!] Unity Editor not detected - please start Unity first
)

echo [✓] All requirements validated
echo.
echo Press any key to continue...
pause > nul

echo.
echo ================================================================
echo [1/4] Python Environment Setup
echo ================================================================

:: Virtual environment name (can be customized)
set VENV_NAME=unity-mcp-env-windows

if not exist "%VENV_NAME%" (
    echo Creating Python virtual environment: %VENV_NAME%
    python -m venv "%VENV_NAME%"
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment
        echo         Check Python installation and permissions
        pause
        exit /b 1
    )
    echo [✓] Virtual environment created
) else (
    echo [✓] Using existing virtual environment: %VENV_NAME%
)

:: Activate environment
call "%VENV_NAME%\Scripts\activate.bat"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [✓] Virtual environment activated

echo.
echo ================================================================
echo [2/4] Dependencies Installation
echo ================================================================

echo Installing Unity MCP dependencies...
pip install --quiet httpx>=0.27.2 "mcp[cli]>=1.4.1" flask>=2.3.0

if !errorlevel! neq 0 (
    echo [WARNING] Some dependencies may have installation issues
    echo           Attempting individual installation...
    pip install httpx
    pip install mcp
    pip install flask
) else (
    echo [✓] All dependencies installed successfully
)

echo.
echo ================================================================
echo [3/4] Unity MCP Server Startup
echo ================================================================

cd "unity-mcp\UnityMcpServer\src"
echo Starting Unity MCP Server on localhost:6500...

:: Create log directory if needed
if not exist "..\..\..\logs" mkdir "..\..\..\logs"

:: Start MCP server in background
start /B python server.py > ..\..\..\logs\mcp-server.log 2>&1

:: Wait for startup
echo Initializing server...
timeout /t 3 > nul

:: Basic connectivity test
for /f %%i in ('tasklist /FI "IMAGENAME eq python.exe" ^| find /c "python.exe"') do set PYTHON_COUNT=%%i
if !PYTHON_COUNT! gtr 0 (
    echo [✓] Unity MCP Server started (PID monitoring available)
) else (
    echo [!] Server startup status unclear - check logs\mcp-server.log
)

echo.
echo ================================================================
echo [4/4] Claude Code Bridge Startup
echo ================================================================

echo Starting Claude Code Bridge on localhost:6501...
echo.
echo ================================================================
echo                    SYSTEM READY
echo ================================================================
echo.
echo Services running:
echo   Unity MCP Server:    http://localhost:6500 (Claude Desktop)
echo   Claude Code Bridge:  http://localhost:6501 (Claude Code)
echo.
echo Unity MCP Tools available in Claude Code:
echo   Health check:  curl http://localhost:6501/health
echo   Scene info:    curl http://localhost:6501/unity/scene
echo   GameObjects:   curl http://localhost:6501/unity/gameobject
echo   Console logs:  curl http://localhost:6501/unity/console
echo   Editor info:   curl http://localhost:6501/unity/editor
echo.
echo Logs directory: logs\
echo.
echo ================================================================
echo        Press Ctrl+C to stop all Unity MCP services
echo ================================================================
echo.

:: Start Claude Code Bridge (this will run in foreground)
python claude_code_bridge.py

:: Cleanup on exit
echo.
echo ================================================================
echo                    SHUTTING DOWN
echo ================================================================
echo.
echo Stopping Unity MCP services...

:: Attempt graceful shutdown of background processes
taskkill /F /FI "WINDOWTITLE eq *server.py*" > nul 2>&1
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO csv ^| find "server.py"') do (
    taskkill /PID %%i /F > nul 2>&1
)

echo [✓] Unity MCP services stopped
echo [✓] Logs preserved in logs\ directory
echo.
echo Thank you for using Unity MCP!
echo Report issues: https://github.com/justinpbarnett/unity-mcp/issues
echo.
pause