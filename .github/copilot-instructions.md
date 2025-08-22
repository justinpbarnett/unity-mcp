# MCP for Unity Development Instructions

**ALWAYS follow these instructions first and fallback to additional search and context gathering only if the information in these instructions is incomplete or found to be in error.**

## Overview

MCP for Unity is a bridge connecting LLMs to Unity Editor via the Model Context Protocol (MCP). It consists of:
- **Unity MCP Bridge**: C# Unity package running inside the Unity Editor
- **MCP Server**: Python server that communicates between Unity Bridge and MCP Clients
- **Development Tools**: Scripts for testing and deploying changes
- **Test Suite**: Unity Test Runner integration for validation

## Bootstrap and Build

### Prerequisites Installation
```bash
# Install Python 3.12+ if not available
# Check: python3 --version

# Install uv package manager
pip install uv

# Verify installation
uv --version
```

### Build the Python MCP Server
```bash
cd UnityMcpBridge/UnityMcpServer~/src
uv sync
```
**Timing**: First run takes < 5 seconds. Subsequent runs take < 1 second.
**NEVER CANCEL**: Wait for completion - this installs all Python dependencies.

### Test Server Startup
```bash
cd UnityMcpBridge/UnityMcpServer~/src
export PATH=$PATH:~/.local/bin  # If uv not in PATH
timeout 10s uv run server.py
```
**Expected Output**: Server starts, shows "MCP for Unity Server starting up", then "Failed to connect to Unity" (normal when Unity not running).

## Testing

### Unity Tests via GitHub Actions
Tests run automatically on:
- Pushes to main branch
- Changes to `TestProjects/UnityMCPTests/**` or `UnityMcpBridge/Editor/**`

**Unity Test Configuration**:
- Unity 2021.3.45f1
- Test Mode: editmode only
- Project: `TestProjects/UnityMCPTests`

**NEVER CANCEL**: Unity tests can take 10-15 minutes to complete. The GitHub Actions workflow has proper timeouts configured.

### Manual Python Tests
```bash
cd UnityMcpBridge/UnityMcpServer~/src
uv run python -c "import mcp; print('MCP available')"
uv run python -c "import tools.manage_script; print('Tools import successfully')"
```

### Unity Test Project Structure
Test project location: `TestProjects/UnityMCPTests/`
- **Test Scripts**: `Assets/Tests/EditMode/CommandRegistryTests.cs`
- **Assembly Definition**: `Assets/Tests/EditMode/MCPForUnityTests.Editor.asmdef`
- **Test Framework**: NUnit testing framework
- **Test Types**: EditMode tests only (no PlayMode tests currently)

**Key Test Cases**:
- Command registry validation
- Tool handler verification  
- Unity Bridge integration tests

### Run Unity Tests Locally (Requires Unity Editor)
**Prerequisites**:
- Unity 2021.3+ installed
- Unity Test Runner package
- Project opened in Unity Editor

**Manual Testing**:
1. Open `TestProjects/UnityMCPTests` in Unity Editor
2. Go to `Window > General > Test Runner`
3. Click `Run All` in EditMode tab
4. Verify all tests pass

**Expected Test Output**: All CommandRegistryTests should pass, validating tool registration.

## Development Tools

### Package Source Switching
Use `mcp_source.py` to switch between package sources for testing:
```bash
python3 mcp_source.py --help
python3 mcp_source.py --choice 1  # Upstream main
python3 mcp_source.py --choice 2  # Remote current branch  
python3 mcp_source.py --choice 3  # Local workspace
```

### Development Deployment (Windows Only)
**Scripts**: `deploy-dev.bat` and `restore-dev.bat`

**Prerequisites**:
- Unity Editor with MCP for Unity package installed
- MCP Server installed via package auto-setup

**Workflow**:
1. Make changes to source code
2. Run `deploy-dev.bat` (creates backup, deploys to installation locations)
3. Restart Unity Editor to load new Bridge code
4. Restart MCP clients to use new Server code
5. Test changes
6. Use `restore-dev.bat` to rollback if needed

**Timing**: Deployment takes 10-30 seconds depending on file sizes.

## Validation Requirements

### Critical Validation Steps
**ALWAYS run these after making changes**:

1. **Python Server Build Validation**:
   ```bash
   cd UnityMcpBridge/UnityMcpServer~/src
   uv sync  # Should complete in < 5 seconds for incremental builds
   ```

2. **Server Startup Test**:
   ```bash
   cd UnityMcpBridge/UnityMcpServer~/src
   timeout 10s uv run server.py  # Should start without Python errors
   ```

