from .manage_script_edits import register_manage_script_edits_tools
from .manage_script import register_manage_script_tools
from .manage_scene import register_manage_scene_tools
from .manage_editor import register_manage_editor_tools
from .manage_gameobject import register_manage_gameobject_tools
from .manage_asset import register_manage_asset_tools
from .manage_shader import register_manage_shader_tools
from .read_console import register_read_console_tools
from .execute_menu_item import register_execute_menu_item_tools

def register_all_tools(mcp):
    """Register all refactored tools with the MCP server."""
    # Note: Do not print to stdout; Claude treats stdout as MCP JSON. Use logging.
    # Prefer the surgical edits tool so LLMs discover it first
    register_manage_script_edits_tools(mcp)
    register_manage_script_tools(mcp)
    register_manage_scene_tools(mcp)
    register_manage_editor_tools(mcp)
    register_manage_gameobject_tools(mcp)
    register_manage_asset_tools(mcp)
    register_manage_shader_tools(mcp)
    register_read_console_tools(mcp)
    register_execute_menu_item_tools(mcp)
    # Do not print to stdout here either.
