using System.Collections.Generic;
using UnityMcpBridge.Editor.Models;

namespace UnityMcpBridge.Editor.Tools
{
    /// <summary>
    /// Provides metadata for built-in Unity MCP tools
    /// </summary>
    public static class BuiltinToolsMetadata
    {
        /// <summary>
        /// Get metadata for all built-in tools
        /// </summary>
        public static List<McpToolMetadata> GetAllBuiltinToolsMetadata()
        {
            return new List<McpToolMetadata>
            {
                GetManageScriptMetadata(),
                GetManageSceneMetadata(), 
                GetManageEditorMetadata(),
                GetManageGameObjectMetadata(),
                GetManageAssetMetadata(),
                GetReadConsoleMetadata(),
                GetExecuteMenuItemMetadata()
            };
        }

        public static McpToolMetadata GetManageScriptMetadata()
        {
            return new McpToolMetadata
            {
                CommandType = "manage_script",
                Description = "Manages C# scripts in Unity (create, read, update, delete). Make reference variables public for easier access in the Unity Editor.",
                ReturnDescription = "Dictionary with results ('success', 'message', 'data').",
                Parameters = new List<McpToolParameter>
                {
                    new McpToolParameter
                    {
                        Name = "action",
                        Type = "string",
                        Description = "Operation ('create', 'read', 'update', 'delete').",
                        Required = true
                    },
                    new McpToolParameter
                    {
                        Name = "name", 
                        Type = "string",
                        Description = "Script name (no .cs extension).",
                        Required = true
                    },
                    new McpToolParameter
                    {
                        Name = "path",
                        Type = "string", 
                        Description = "Asset path (default: \"Assets/\").",
                        Required = true
                    },
                    new McpToolParameter
                    {
                        Name = "contents",
                        Type = "string",
                        Description = "C# code for 'create'/'update'.",
                        Required = false
                    },
                    new McpToolParameter
                    {
                        Name = "script_type",
                        Type = "string",
                        Description = "Type hint (e.g., 'MonoBehaviour').",
                        Required = false
                    },
                    new McpToolParameter
                    {
                        Name = "namespace",
                        Type = "string", 
                        Description = "Script namespace.",
                        Required = false
                    }
                }
            };
        }

        public static McpToolMetadata GetManageSceneMetadata()
        {
            return new McpToolMetadata
            {
                CommandType = "manage_scene",
                Description = "Manages Unity scenes (create, load, save, get hierarchy).",
                ReturnDescription = "Dictionary with results ('success', 'message', 'data').",
                Parameters = new List<McpToolParameter>
                {
                    new McpToolParameter
                    {
                        Name = "action",
                        Type = "string",
                        Description = "Operation ('create', 'load', 'save', 'get_hierarchy', 'get_current').",
                        Required = true
                    },
                    new McpToolParameter
                    {
                        Name = "scene_name",
                        Type = "string",
                        Description = "Scene name or path.",
                        Required = false
                    },
                    new McpToolParameter
                    {
                        Name = "path",
                        Type = "string",
                        Description = "Scene path in Assets folder.",
                        Required = false
                    }
                }
            };
        }

        public static McpToolMetadata GetManageEditorMetadata()
        {
            return new McpToolMetadata
            {
                CommandType = "manage_editor", 
                Description = "Editor control and status queries (play, stop, pause, compile, get_status).",
                ReturnDescription = "Dictionary with results ('success', 'message', 'data').",
                Parameters = new List<McpToolParameter>
                {
                    new McpToolParameter
                    {
                        Name = "action",
                        Type = "string",
                        Description = "Operation ('play', 'stop', 'pause', 'compile', 'get_status').",
                        Required = true
                    }
                }
            };
        }

        public static McpToolMetadata GetManageGameObjectMetadata()
        {
            return new McpToolMetadata
            {
                CommandType = "manage_gameobject",
                Description = "Manages GameObjects in scene (create, delete, modify, find, get_components).",
                ReturnDescription = "Dictionary with results ('success', 'message', 'data').",
                Parameters = new List<McpToolParameter>
                {
                    new McpToolParameter
                    {
                        Name = "action",
                        Type = "string",
                        Description = "Operation ('create', 'delete', 'modify', 'find', 'get_components', 'add_component', 'remove_component').",
                        Required = true
                    },
                    new McpToolParameter
                    {
                        Name = "name",
                        Type = "string",
                        Description = "GameObject name.",
                        Required = false
                    },
                    new McpToolParameter
                    {
                        Name = "parent_name",
                        Type = "string",
                        Description = "Parent GameObject name.",
                        Required = false
                    },
                    new McpToolParameter
                    {
                        Name = "component_type",
                        Type = "string",
                        Description = "Component type name.",
                        Required = false
                    },
                    new McpToolParameter
                    {
                        Name = "properties",
                        Type = "object",
                        Description = "Properties to set on GameObject or component.",
                        Required = false
                    }
                }
            };
        }

        public static McpToolMetadata GetManageAssetMetadata()
        {
            return new McpToolMetadata
            {
                CommandType = "manage_asset",
                Description = "Manages prefabs and assets (create, delete, modify, import, export).",
                ReturnDescription = "Dictionary with results ('success', 'message', 'data').",
                Parameters = new List<McpToolParameter>
                {
                    new McpToolParameter
                    {
                        Name = "action",
                        Type = "string",
                        Description = "Operation ('create', 'delete', 'modify', 'import', 'export', 'get_info').",
                        Required = true
                    },
                    new McpToolParameter
                    {
                        Name = "asset_path",
                        Type = "string",
                        Description = "Asset path in project.",
                        Required = false
                    },
                    new McpToolParameter
                    {
                        Name = "name",
                        Type = "string",
                        Description = "Asset name.",
                        Required = false
                    },
                    new McpToolParameter
                    {
                        Name = "source_path",
                        Type = "string", 
                        Description = "Source file path for import.",
                        Required = false
                    }
                }
            };
        }

        public static McpToolMetadata GetReadConsoleMetadata()
        {
            return new McpToolMetadata
            {
                CommandType = "read_console",
                Description = "Reads Unity console messages (logs, warnings, errors) and can clear the console.",
                ReturnDescription = "Dictionary with results ('success', 'message', 'data').",
                Parameters = new List<McpToolParameter>
                {
                    new McpToolParameter
                    {
                        Name = "action",
                        Type = "string",
                        Description = "Operation ('read', 'clear').",
                        Required = true
                    },
                    new McpToolParameter
                    {
                        Name = "max_entries",
                        Type = "integer",
                        Description = "Maximum number of console entries to return.",
                        Required = false,
                        DefaultValue = 100
                    }
                }
            };
        }

        public static McpToolMetadata GetExecuteMenuItemMetadata()
        {
            return new McpToolMetadata
            {
                CommandType = "execute_menu_item",
                Description = "Executes Unity menu items by menu path.",
                ReturnDescription = "Dictionary with results ('success', 'message', 'data').",
                Parameters = new List<McpToolParameter>
                {
                    new McpToolParameter
                    {
                        Name = "menu_path",
                        Type = "string",
                        Description = "Full menu path (e.g., 'Assets/Create/C# Script').",
                        Required = true
                    }
                }
            };
        }
    }
}