using System.Linq;
using Newtonsoft.Json.Linq;
using UnityMcpBridge.Editor.Models;
using UnityMcpBridge.Editor.Helpers;
using System.Collections.Generic;

namespace UnityMcpBridge.Editor.Tools
{
    /// <summary>
    /// Built-in tool: List all registered MCP tools with complete metadata
    /// </summary>
    public class ListToolsTool : IUnityMcpTool
    {
        public string CommandType => "list_tools";
        
        public string Description => "List all registered Unity MCP tools with complete metadata for MCP server registration";

        public McpToolMetadata GetToolMetadata()
        {
            return new McpToolMetadata
            {
                CommandType = "list_tools",
                Description = "List all registered Unity MCP tools with complete metadata for MCP server registration",
                ReturnDescription = "Dictionary with complete tool metadata including parameters and descriptions",
                Parameters = new List<McpToolParameter>()
            };
        }
        
        public object HandleCommand(JObject parameters)
        {
            try
            {
                // Get complete metadata for all built-in tools
                var builtinToolsMetadata = BuiltinToolsMetadata.GetAllBuiltinToolsMetadata();
                
                // Get metadata for all registered dynamic tools
                var dynamicToolsMetadata = new List<McpToolMetadata>();
                var dynamicTools = DynamicToolRegistry.GetRegisteredToolsInfo();
                
                foreach (var (commandType, description, typeName) in dynamicTools)
                {
                    // Skip list_tools to avoid self-reference
                    if (commandType == "list_tools")
                        continue;
                                 
                    var tool = DynamicToolRegistry.GetTool(commandType);
                    if (tool != null)
                    {
                        dynamicToolsMetadata.Add(tool.GetToolMetadata());
                    }
                }
                
                // Combine all tool metadata
                var allToolsMetadata = new List<McpToolMetadata>();
                allToolsMetadata.AddRange(builtinToolsMetadata);
                allToolsMetadata.AddRange(dynamicToolsMetadata);
                
                return Response.Success("Successfully retrieved complete tool metadata", new
                {
                    tools = allToolsMetadata,
                    totalCount = allToolsMetadata.Count,
                    builtinCount = builtinToolsMetadata.Count,
                    dynamicCount = dynamicToolsMetadata.Count
                });
            }
            catch (System.Exception ex)
            {
                return Response.Error($"Error getting tool metadata: {ex.Message}");
            }
        }
    }
}