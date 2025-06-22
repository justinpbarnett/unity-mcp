using Newtonsoft.Json.Linq;
using System.Collections.Generic;

namespace UnityMcpBridge.Editor.Models
{
    /// <summary>
    /// Parameter definition for MCP tools
    /// </summary>
    public class McpToolParameter
    {
        public string Name { get; set; }
        public string Type { get; set; }
        public string Description { get; set; }
        public bool Required { get; set; }
        public object DefaultValue { get; set; }
    }

    /// <summary>
    /// Complete tool metadata for MCP server registration
    /// </summary>
    public class McpToolMetadata
    {
        public string CommandType { get; set; }
        public string Description { get; set; }
        public List<McpToolParameter> Parameters { get; set; } = new List<McpToolParameter>();
        public string ReturnDescription { get; set; }
    }

    /// <summary>
    /// Interface for Unity MCP tools that defines the contract for extending MCP Bridge functionality
    /// </summary>
    public interface IUnityMcpTool
    {
        /// <summary>
        /// The tool command type, must be a unique identifier
        /// </summary>
        string CommandType { get; }

        /// <summary>
        /// Tool description for debugging and documentation
        /// </summary>
        string Description { get; }

        /// <summary>
        /// Get complete metadata for MCP server registration
        /// </summary>
        /// <returns>Complete tool metadata including parameters</returns>
        McpToolMetadata GetToolMetadata();

        /// <summary>
        /// Main method to handle MCP commands
        /// </summary>
        /// <param name="parameters">Parameters from MCP client</param>
        /// <returns>Result that will be serialized as JSON response</returns>
        object HandleCommand(JObject parameters);
    }
}