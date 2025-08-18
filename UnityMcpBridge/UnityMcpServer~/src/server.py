from mcp.server.fastmcp import FastMCP, Context, Image
import logging
import sys
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List
from config import config
from tools import register_all_tools
from unity_connection import get_unity_connection, UnityConnection
from pathlib import Path
import os
import hashlib

# Configure logging: strictly stderr/file only (never stdout)
stderr_handler = logging.StreamHandler(stream=sys.stderr)
stderr_handler.setFormatter(logging.Formatter(config.log_format))

handlers = [stderr_handler]
logger = logging.getLogger("unity-mcp-server")
logger.setLevel(getattr(logging, config.log_level))
for h in list(logger.handlers):
    logger.removeHandler(h)
for h in list(logging.getLogger().handlers):
    logging.getLogger().removeHandler(h)
logger.addHandler(stderr_handler)
logging.getLogger().addHandler(stderr_handler)
logging.getLogger().setLevel(getattr(logging, config.log_level))

# File logging to avoid stdout interference with MCP stdio
try:
    log_dir = Path.home() / ".unity-mcp"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(str(log_dir / "server.log"), maxBytes=5*1024*1024, backupCount=3)
    file_handler.setFormatter(logging.Formatter(config.log_format))
    file_handler.setLevel(getattr(logging, config.log_level))
    logger.addHandler(file_handler)
    # Prevent duplicate propagation to root handlers
    logger.propagate = False
except Exception:
    # If file logging setup fails, continue with stderr logging only
    pass

