using Newtonsoft.Json.Linq;

namespace UnityMcpBridge.Editor.Models
{
    /// <summary>
    /// 定义Unity MCP工具的标准接口，用于扩展MCP Bridge功能
    /// Interface for Unity MCP tools that defines the contract for extending MCP Bridge functionality
    /// </summary>
    public interface IUnityMcpTool
    {
        /// <summary>
        /// 工具命令类型，必须是唯一的标识符
        /// The tool command type, must be a unique identifier
        /// </summary>
        string CommandType { get; }

        /// <summary>
        /// 工具描述，用于调试和文档
        /// Tool description for debugging and documentation
        /// </summary>
        string Description { get; }

        /// <summary>
        /// 处理MCP命令的主要方法
        /// Main method to handle MCP commands
        /// </summary>
        /// <param name="parameters">来自MCP客户端的参数 / Parameters from MCP client</param>
        /// <returns>执行结果，将序列化为JSON响应 / Result that will be serialized as JSON response</returns>
        object HandleCommand(JObject parameters);
    }
}