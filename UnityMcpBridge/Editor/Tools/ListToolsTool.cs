using System.Linq;
using Newtonsoft.Json.Linq;
using UnityMcpBridge.Editor.Models;
using UnityMcpBridge.Editor.Helpers;

namespace UnityMcpBridge.Editor.Tools
{
    /// <summary>
    /// Built-in tool: List all registered MCP tools
    /// </summary>
    public class ListToolsTool : IUnityMcpTool
    {
        public string CommandType => "list_tools";
        
        public string Description => "List all registered Unity MCP tools, including built-in and custom tools";
        
        public object HandleCommand(JObject parameters)
        {
            try
            {
                // Get information about all registered dynamic tools
                var dynamicTools = DynamicToolRegistry.GetRegisteredToolsInfo();
                
                // Get built-in tool information
                var builtInTools = new[]
                {
                    new { CommandType = "manage_script", Description = "Manage C# script files", TypeName = "ManageScript" },
                    new { CommandType = "manage_scene", Description = "Manage Unity scenes", TypeName = "ManageScene" },
                    new { CommandType = "manage_editor", Description = "Editor control and status queries", TypeName = "ManageEditor" },
                    new { CommandType = "manage_gameobject", Description = "Manage GameObjects in scene", TypeName = "ManageGameObject" },
                    new { CommandType = "manage_asset", Description = "Manage prefabs and assets", TypeName = "ManageAsset" },
                    new { CommandType = "read_console", Description = "Read Unity console messages", TypeName = "ReadConsole" },
                    new { CommandType = "execute_menu_item", Description = "Execute Unity menu items", TypeName = "ExecuteMenuItem" },
                };
                
                // Combine all tool information
                var allTools = builtInTools.Select(t => new
                {
                    commandType = t.CommandType,
                    description = t.Description,
                    typeName = t.TypeName
                }).Concat(dynamicTools.Select(t => new
                {
                    commandType = t.CommandType,
                    description = t.Description,
                    typeName = t.TypeName
                })).ToArray();
                
                return Response.Success("Successfully retrieved tool list", new
                {
                    tools = allTools,
                    totalCount = allTools.Length
                });
            }
            catch (System.Exception ex)
            {
                return Response.Error($"Error getting tool list: {ex.Message}");
            }
        }
    }
}