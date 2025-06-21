using System.Linq;
using Newtonsoft.Json.Linq;
using UnityMcpBridge.Editor.Models;
using UnityMcpBridge.Editor.Helpers;

namespace UnityMcpBridge.Editor.Tools
{
    /// <summary>
    /// 内置工具：列出所有已注册的MCP工具
    /// Built-in tool: List all registered MCP tools
    /// </summary>
    public class ListToolsTool : IUnityMcpTool
    {
        public string CommandType => "list_tools";
        
        public string Description => "列出所有已注册的Unity MCP工具，包括内置和自定义工具 / List all registered Unity MCP tools, including built-in and custom tools";
        
        public object HandleCommand(JObject parameters)
        {
            try
            {
                // 获取所有已注册的动态工具信息
                // Get information about all registered dynamic tools
                var dynamicTools = DynamicToolRegistry.GetRegisteredToolsInfo();
                
                // 获取内置工具信息
                // Get built-in tool information
                var builtInTools = new[]
                {
                    new { CommandType = "manage_script", Description = "管理C#脚本文件 / Manage C# script files", TypeName = "ManageScript" },
                    new { CommandType = "manage_scene", Description = "管理Unity场景 / Manage Unity scenes", TypeName = "ManageScene" },
                    new { CommandType = "manage_editor", Description = "编辑器控制和状态查询 / Editor control and status queries", TypeName = "ManageEditor" },
                    new { CommandType = "manage_gameobject", Description = "管理场景中的GameObjects / Manage GameObjects in scene", TypeName = "ManageGameObject" },
                    new { CommandType = "manage_asset", Description = "管理预制体和资源 / Manage prefabs and assets", TypeName = "ManageAsset" },
                    new { CommandType = "read_console", Description = "读取Unity控制台消息 / Read Unity console messages", TypeName = "ReadConsole" },
                    new { CommandType = "execute_menu_item", Description = "执行Unity菜单项 / Execute Unity menu items", TypeName = "ExecuteMenuItem" },
                    new { CommandType = "list_tools", Description = "列出所有已注册的工具 / List all registered tools", TypeName = "ListToolsTool" }
                };
                
                // 合并所有工具信息
                // Combine all tool information
                var allTools = builtInTools.Select(t => new
                {
                    commandType = t.CommandType,
                    description = t.Description,
                    typeName = t.TypeName,
                    isBuiltIn = true,
                    isDynamic = false
                }).Concat(dynamicTools.Select(t => new
                {
                    commandType = t.CommandType,
                    description = t.Description,
                    typeName = t.TypeName,
                    isBuiltIn = false,
                    isDynamic = true
                })).ToArray();
                
                return Response.Success(new
                {
                    tools = allTools,
                    totalCount = allTools.Length,
                    builtInCount = builtInTools.Length,
                    dynamicCount = dynamicTools.Count,
                    summary = new
                    {
                        builtInTools = builtInTools.Select(t => t.CommandType).ToArray(),
                        dynamicTools = dynamicTools.Select(t => t.CommandType).ToArray()
                    }
                });
            }
            catch (System.Exception ex)
            {
                return Response.Error($"获取工具列表时发生错误 / Error getting tool list: {ex.Message}");
            }
        }
    }
}