# Global connection state
_unity_connection: UnityConnection = None

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Handle server startup and shutdown."""
    global _unity_connection
    logger.info("Unity MCP Server starting up")
    try:
        _unity_connection = get_unity_connection()
        logger.info("Connected to Unity on startup")
    except Exception as e:
        logger.warning(f"Could not connect to Unity on startup: {str(e)}")
        _unity_connection = None
    try:
        # Yield the connection object so it can be attached to the context
        # The key 'bridge' matches how tools like read_console expect to access it (ctx.bridge)
        yield {"bridge": _unity_connection}
    finally:
        if _unity_connection:
            _unity_connection.disconnect()
            _unity_connection = None
        logger.info("Unity MCP Server shut down")

# Initialize MCP server
mcp = FastMCP(
    "unity-mcp-server",
    description="Unity Editor integration via Model Context Protocol",
    lifespan=server_lifespan
)

# Register all tools
register_all_tools(mcp)

# Asset Creation Strategy

@mcp.prompt()
def asset_creation_strategy() -> str:
    """Guide for discovering and using Unity MCP tools effectively."""
    return (
        "Available Unity MCP Server Tools:\n\n"
        "- `manage_editor`: Controls editor state and queries info.\n"
        "- `execute_menu_item`: Executes Unity Editor menu items by path.\n"
        "- `read_console`: Reads or clears Unity console messages, with filtering options.\n"
        "- `manage_scene`: Manages scenes.\n"
        "- `manage_gameobject`: Manages GameObjects in the scene.\n"
        "- `manage_script`: Manages C# script files.\n"
        "- `manage_asset`: Manages prefabs and assets.\n"
        "- `manage_shader`: Manages shaders.\n\n"
        "Tips:\n"
        "- Prefer structured script edits over raw text ranges.\n"
        "- For script edits, common aliases are accepted: class_name→className; method_name/target/method→methodName; new_method/newMethod/content→replacement; anchor_method→afterMethodName/beforeMethodName based on position.\n"
        "- You can pass uri or full file path for scripts; the server normalizes to name/path.\n"
    )

# Resources support: list and read Unity scripts/files
# Guard for older MCP versions without 'capabilities' API
if hasattr(mcp, "capabilities"):
    @mcp.capabilities(resources={"listChanged": True})
    class _:
        pass

PROJECT_ROOT = Path(os.environ.get("UNITY_PROJECT_ROOT", Path.cwd())).resolve()
ASSETS_ROOT = (PROJECT_ROOT / "Assets").resolve()

def _resolve_safe_path_from_uri(uri: str) -> Path | None:
    raw: str | None = None
    if uri.startswith("unity://path/"):
        raw = uri[len("unity://path/"):]
    elif uri.startswith("file://"):
        raw = uri[len("file://"):]
    elif uri.startswith("Assets/"):
        raw = uri
    if raw is None:
        return None
    p = (PROJECT_ROOT / raw).resolve()
    try:
        p.relative_to(PROJECT_ROOT)
    except ValueError:
        return None
    return p


if hasattr(mcp, "resource") and hasattr(getattr(mcp, "resource"), "list"):
    @mcp.resource.list()
    def list_resources(ctx: Context) -> list[dict]:
        assets = []
        try:
            for p in ASSETS_ROOT.rglob("*.cs"):
                rel = p.relative_to(PROJECT_ROOT).as_posix()
                assets.append({"uri": f"unity://path/{rel}", "name": p.name})
        except Exception:
            pass
        # Add spec resource so clients (e.g., Claude Desktop) can learn the exact contract
        assets.append({
            "uri": "unity://spec/script-edits",
            "name": "Unity Script Edits – Required JSON"
        })
        return assets

if hasattr(mcp, "resource") and hasattr(getattr(mcp, "resource"), "read"):
    @mcp.resource.read()
    def read_resource(ctx: Context, uri: str) -> dict:
        # Serve script-edits spec
        if uri == "unity://spec/script-edits":
            spec_json = (
                '{\n'
                '  "name": "Unity MCP — Script Edits v1",\n'
                '  "target_tool": "script_apply_edits",\n'
                '  "canonical_rules": {\n'
                '    "always_use": ["op","className","methodName","replacement","afterMethodName","beforeMethodName"],\n'
                '    "never_use": ["new_method","anchor_method","content","newText"],\n'
                '    "defaults": {\n'
                '      "className": "← server will default to \'name\' when omitted",\n'
                '      "position": "end"\n'
                '    }\n'
                '  },\n'
                '  "ops": [\n'
                '    {"op":"replace_method","required":["className","methodName","replacement"],"optional":["returnType","parametersSignature","attributesContains"]},\n'
                '    {"op":"insert_method","required":["className","replacement"],"position":{"enum":["start","end","after","before"],"after_requires":"afterMethodName","before_requires":"beforeMethodName"}},\n'
                '    {"op":"delete_method","required":["className","methodName"]},\n'
                '    {"op":"anchor_insert","required":["anchor","text"],"notes":"regex; position=before|after"}\n'
                '  ],\n'
                '  "apply_text_edits_recipe": {\n'
                '    "step1_read": { "tool": "resources/read", "args": {"uri": "unity://path/Assets/Scripts/Interaction/SmartReach.cs"} },\n'
                '    "step2_apply": {\n'
                '      "tool": "manage_script",\n'
                '      "args": {\n'
                '        "action": "apply_text_edits",\n'
                '        "name": "SmartReach", "path": "Assets/Scripts/Interaction",\n'
                '        "edits": [{"startLine": 42, "startCol": 1, "endLine": 42, "endCol": 1, "newText": "[MyAttr]\\n"}],\n'
                '        "precondition_sha256": "<sha-from-step1>",\n'
                '        "options": {"refresh": "immediate", "validate": "standard"}\n'
                '      }\n'
                '    },\n'
                '    "note": "newText is for apply_text_edits ranges only; use replacement in script_apply_edits ops."\n'
                '  },\n'
                '  "examples": [\n'
                '    {\n'
                '      "title": "Replace a method",\n'
                '      "args": {\n'
                '        "name": "SmartReach",\n'
                '        "path": "Assets/Scripts/Interaction",\n'
                '        "edits": [\n'
                '          {"op":"replace_method","className":"SmartReach","methodName":"HasTarget","replacement":"public bool HasTarget() { return currentTarget != null; }"}\n'
                '        ],\n'
                '        "options": { "validate": "standard", "refresh": "immediate" }\n'
                '      }\n'
                '    },\n'
                '    {\n'
                '      "title": "Insert a method after another",\n'
                '      "args": {\n'
                '        "name": "SmartReach",\n'
                '        "path": "Assets/Scripts/Interaction",\n'
                '        "edits": [\n'
                '          {"op":"insert_method","className":"SmartReach","replacement":"public void PrintSeries() { Debug.Log(seriesName); }","position":"after","afterMethodName":"GetCurrentTarget"}\n'
                '        ]\n'
                '      }\n'
                '    }\n'
                '  ]\n'
                '}\n'
            )
            return {"mimeType": "application/json", "text": spec_json}
        p = _resolve_safe_path_from_uri(uri)
        if not p or not p.exists():
            return {"mimeType": "text/plain", "text": f"Resource not found: {uri}"}
        try:
            text = p.read_text(encoding="utf-8")
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            return {"mimeType": "text/plain", "text": text, "metadata": {"sha256": sha}}
        except Exception as e:
            return {"mimeType": "text/plain", "text": f"Error reading resource: {e}"}

# Run the server
if __name__ == "__main__":
    mcp.run(transport='stdio')