3. **Tools Import Test**:
   ```bash
   cd UnityMcpBridge/UnityMcpServer~/src
   uv run python -c "from tools import *; print('All tools imported successfully')"
   ```

### Manual Scenario Testing
When making changes, **ALWAYS test these scenarios**:

1. **Server Connection Flow**:
   ```bash
   cd UnityMcpBridge/UnityMcpServer~/src
   timeout 10s uv run server.py
   # Expected: Starts, shows registration, then "Failed to connect to Unity"
   ```

2. **Development Script Testing**:
   ```bash
   python3 mcp_source.py --help  # Should show usage in < 1 second
   ```

3. **Package Validation**:
   ```bash
   python3 -c "import json; json.load(open('UnityMcpBridge/package.json')); print('package.json valid')"
   python3 -c "import tomllib; f=open('UnityMcpBridge/UnityMcpServer~/src/pyproject.toml','rb'); tomllib.load(f); print('pyproject.toml valid')"
   ```

4. **Dependency Resolution Test**:
   ```bash
   cd UnityMcpBridge/UnityMcpServer~/src
   uv run python -c "
   import tools.manage_script
   import tools.manage_gameobject  
   import tools.manage_scene
   import tools.manage_asset
   print('All core tools import successfully')
   "
   ```

5. **Virtual Environment Integrity**:
   ```bash
   cd UnityMcpBridge/UnityMcpServer~/src
   uv run python -c "import sys; print('Python path:', sys.executable)"
   # Should show .venv path, not system Python
   ```

## Build Timing and Timeouts

**Set these timeout values for build commands**:

- **uv sync**: 60 seconds first run, 30 seconds subsequent
- **Unity tests**: 1800 seconds (30 minutes) - NEVER CANCEL
- **Server startup**: 60 seconds for testing
- **Development deployment**: 120 seconds (2 minutes)

**CRITICAL**: NEVER CANCEL builds or long-running commands. Unity compilation and testing can take substantial time.

## Common File Locations

### Key Directories
- **Unity Bridge**: `UnityMcpBridge/Editor/` - C# Unity Editor scripts
- **Python Server**: `UnityMcpBridge/UnityMcpServer~/src/` - MCP server implementation
- **Tools**: `UnityMcpBridge/UnityMcpServer~/src/tools/` - MCP tool implementations
- **Tests**: `TestProjects/UnityMCPTests/Assets/Tests/EditMode/` - Unity test scripts
- **CI/CD**: `.github/workflows/` - GitHub Actions workflows

### Important Files
- `UnityMcpBridge/package.json` - Unity package manifest
- `UnityMcpBridge/UnityMcpServer~/src/pyproject.toml` - Python project configuration
- `UnityMcpBridge/UnityMcpServer~/src/server.py` - Main MCP server entry point
- `TestProjects/UnityMCPTests/Assets/Tests/EditMode/CommandRegistryTests.cs` - Core Unity tests

### Configuration Files
- `UnityMcpBridge/UnityMcpServer~/src/uv.lock` - Python dependency lock file
- `.github/workflows/unity-tests.yml` - Unity test automation
- `.github/workflows/bump-version.yml` - Version management

## Working Effectively

### Code Changes
1. **Python Server Changes**:
   - Edit files in `UnityMcpBridge/UnityMcpServer~/src/`
   - Run `uv sync` after dependency changes
   - Test with `uv run server.py`

2. **Unity Bridge Changes**:  
   - Edit C# files in `UnityMcpBridge/Editor/`
   - Use development deployment scripts for testing
   - Restart Unity Editor after changes

3. **Tool Development**:
   - Add new tools in `UnityMcpBridge/UnityMcpServer~/src/tools/`
   - Follow existing tool patterns (`manage_*.py`)
   - Register tools in `server.py`

### Testing Strategy
1. Always run Python tests before Unity tests
2. Use development deployment for integration testing
3. Run CI tests for full validation
4. Test both server startup and tool functionality

### Version Management
- Version is managed in two files:
  - `UnityMcpBridge/package.json` 
  - `UnityMcpBridge/UnityMcpServer~/src/pyproject.toml`
- Use `.github/workflows/bump-version.yml` for version updates
- Versions must be synchronized between Unity and Python components

## Commands That Do NOT Work

- **Unity Editor CLI**: Unity Editor cannot be run in headless mode for this project's test suite on most systems
- **Windows batch scripts on Linux/macOS**: Development deployment scripts (`deploy-dev.bat`, `restore-dev.bat`) are Windows-only
- **Direct Unity package installation**: Package must be installed via Unity Package Manager or OpenUPM
- **Running server without uv**: Direct `python server.py` will fail - must use `uv run server.py`
- **Cross-platform file paths**: Development scripts use Windows path conventions (backslashes)

