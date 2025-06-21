using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityMcpBridge.Editor.Helpers;
using UnityMcpBridge.Editor.Models;
using UnityMcpBridge.Editor.Tools;

namespace UnityMcpBridge.Editor
{
    [InitializeOnLoad]
    public static partial class UnityMcpBridge
    {
        private static TcpListener listener;
        private static bool isRunning = false;
        private static readonly object lockObj = new();
        private static Dictionary<
            string,
            (string commandJson, TaskCompletionSource<string> tcs)
        > commandQueue = new();
        private static readonly int unityPort = 6400; // Hardcoded port

        public static bool IsRunning => isRunning;

        public static bool FolderExists(string path)
        {
            if (string.IsNullOrEmpty(path))
            {
                return false;
            }

            if (path.Equals("Assets", StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }

            string fullPath = Path.Combine(
                Application.dataPath,
                path.StartsWith("Assets/") ? path[7..] : path
            );
            return Directory.Exists(fullPath);
        }

        static UnityMcpBridge()
        {
            // Initialize dynamic tool registry for extensible MCP tools
            DynamicToolRegistry.Initialize();
            
            Start();
            EditorApplication.quitting += Stop;
        }

        public static void Start()
        {
            Stop();

            try
            {
                ServerInstaller.EnsureServerInstalled();
            }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to ensure UnityMcpServer is installed: {ex.Message}");
            }

            if (isRunning)
            {
                return;
            }

            try
            {
                listener = new TcpListener(IPAddress.Loopback, unityPort);
                listener.Start();
                isRunning = true;
                Debug.Log($"UnityMcpBridge started on port {unityPort}.");
                // Assuming ListenerLoop and ProcessCommands are defined elsewhere
                Task.Run(ListenerLoop);
                EditorApplication.update += ProcessCommands;
            }
            catch (SocketException ex)
            {
                if (ex.SocketErrorCode == SocketError.AddressAlreadyInUse)
                {
                    Debug.LogError(
                        $"Port {unityPort} is already in use. Ensure no other instances are running or change the port."
                    );
                }
                else
                {
                    Debug.LogError($"Failed to start TCP listener: {ex.Message}");
                }
            }
        }

        public static void Stop()
        {
            if (!isRunning)
            {
                return;
            }

            try
            {
                listener?.Stop();
                listener = null;
                isRunning = false;
                EditorApplication.update -= ProcessCommands;
                Debug.Log("UnityMcpBridge stopped.");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Error stopping UnityMcpBridge: {ex.Message}");
            }
        }

        private static async Task ListenerLoop()
        {
            while (isRunning)
            {
                try
                {
                    TcpClient client = await listener.AcceptTcpClientAsync();
                    // Enable basic socket keepalive
                    client.Client.SetSocketOption(
                        SocketOptionLevel.Socket,
                        SocketOptionName.KeepAlive,
                        true
                    );

                    // Set longer receive timeout to prevent quick disconnections
                    client.ReceiveTimeout = 60000; // 60 seconds

                    // Fire and forget each client connection
                    _ = HandleClientAsync(client);
                }
                catch (Exception ex)
                {
                    if (isRunning)
                    {
                        Debug.LogError($"Listener error: {ex.Message}");
                    }
                }
            }
        }

        private static async Task HandleClientAsync(TcpClient client)
        {
            using (client)
            using (NetworkStream stream = client.GetStream())
            {
                byte[] buffer = new byte[8192];
                while (isRunning)
                {
                    try
                    {
                        int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length);
                        if (bytesRead == 0)
                        {
                            break; // Client disconnected
                        }

                        string commandText = System.Text.Encoding.UTF8.GetString(
                            buffer,
                            0,
                            bytesRead
                        );
                        string commandId = Guid.NewGuid().ToString();
                        TaskCompletionSource<string> tcs = new();

                        // Special handling for ping command to avoid JSON parsing
                        if (commandText.Trim() == "ping")
                        {
                            // Direct response to ping without going through JSON parsing
                            byte[] pingResponseBytes = System.Text.Encoding.UTF8.GetBytes(
                                /*lang=json,strict*/
                                "{\"status\":\"success\",\"result\":{\"message\":\"pong\"}}"
                            );
                            await stream.WriteAsync(pingResponseBytes, 0, pingResponseBytes.Length);
                            continue;
                        }

                        lock (lockObj)
                        {
                            commandQueue[commandId] = (commandText, tcs);
                        }

                        string response = await tcs.Task;
                        byte[] responseBytes = System.Text.Encoding.UTF8.GetBytes(response);
                        await stream.WriteAsync(responseBytes, 0, responseBytes.Length);
                    }
                    catch (Exception ex)
                    {
                        Debug.LogError($"Client handler error: {ex.Message}");
                        break;
                    }
                }
            }
        }

