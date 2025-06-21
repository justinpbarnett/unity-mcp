using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityMcpBridge.Editor.Models;

namespace UnityMcpBridge.Editor.Tools
{
    /// <summary>
    /// 动态工具注册系统，通过反射发现和注册所有实现了IUnityMcpTool接口的类
    /// Dynamic tool registry system that discovers and registers all classes implementing IUnityMcpTool interface via reflection
    /// </summary>
    public static class DynamicToolRegistry
    {
        private static readonly Dictionary<string, IUnityMcpTool> _registeredTools = new();
        private static bool _isInitialized = false;

        /// <summary>
        /// 初始化动态工具注册系统
        /// Initialize the dynamic tool registry system
        /// </summary>
        public static void Initialize()
        {
            if (_isInitialized)
                return;

            try
            {
                DiscoverAndRegisterTools();
                _isInitialized = true;
                Debug.Log($"[DynamicToolRegistry] Initialized with {_registeredTools.Count} tools");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[DynamicToolRegistry] Failed to initialize: {ex.Message}\n{ex.StackTrace}");
            }
        }

        /// <summary>
        /// 通过反射发现并注册所有工具
        /// Discover and register all tools via reflection
        /// </summary>
        private static void DiscoverAndRegisterTools()
        {
            // 获取当前应用程序域中的所有程序集
            // Get all assemblies in the current application domain
            Assembly[] assemblies = AppDomain.CurrentDomain.GetAssemblies();

            foreach (Assembly assembly in assemblies)
            {
                try
                {
                    // 跳过系统程序集以提高性能
                    // Skip system assemblies for performance
                    if (IsSystemAssembly(assembly))
                        continue;

                    // 查找实现了IUnityMcpTool接口的所有类型
                    // Find all types that implement IUnityMcpTool interface
                    Type[] toolTypes = assembly.GetTypes()
                        .Where(type => 
                            typeof(IUnityMcpTool).IsAssignableFrom(type) && 
                            !type.IsInterface && 
                            !type.IsAbstract)
                        .ToArray();

                    foreach (Type toolType in toolTypes)
                    {
                        RegisterTool(toolType);
                    }
                }
                catch (Exception ex)
                {
                    // 某些程序集可能无法访问，记录但不中断整个过程
                    // Some assemblies might not be accessible, log but don't break the entire process
                    Debug.LogWarning($"[DynamicToolRegistry] Failed to scan assembly {assembly.GetName().Name}: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// 注册单个工具类型
        /// Register a single tool type
        /// </summary>
        private static void RegisterTool(Type toolType)
        {
            try
            {
                // 创建工具实例
                // Create tool instance
                IUnityMcpTool toolInstance = (IUnityMcpTool)Activator.CreateInstance(toolType);

                // 检查命令类型是否有效
                // Check if command type is valid
                if (string.IsNullOrEmpty(toolInstance.CommandType))
                {
                    Debug.LogError($"[DynamicToolRegistry] Tool {toolType.Name} has empty CommandType");
                    return;
                }

                // 检查是否存在重复的命令类型
                // Check for duplicate command types
                if (_registeredTools.ContainsKey(toolInstance.CommandType))
                {
                    Debug.LogError($"[DynamicToolRegistry] Duplicate command type '{toolInstance.CommandType}' found in {toolType.Name}. Previous tool: {_registeredTools[toolInstance.CommandType].GetType().Name}");
                    return;
                }

                // 注册工具
                // Register the tool
                _registeredTools[toolInstance.CommandType] = toolInstance;
                Debug.Log($"[DynamicToolRegistry] Registered tool '{toolInstance.CommandType}' from {toolType.Name} - {toolInstance.Description}");
            }
            catch (Exception ex)
            {
                Debug.LogError($"[DynamicToolRegistry] Failed to register tool {toolType.Name}: {ex.Message}\n{ex.StackTrace}");
            }
        }

        /// <summary>
        /// 判断程序集是否为系统程序集
        /// Determine if an assembly is a system assembly
        /// </summary>
        private static bool IsSystemAssembly(Assembly assembly)
        {
            string assemblyName = assembly.GetName().Name;
            return assemblyName.StartsWith("System.") ||
                   assemblyName.StartsWith("Microsoft.") ||
                   assemblyName.StartsWith("UnityEngine") ||
                   assemblyName.StartsWith("UnityEditor") ||
                   assemblyName.StartsWith("mscorlib") ||
                   assemblyName.StartsWith("netstandard") ||
                   assemblyName.StartsWith("Newtonsoft.");
        }

        /// <summary>
        /// 根据命令类型获取工具处理器
        /// Get tool handler by command type
        /// </summary>
        /// <param name="commandType">命令类型 / Command type</param>
        /// <returns>工具实例，如果未找到则返回null / Tool instance, or null if not found</returns>
        public static IUnityMcpTool GetTool(string commandType)
        {
            if (!_isInitialized)
                Initialize();

            return _registeredTools.TryGetValue(commandType, out IUnityMcpTool tool) ? tool : null;
        }

        /// <summary>
        /// 执行指定命令类型的工具
        /// Execute tool for specified command type
        /// </summary>
        /// <param name="commandType">命令类型 / Command type</param>
        /// <param name="parameters">参数 / Parameters</param>
        /// <returns>执行结果 / Execution result</returns>
        public static object ExecuteTool(string commandType, JObject parameters)
        {
            IUnityMcpTool tool = GetTool(commandType);
            if (tool == null)
            {
                throw new ArgumentException($"未找到命令类型 '{commandType}' 的工具处理器 / No tool handler found for command type '{commandType}'");
            }

            return tool.HandleCommand(parameters);
        }

        /// <summary>
        /// 获取所有已注册的工具信息
        /// Get information about all registered tools
        /// </summary>
        /// <returns>工具信息列表 / List of tool information</returns>
        public static List<(string CommandType, string Description, string TypeName)> GetRegisteredToolsInfo()
        {
            if (!_isInitialized)
                Initialize();

            return _registeredTools.Values
                .Select(tool => (tool.CommandType, tool.Description, tool.GetType().Name))
                .OrderBy(info => info.CommandType)
                .ToList();
        }

        /// <summary>
        /// 强制重新扫描和注册工具（用于开发时的热重载）
        /// Force re-scan and register tools (for hot reload during development)
        /// </summary>
        public static void ForceReload()
        {
            _registeredTools.Clear();
            _isInitialized = false;
            Initialize();
        }
    }
}