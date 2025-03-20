from .scene_tools import register_scene_tools
from .script_tools import register_script_tools
from .material_tools import register_material_tools
from .editor_tools import register_editor_tools
from .asset_tools import register_asset_tools
from .object_tools import register_object_tools
from .hyper3d_rodin_tools import register_hyper3d_tools

def register_all_tools(mcp):
    """Register all tools with the MCP server."""
    register_scene_tools(mcp)
    register_script_tools(mcp)
    register_material_tools(mcp)
    register_editor_tools(mcp)
    register_asset_tools(mcp)
    register_object_tools(mcp)
    register_hyper3d_tools(mcp)