        private static void ProcessCommands()
        {
            List<string> processedIds = new();
            lock (lockObj)
            {
                foreach (
                    KeyValuePair<
                        string,
                        (string commandJson, TaskCompletionSource<string> tcs)
                    > kvp in commandQueue.ToList()
                )
                {
                    string id = kvp.Key;
                    string commandText = kvp.Value.commandJson;
                    TaskCompletionSource<string> tcs = kvp.Value.tcs;

                    try
                    {
                        // Special case handling
                        if (string.IsNullOrEmpty(commandText))
                        {
                            var emptyResponse = new
                            {
                                status = "error",
                                error = "Empty command received",
                            };
                            tcs.SetResult(JsonConvert.SerializeObject(emptyResponse));
                            processedIds.Add(id);
                            continue;
                        }

                        // Trim the command text to remove any whitespace
                        commandText = commandText.Trim();

                        // Non-JSON direct commands handling (like ping)
                        if (commandText == "ping")
                        {
                            var pingResponse = new
                            {
                                status = "success",
                                result = new { message = "pong" },
                            };
                            tcs.SetResult(JsonConvert.SerializeObject(pingResponse));
                            processedIds.Add(id);
                            continue;
                        }

                        // Check if the command is valid JSON before attempting to deserialize
                        if (!IsValidJson(commandText))
                        {
                            var invalidJsonResponse = new
                            {
                                status = "error",
                                error = "Invalid JSON format",
                                receivedText = commandText.Length > 50
                                    ? commandText[..50] + "..."
                                    : commandText,
                            };
                            tcs.SetResult(JsonConvert.SerializeObject(invalidJsonResponse));
                            processedIds.Add(id);
                            continue;
                        }

                        // Normal JSON command processing
                        Command command = JsonConvert.DeserializeObject<Command>(commandText);
                        if (command == null)
                        {
                            var nullCommandResponse = new
                            {
                                status = "error",
                                error = "Command deserialized to null",
                                details = "The command was valid JSON but could not be deserialized to a Command object",
                            };
                            tcs.SetResult(JsonConvert.SerializeObject(nullCommandResponse));
                        }
                        else
                        {
                            string responseJson = ExecuteCommand(command);
                            tcs.SetResult(responseJson);
                        }
                    }
                    catch (Exception ex)
                    {
                        Debug.LogError($"Error processing command: {ex.Message}\n{ex.StackTrace}");

                        var response = new
                        {
                            status = "error",
                            error = ex.Message,
                            commandType = "Unknown (error during processing)",
                            receivedText = commandText?.Length > 50
                                ? commandText[..50] + "..."
                                : commandText,
                        };
                        string responseJson = JsonConvert.SerializeObject(response);
                        tcs.SetResult(responseJson);
                    }

                    processedIds.Add(id);
                }

                foreach (string id in processedIds)
                {
                    commandQueue.Remove(id);
                }
            }
        }

        // Helper method to check if a string is valid JSON
        private static bool IsValidJson(string text)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return false;
            }

            text = text.Trim();
            if (
                (text.StartsWith("{") && text.EndsWith("}"))
                || // Object
                (text.StartsWith("[") && text.EndsWith("]"))
            ) // Array
            {
                try
                {
                    JToken.Parse(text);
                    return true;
                }
                catch
                {
                    return false;
                }
            }

            return false;
        }

        private static string ExecuteCommand(Command command)
        {
            try
            {
                if (string.IsNullOrEmpty(command.type))
                {
                    var errorResponse = new
                    {
                        status = "error",
                        error = "Command type cannot be empty",
                        details = "A valid command type is required for processing",
                    };
                    return JsonConvert.SerializeObject(errorResponse);
                }

                // Handle ping command for connection verification
                if (command.type.Equals("ping", StringComparison.OrdinalIgnoreCase))
                {
                    var pingResponse = new
                    {
                        status = "success",
                        result = new { message = "pong" },
                    };
                    return JsonConvert.SerializeObject(pingResponse);
                }

                // Use JObject for parameters as the new handlers likely expect this
                JObject paramsObject = command.@params ?? new JObject();

                // Try dynamic tool registry first for extensible tools
                object result;
                try
                {
                    result = DynamicToolRegistry.ExecuteTool(command.type, paramsObject);
                }
                catch (ArgumentException)
                {
                    // Fallback to legacy static handlers for backward compatibility
                    result = command.type switch
                    {
                        "manage_script" => ManageScript.HandleCommand(paramsObject),
                        "manage_scene" => ManageScene.HandleCommand(paramsObject),
                        "manage_editor" => ManageEditor.HandleCommand(paramsObject),
                        "manage_gameobject" => ManageGameObject.HandleCommand(paramsObject),
                        "manage_asset" => ManageAsset.HandleCommand(paramsObject),
                        "read_console" => ReadConsole.HandleCommand(paramsObject),
                        "execute_menu_item" => ExecuteMenuItem.HandleCommand(paramsObject),
                        _ => throw new ArgumentException(
                            $"Unknown or unsupported command type: {command.type}"
                        ),
                    };
                }

                // Standard success response format
                var response = new { status = "success", result };
                return JsonConvert.SerializeObject(response);
            }
            catch (Exception ex)
            {
                // Log the detailed error in Unity for debugging
                Debug.LogError(
                    $"Error executing command '{command?.type ?? "Unknown"}': {ex.Message}\n{ex.StackTrace}"
                );

                // Standard error response format
                var response = new
                {
                    status = "error",
                    error = ex.Message, // Provide the specific error message
                    command = command?.type ?? "Unknown", // Include the command type if available
                    stackTrace = ex.StackTrace, // Include stack trace for detailed debugging
                    paramsSummary = command?.@params != null
                        ? GetParamsSummary(command.@params)
                        : "No parameters", // Summarize parameters for context
                };
                return JsonConvert.SerializeObject(response);
            }
        }

        // Helper method to get a summary of parameters for error reporting
        private static string GetParamsSummary(JObject @params)
        {
            try
            {
                return @params == null || !@params.HasValues
                    ? "No parameters"
                    : string.Join(
                        ", ",
                        @params
                            .Properties()
                            .Select(static p =>
                                $"{p.Name}: {p.Value?.ToString()?[..Math.Min(20, p.Value?.ToString()?.Length ?? 0)]}"
                            )
                    );
            }
            catch
            {
                return "Could not summarize parameters";
            }
        }
    }
}
