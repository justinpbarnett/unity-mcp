using Newtonsoft.Json.Linq;

namespace UnityMcpBridge.Editor.Models
{
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
        /// Main method to handle MCP commands
        /// </summary>
        /// <param name="parameters">Parameters from MCP client</param>
        /// <returns>Result that will be serialized as JSON response</returns>
        object HandleCommand(JObject parameters);
    }
}