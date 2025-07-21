# File: C:\Users\admin\AppData\Local\Programs\UnityMCP\UnityMcpServer\src\tools\__init__.py

# --- 导入所有工具的注册函数 ---
from .manage_script import register_manage_script_tools
from .manage_scene import register_manage_scene_tools
from .manage_editor import register_manage_editor_tools
from .manage_gameobject import register_manage_gameobject_tools
from .manage_asset import register_manage_asset_tools
from .manage_shader import register_manage_shader_tools
from .read_console import register_read_console_tools
from .execute_menu_item import register_execute_menu_item_tools
from .fix_asmdef_references import register_fix_asmdef_references_tools



def register_all_tools(mcp):
    """Register all refactored tools with the MCP server."""
    print("Registering Unity MCP Server refactored tools...")
    register_manage_script_tools(mcp)
    register_manage_scene_tools(mcp)
    register_manage_editor_tools(mcp)
    register_manage_gameobject_tools(mcp)
    register_manage_asset_tools(mcp)
    register_manage_shader_tools(mcp)
    register_read_console_tools(mcp)
    register_execute_menu_item_tools(mcp)
    register_fix_asmdef_references_tools(mcp)
    print("Unity MCP Server tool registration complete.")

