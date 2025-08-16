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
        "Available Unity MCP Server Tools:\\n\\n"
        "- `manage_editor`: Controls editor state and queries info.\\n"
        "- `execute_menu_item`: Executes Unity Editor menu items by path.\\n"
        "- `read_console`: Reads or clears Unity console messages, with filtering options.\\n"
        "- `manage_scene`: Manages scenes.\\n"
        "- `manage_gameobject`: Manages GameObjects in the scene.\\n"
        "- `manage_script`: Manages C# script files.\\n"
        "- `manage_asset`: Manages prefabs and assets.\\n"
        "- `manage_shader`: Manages shaders.\\n\\n"
        "Tips:\\n"
        "- Create prefabs for reusable GameObjects.\\n"
        "- Always include a camera and main light in your scenes.\\n"
    )

# Resources support: list and read Unity scripts/files
@mcp.capabilities(resources={"listChanged": True})
class _:
    pass

import os
import hashlib

def _unity_assets_root() -> str:
    # Heuristic: from the Unity project root (one level up from Library/ProjectSettings), 'Assets'
    # Here, assume server runs from repo; let clients pass absolute paths under project too.
    return None

def _safe_path(uri: str) -> str | None:
    # URIs: unity://path/Assets/... or file:///absolute
    if uri.startswith("unity://path/"):
        p = uri[len("unity://path/"):]
        return p
    if uri.startswith("file://"):
        return uri[len("file://"):]
    # Minimal tolerance for plain Assets/... paths
    if uri.startswith("Assets/"):
        return uri
    return None

@mcp.resource.list()
def list_resources(ctx: Context) -> list[dict]:
    # Lightweight: expose only C# under Assets by default
    assets = []
    try:
        root = os.getcwd()
        for base, _, files in os.walk(os.path.join(root, "Assets")):
            for f in files:
                if f.endswith(".cs"):
                    rel = os.path.relpath(os.path.join(base, f), root).replace("\\", "/")
                    assets.append({
                        "uri": f"unity://path/{rel}",
                        "name": os.path.basename(rel)
                    })
    except Exception:
        pass
    return assets

@mcp.resource.read()
def read_resource(ctx: Context, uri: str) -> dict:
    path = _safe_path(uri)
    if not path or not os.path.exists(path):
        return {"mimeType": "text/plain", "text": f"Resource not found: {uri}"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return {"mimeType": "text/plain", "text": text, "metadata": {"sha256": sha}}
    except Exception as e:
        return {"mimeType": "text/plain", "text": f"Error reading resource: {e}"}

# Run the server
if __name__ == "__main__":
    mcp.run(transport='stdio')
