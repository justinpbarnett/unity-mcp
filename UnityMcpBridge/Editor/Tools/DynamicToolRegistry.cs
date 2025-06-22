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
    /// Dynamic tool registry system that discovers and registers all classes implementing IUnityMcpTool interface via reflection
    /// </summary>
    public static class DynamicToolRegistry
    {
        private static readonly Dictionary<string, IUnityMcpTool> _registeredTools = new();
        private static bool _isInitialized = false;

        /// <summary>
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
        /// Discover and register all tools via reflection
        /// </summary>
        private static void DiscoverAndRegisterTools()
        {
            // Get all assemblies in the current application domain
            Assembly[] assemblies = AppDomain.CurrentDomain.GetAssemblies();

            foreach (Assembly assembly in assemblies)
            {
                try
                {
                    // Skip system assemblies for performance
                    if (IsSystemAssembly(assembly))
                        continue;

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
                    // Some assemblies might not be accessible, log but don't break the entire process
                    Debug.LogWarning($"[DynamicToolRegistry] Failed to scan assembly {assembly.GetName().Name}: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Register a single tool type
        /// </summary>
        private static void RegisterTool(Type toolType)
        {
            try
            {
                // Create tool instance
                IUnityMcpTool toolInstance = (IUnityMcpTool)Activator.CreateInstance(toolType);

                // Check if command type is valid
                if (string.IsNullOrEmpty(toolInstance.CommandType))
                {
                    Debug.LogError($"[DynamicToolRegistry] Tool {toolType.Name} has empty CommandType");
                    return;
                }

                // Check for duplicate command types
                if (_registeredTools.ContainsKey(toolInstance.CommandType))
                {
                    Debug.LogError($"[DynamicToolRegistry] Duplicate command type '{toolInstance.CommandType}' found in {toolType.Name}. Previous tool: {_registeredTools[toolInstance.CommandType].GetType().Name}");
                    return;
                }

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
        /// Get tool handler by command type
        /// </summary>
        /// <param name="commandType">Command type</param>
        /// <returns>Tool instance, or null if not found</returns>
        public static IUnityMcpTool GetTool(string commandType)
        {
            if (!_isInitialized)
                Initialize();

            return _registeredTools.TryGetValue(commandType, out IUnityMcpTool tool) ? tool : null;
        }

        /// <summary>
        /// Execute tool for specified command type
        /// </summary>
        /// <param name="commandType">Command type</param>
        /// <param name="parameters">Parameters</param>
        /// <returns>Execution result</returns>
        public static object ExecuteTool(string commandType, JObject parameters)
        {
            IUnityMcpTool tool = GetTool(commandType);
            if (tool == null)
            {
                throw new ArgumentException($"No tool handler found for command type '{commandType}'");
            }

            return tool.HandleCommand(parameters);
        }

        /// <summary>
        /// Get information about all registered tools
        /// </summary>
        /// <returns>List of tool information</returns>
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