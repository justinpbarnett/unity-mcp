using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityMcpBridge.Editor.Helpers;
using UnityMcpBridge.Editor.Models;

namespace UnityMcpBridge.Editor
{
    /// <summary>
    /// Headless mode extensions for Unity MCP Bridge.
    /// Provides enhanced support for -batchmode Unity operations.
    /// </summary>
    public static partial class UnityMcpBridge
    {
        private static bool isHeadlessMode = false;
        private static string headlessLogPath = "/tmp/unity-mcp-headless.log";
        
        /// <summary>
        /// Check if Unity is running in headless batch mode.
        /// </summary>
        public static bool IsHeadlessMode()
        {
            return Application.isBatchMode || isHeadlessMode;
        }
        
        /// <summary>
        /// Initialize headless mode with enhanced logging and configuration.
        /// </summary>
        [InitializeOnLoadMethod]
        public static void InitializeHeadlessMode()
        {
            if (Application.isBatchMode)
            {
                isHeadlessMode = true;
                ConfigureHeadlessLogging();
                LogHeadless("Unity MCP Bridge initialized in headless mode");
                
                // Auto-start bridge in headless mode if environment variable is set
                if (Environment.GetEnvironmentVariable("UNITY_MCP_AUTOSTART") == "true")
                {
                    StartHeadless();
                }
            }
        }
        
        /// <summary>
        /// Start the MCP bridge optimized for headless operation.
        /// </summary>
        public static void StartHeadless()
        {
            try
            {
                LogHeadless("Starting Unity MCP Bridge in headless mode");
                
                // Use environment variable for port if available
                string portEnv = Environment.GetEnvironmentVariable("UNITY_MCP_PORT");
                if (!string.IsNullOrEmpty(portEnv) && int.TryParse(portEnv, out int envPort))
                {
                    currentUnityPort = envPort;
                }
                
                Start();
                
                if (IsRunning)
                {
                    LogHeadless($"Unity MCP Bridge started successfully on port {currentUnityPort}");
                    
                    // Write port info to file for discovery
                    WriteHeadlessPortInfo();
                }
                else
                {
                    LogHeadless("Failed to start Unity MCP Bridge", LogType.Error);
                }
            }
            catch (Exception ex)
            {
                LogHeadless($"Error starting headless mode: {ex.Message}", LogType.Error);
                throw;
            }
        }
        
        /// <summary>
        /// Configure enhanced logging for headless operations.
        /// </summary>
        private static void ConfigureHeadlessLogging()
        {
            try
            {
                // Set log path from environment or use default
                string logPathEnv = Environment.GetEnvironmentVariable("UNITY_MCP_LOG_PATH");
                if (!string.IsNullOrEmpty(logPathEnv))
                {
                    headlessLogPath = logPathEnv;
                }
                
                // Ensure log directory exists
                string logDir = Path.GetDirectoryName(headlessLogPath);
                if (!string.IsNullOrEmpty(logDir) && !Directory.Exists(logDir))
                {
                    Directory.CreateDirectory(logDir);
                }
                
                // Enable verbose console logging in headless mode
                Debug.unityLogger.logEnabled = true;
                
                LogHeadless("Headless logging configured");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to configure headless logging: {ex.Message}");
            }
        }
        
        /// <summary>
        /// Enhanced logging for headless operations.
        /// </summary>
        private static void LogHeadless(string message, LogType logType = LogType.Log)
        {
            string timestamp = DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss.fff");
            string logMessage = $"[{timestamp}] [HEADLESS] {message}";
            
            // Console output
            switch (logType)
            {
                case LogType.Error:
                    Debug.LogError(logMessage);
                    break;
                case LogType.Warning:
                    Debug.LogWarning(logMessage);
                    break;
                default:
                    Debug.Log(logMessage);
                    break;
            }
            
            // File output
            try
            {
                File.AppendAllText(headlessLogPath, logMessage + Environment.NewLine);
            }
            catch
            {
                // Silent fail to avoid recursive logging issues
            }
        }
        
        /// <summary>
        /// Write port information to file for headless server discovery.
        /// </summary>
        private static void WriteHeadlessPortInfo()
        {
            try
            {
                var portInfo = new
                {
                    unity_port = currentUnityPort,
                    pid = System.Diagnostics.Process.GetCurrentProcess().Id,
                    started_at = DateTime.UtcNow.ToString("O"),
                    headless_mode = true,
                    project_path = Application.dataPath
                };
                
                string portInfoPath = "/tmp/unity-mcp-port.json";
                string portInfoEnv = Environment.GetEnvironmentVariable("UNITY_MCP_PORT_INFO_PATH");
                if (!string.IsNullOrEmpty(portInfoEnv))
                {
                    portInfoPath = portInfoEnv;
                }
                
                string json = EditorJsonUtility.ToJson(portInfo, true);
                File.WriteAllText(portInfoPath, json);
                
                LogHeadless($"Port info written to {portInfoPath}");
            }
            catch (Exception ex)
            {
                LogHeadless($"Failed to write port info: {ex.Message}", LogType.Warning);
            }
        }
        