## Edge Cases and Limitations

### Platform-Specific Behavior
- **Windows**: Development deployment scripts work fully
- **macOS/Linux**: Use manual deployment or symbolic links for testing
- **CI Environment**: Unity tests require license configuration

### Network and Port Issues
- **Port 6400**: Default Unity Bridge communication port
- **Port 6500**: Default MCP server port  
- **Firewall**: May block initial connections - not necessarily an error
- **Multiple Unity instances**: May cause port conflicts

### Virtual Environment Considerations
- **uv.lock**: Contains exact dependency versions - do not modify manually
- **.venv directory**: Created automatically by uv - do not version control
- **Path isolation**: Commands must use `uv run` prefix for proper isolation

## Troubleshooting

### Common Issues
- **"uv not found"**: Add `export PATH=$PATH:~/.local/bin` or install uv globally
- **"Connection refused"**: Expected when Unity Editor not running - not an error
- **Permission errors on deployment**: Use Administrator mode on Windows
- **Unity test failures**: May require Unity license in CI environment

### Build Failures
- Check Python syntax in server files
- Verify all imports are available  
- Ensure uv.lock is not corrupted
- Validate JSON syntax in configuration files

### Validation Failures
- Always test server startup after changes
- Verify tool imports work correctly
- Check that Unity package format is valid
- Test development scripts before relying on them

## Expected Command Outputs

### Successful Server Start
```
Registering MCP for Unity Server refactored tools...
MCP for Unity Server tool registration complete.
2025-XX-XX XX:XX:XX,XXX - mcp-for-unity-server - INFO - MCP for Unity Server starting up
2025-XX-XX XX:XX:XX,XXX - mcp-for-unity-server - INFO - Creating new Unity connection
2025-XX-XX XX:XX:XX,XXX - mcp-for-unity-server - INFO - No port registry found; using default port 6400
2025-XX-XX XX:XX:XX,XXX - mcp-for-unity-server - ERROR - Failed to connect to Unity: [Errno 111] Connection refused
```

### Successful Tool Import
```
All tools imported successfully
```

## Complete End-to-End Validation

**Run this complete validation sequence after making any changes**:

```bash
# Navigate to repository root
cd /path/to/unity-mcp

# 1. Validate Python environment
python3 --version  # Should be 3.12+
export PATH=$PATH:~/.local/bin  # Add if needed
uv --version

# 2. Build and test Python server
cd UnityMcpBridge/UnityMcpServer~/src
uv sync  # Should complete in < 5 seconds
timeout 10s uv run server.py  # Should start and show expected output

# 3. Test tool imports
uv run python -c "from tools import *; print('All tools imported successfully')"

# 4. Validate configuration files
cd ../../..  # Back to repo root
python3 -c "import json; json.load(open('UnityMcpBridge/package.json')); print('package.json valid')"
python3 -c "import tomllib; f=open('UnityMcpBridge/UnityMcpServer~/src/pyproject.toml','rb'); tomllib.load(f); print('pyproject.toml valid')"

# 5. Test development tools
python3 mcp_source.py --help  # Should show usage quickly

# 6. Verify virtual environment integrity
cd UnityMcpBridge/UnityMcpServer~/src
uv run python -c "import sys; assert '.venv' in sys.executable; print('Virtual environment OK')"

echo "All validations passed - ready for development!"
```

**Total validation time**: < 30 seconds

### Validation Success Indicators
- ✅ All `uv sync` operations complete without errors
- ✅ Server starts and shows "MCP for Unity Server starting up"
- ✅ All tool imports succeed without ImportError
- ✅ JSON/TOML files parse without syntax errors
- ✅ Virtual environment is active and isolated
- ✅ Help commands respond quickly (< 1 second)

### Successful Complete Validation Output
```
Python 3.12.3
uv 0.8.13
Resolved 28 packages in 7ms
Audited 26 packages in 0.05ms
Registering MCP for Unity Server refactored tools...
MCP for Unity Server tool registration complete.
2025-XX-XX XX:XX:XX,XXX - mcp-for-unity-server - INFO - MCP for Unity Server starting up
2025-XX-XX XX:XX:XX,XXX - mcp-for-unity-server - INFO - Creating new Unity connection
2025-XX-XX XX:XX:XX,XXX - mcp-for-unity-server - INFO - No port registry found; using default port 6400
2025-XX-XX XX:XX:XX,XXX - mcp-for-unity-server - ERROR - Failed to connect to Unity: [Errno 111] Connection refused
Server test completed
All tools imported successfully
package.json valid
pyproject.toml valid
mcp_source.py help OK
Virtual environment OK
All validations passed - ready for development!
```