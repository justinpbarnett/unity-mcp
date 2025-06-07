# Claude Code Bridge for Unity MCP

**Extend Unity MCP to work with Claude Code, not just Claude Desktop!**

## What This Does

Unity MCP is amazing but only works with Claude Desktop. This bridge adds **Claude Code compatibility** with zero changes to the original Unity MCP code.

Now you can control Unity Editor from:
- ✅ **Claude Desktop** (original functionality)  
- ✅ **Claude Code** (new functionality!)

## Quick Demo

After setup, ask Claude Code:
- *"What objects are in my Unity scene?"*
- *"Create a player GameObject at (5, 0, 5)"*  
- *"Show me Unity console errors"*
- *"Add a Rigidbody to the Player"*

Claude Code will control Unity directly! 🎮

## Installation

1. **Install Unity MCP** (if not already done):
   ```
   Window > Package Manager > + > Add package from git URL:
   https://github.com/justinpbarnett/unity-mcp.git?path=/UnityMcpBridge
   ```

2. **Add these files** to your Unity project root:
   - `claude_code_bridge.py`
   - `start-unity-mcp-universal.bat` 
   - `requirements.txt` (updated with Flask)

3. **Run the launcher:**
   ```cmd
   start-unity-mcp-universal.bat
   ```

4. **Done!** Both Claude Desktop and Claude Code now work with Unity.

## How It Works

```
Original:  Claude Desktop → Unity MCP → Unity Editor
Added:     Claude Code → HTTP Bridge → Unity MCP → Unity Editor
```

The bridge creates HTTP endpoints that Claude Code can use, while preserving all original functionality.

## Files Included

| File | Purpose |
|------|---------|
| `claude_code_bridge.py` | HTTP API wrapper for Claude Code |
| `start-unity-mcp-universal.bat` | Launches both servers automatically |
| `requirements.txt` | Python dependencies (adds Flask) |
| `CLAUDE_CODE_INTEGRATION.md` | Detailed setup and usage guide |

## Tested With
- ✅ Unity 6000.0.37f1
- ✅ Windows 11
- ✅ Python 3.12
- ✅ Original Unity MCP functionality preserved
- ✅ Claude Code HTTP endpoints working

## Contributing to Unity MCP

This extension is ready for contribution to the main Unity MCP project. It:
- ✅ **Doesn't modify existing code**
- ✅ **Adds valuable functionality**  
- ✅ **Maintains full compatibility**
- ✅ **Is thoroughly tested**

## License
MIT (same as Unity MCP)