        /// <summary>
        /// Execute a command with enhanced error handling for headless mode.
        /// </summary>
        public static string ExecuteHeadlessCommand(Command command)
        {
            try
            {
                LogHeadless($"Executing headless command: {command.type}");
                
                // Use the existing command execution but with enhanced logging
                string result = ExecuteCommand(command);
                
                LogHeadless($"Command {command.type} completed successfully");
                return result;
            }
            catch (Exception ex)
            {
                string errorMessage = $"Headless command {command.type} failed: {ex.Message}";
                LogHeadless(errorMessage, LogType.Error);
                
                // Return structured error response
                var errorResponse = new
                {
                    status = "error",
                    error = ex.Message,
                    command = command.type,
                    headless_mode = true,
                    timestamp = DateTime.UtcNow.ToString("O")
                };
                
                return EditorJsonUtility.ToJson(errorResponse);
            }
        }
        
        /// <summary>
        /// Shutdown method for headless mode with cleanup.
        /// </summary>
        public static void ShutdownHeadless()
        {
            try
            {
                LogHeadless("Shutting down Unity MCP Bridge in headless mode");
                
                // Stop the bridge
                Stop();
                
                // Clean up port info file
                try
                {
                    string portInfoPath = "/tmp/unity-mcp-port.json";
                    string portInfoEnv = Environment.GetEnvironmentVariable("UNITY_MCP_PORT_INFO_PATH");
                    if (!string.IsNullOrEmpty(portInfoEnv))
                    {
                        portInfoPath = portInfoEnv;
                    }
                    
                    if (File.Exists(portInfoPath))
                    {
                        File.Delete(portInfoPath);
                    }
                }
                catch (Exception ex)
                {
                    LogHeadless($"Failed to clean up port info file: {ex.Message}", LogType.Warning);
                }
                
                LogHeadless("Headless shutdown completed");
            }
            catch (Exception ex)
            {
                LogHeadless($"Error during headless shutdown: {ex.Message}", LogType.Error);
            }
        }
        
        /// <summary>
        /// Get detailed status for headless operations.
        /// </summary>
        public static Dictionary<string, object> GetHeadlessStatus()
        {
            return new Dictionary<string, object>
            {
                ["headless_mode"] = IsHeadlessMode(),
                ["is_running"] = IsRunning,
                ["current_port"] = GetCurrentPort(),
                ["batch_mode"] = Application.isBatchMode,
                ["platform"] = Application.platform.ToString(),
                ["unity_version"] = Application.unityVersion,
                ["project_path"] = Application.dataPath,
                ["log_path"] = headlessLogPath,
                ["pid"] = System.Diagnostics.Process.GetCurrentProcess().Id,
                ["uptime"] = Time.realtimeSinceStartup,
                ["timestamp"] = DateTime.UtcNow.ToString("O")
            };
        }
        
        /// <summary>
        /// Command line handler for headless Unity operations.
        /// Call this method from Unity command line scripts.
        /// </summary>
        public static void HandleCommandLineArgs()
        {
            string[] args = Environment.GetCommandLineArgs();
            
            for (int i = 0; i < args.Length; i++)
            {
                switch (args[i].ToLower())
                {
                    case "-mcp-port":
                        if (i + 1 < args.Length && int.TryParse(args[i + 1], out int port))
                        {
                            currentUnityPort = port;
                            LogHeadless($"MCP port set to {port} via command line");
                        }
                        break;
                        
                    case "-mcp-autostart":
                        Environment.SetEnvironmentVariable("UNITY_MCP_AUTOSTART", "true");
                        LogHeadless("MCP autostart enabled via command line");
                        break;
                        
                    case "-mcp-log":
                        if (i + 1 < args.Length)
                        {
                            headlessLogPath = args[i + 1];
                            LogHeadless($"MCP log path set to {headlessLogPath}");
                        }
                        break;
                }
            }
        }
    }
    
    /// <summary>
    /// Static class for handling Unity quit events in headless mode.
    /// </summary>
    [InitializeOnLoad]
    public static class HeadlessQuitHandler
    {
        static HeadlessQuitHandler()
        {
            // Register for application quit events
            EditorApplication.quitting += OnApplicationQuitting;
        }
        
        private static void OnApplicationQuitting()
        {
            if (UnityMcpBridge.IsHeadlessMode())
            {
                UnityMcpBridge.ShutdownHeadless();
            }
        }
    }
}