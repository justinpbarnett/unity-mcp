using UnityEngine;
using UnityEditor;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System;
using Newtonsoft.Json;
using System.Net.Sockets;
using System.Threading.Tasks;
using System.Text;
using System.Collections.Generic;
using System.Linq;
using UnityMCP.Editor.Models;
using UnityMCP.Editor.Data;

namespace UnityMCP.Editor.Windows
{
    public class UnityMCPEditorWindow : EditorWindow
    {
        private bool isUnityBridgeRunning = false;
        private Vector2 scrollPosition;
        private string claudeConfigStatus = "Not configured";
        private string cursorConfigStatus = "Not configured";
        private string pythonServerStatus = "Not Connected";
        private Color pythonServerStatusColor = Color.red;
        private const int unityPort = 6400;  // Hardcoded Unity port
        private const int mcpPort = 6500;    // Hardcoded MCP port
        private const float CONNECTION_CHECK_INTERVAL = 2f; // Check every 2 seconds
        private float lastCheckTime = 0f;
        private McpClients mcpClients = new();

        private List<string> possiblePaths = new List<string>();
        

        [MenuItem("Window/Unity MCP")]
        public static void ShowWindow()
        {
            GetWindow<UnityMCPEditorWindow>("MCP Editor");
        }

        private void OnEnable()
        {
            var configPaths = new List<string>
            {
                Path.GetFullPath(Path.Combine(Application.dataPath, "unity-mcp", "Python", "server.py")),
                Path.GetFullPath(Path.Combine(Application.dataPath, "Packages", "com.justinpbarnett.unity-mcp", "Python", "server.py")),
                Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Library", "PackageCache", "com.justinpbarnett.unity-mcp@*", "Python", "server.py")),
                Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Packages", "com.justinpbarnett.unity-mcp", "Python", "server.py"))
            };
            possiblePaths.AddRange(configPaths);
            
            // Check initial states
            isUnityBridgeRunning = UnityMCPBridge.IsRunning;
            CheckPythonServerConnection();
            foreach (McpClient mcpClient in mcpClients.clients)
            {
                CheckMcpConfiguration(mcpClient);
            }
        }

        private void Update()
        {
            // Check Python server connection periodically
            if (Time.realtimeSinceStartup - lastCheckTime >= CONNECTION_CHECK_INTERVAL)
            {
                CheckPythonServerConnection();
                lastCheckTime = Time.realtimeSinceStartup;
            }
        }

        private async void CheckPythonServerConnection()
        {
            try
            {
                using (var client = new TcpClient())
                {
                    // Try to connect with a short timeout
                    var connectTask = client.ConnectAsync("localhost", unityPort);
                    if (await Task.WhenAny(connectTask, Task.Delay(1000)) == connectTask)
                    {
                        // Try to send a ping message to verify connection is alive
                        try
                        {
                            NetworkStream stream = client.GetStream();
                            byte[] pingMessage = Encoding.UTF8.GetBytes("ping");
                            await stream.WriteAsync(pingMessage, 0, pingMessage.Length);

                            // Wait for response with timeout
                            byte[] buffer = new byte[1024];
                            var readTask = stream.ReadAsync(buffer, 0, buffer.Length);
                            if (await Task.WhenAny(readTask, Task.Delay(1000)) == readTask)
                            {
                                int bytesRead = await readTask;
                                if (bytesRead <= 0)
                                {
                                    // Received empty response
                                    pythonServerStatus = "Invalid Response";
                                    pythonServerStatusColor = GetStatusColor(McpStatus.NoResponse);
                                    return;
                                }

                                // Validate the response is actually from our server
                                string response = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                                if (response.Contains("pong"))
                                {
                                    // Connection successful and responsive with valid response
                                    pythonServerStatus = "Connected";
                                    pythonServerStatusColor = GetStatusColor(McpStatus.Connected);
                                }
                                else
                                {
                                    // Received response but not the expected one
                                    pythonServerStatus = "Invalid Server";
                                    pythonServerStatusColor = GetStatusColor(McpStatus.CommunicationError);
                                }
                            }
                            else
                            {
                                // No response received
                                pythonServerStatus = "No Response";
                                pythonServerStatusColor = GetStatusColor(McpStatus.NoResponse);
                                UnityEngine.Debug.LogWarning($"Python server not responding on port {unityPort}");
                            }
                        }
                        catch (Exception e)
                        {
                            // Connection established but communication failed
                            pythonServerStatus = "Communication Error";
                            pythonServerStatusColor = GetStatusColor(McpStatus.CommunicationError);
                            UnityEngine.Debug.LogWarning($"Error communicating with Python server: {e.Message}");
                        }
                    }
                    else
                    {
                        // Connection failed
                        pythonServerStatus = "Not Connected";
                        pythonServerStatusColor = GetStatusColor(McpStatus.NotConfigured);
                        UnityEngine.Debug.LogWarning($"Python server is not running or not accessible on port {unityPort}");
                    }
                    client.Close();
                }
            }
            catch (Exception e)
            {
                pythonServerStatus = "Connection Error";
                pythonServerStatusColor = GetStatusColor(McpStatus.Error);
                UnityEngine.Debug.LogError($"Error checking Python server connection: {e.Message}");
            }
        }

        private Color GetStatusColor(McpStatus status)
        {
            // Return appropriate color based on the status enum
            return status switch
            {
                McpStatus.Configured => Color.green,
                McpStatus.Running => Color.green,
                McpStatus.Connected => Color.green,
                McpStatus.IncorrectPath => Color.yellow,
                McpStatus.CommunicationError => Color.yellow,
                McpStatus.NoResponse => Color.yellow,
                _ => Color.red // Default to red for error states or not configured
            };
        }

        private void ConfigurationSection(McpClient mcpClient)
        {
            // Calculate if we should use half-width layout
            // Minimum width for half-width layout is 400 pixels
            bool useHalfWidth = position.width >= 800;
            float sectionWidth = useHalfWidth ? position.width / 2 - 15 : position.width - 20;

            // Begin horizontal layout if using half-width
            if (useHalfWidth && mcpClients.clients.IndexOf(mcpClient) % 2 == 0)
            {
                EditorGUILayout.BeginHorizontal();
            }

            // Begin section with fixed width
            EditorGUILayout.BeginVertical(EditorStyles.helpBox, GUILayout.Width(sectionWidth));

            // Header with improved styling
            EditorGUILayout.Space(5);
            Rect headerRect = EditorGUILayout.GetControlRect(false, 24);
            GUI.Label(new Rect(headerRect.x + 8, headerRect.y + 4, headerRect.width - 16, headerRect.height),
                mcpClient.name + " Configuration", EditorStyles.boldLabel);
            EditorGUILayout.Space(5);

            // Status indicator with colored dot
            Rect statusRect = EditorGUILayout.BeginHorizontal(GUILayout.Height(20));
            Color statusColor = GetStatusColor(mcpClient.status);

            // Draw status dot
            DrawStatusDot(statusRect, statusColor);

            // Status text with some padding
            EditorGUILayout.LabelField(new GUIContent("      " + mcpClient.configStatus), GUILayout.Height(20), GUILayout.MinWidth(100));
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space(8);

            // Configure button with improved styling
            GUIStyle buttonStyle = new(GUI.skin.button);
            buttonStyle.padding = new RectOffset(15, 15, 5, 5);
            buttonStyle.margin = new RectOffset(10, 10, 5, 5);

            // Create muted button style for Manual Setup
            GUIStyle mutedButtonStyle = new(buttonStyle);

            if (GUILayout.Button($"Auto Configure {mcpClient.name}", buttonStyle, GUILayout.Height(28)))
            {
                ConfigureMcpClient(mcpClient);
            }

            if (GUILayout.Button("Manual Setup", mutedButtonStyle, GUILayout.Height(28)))
            {
                // Get the appropriate config path based on OS
                string configPath = RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
                    ? mcpClient.windowsConfigPath
                    : mcpClient.linuxConfigPath;
                ShowManualInstructionsWindow(configPath, mcpClient);
            }
            EditorGUILayout.Space(5);

            EditorGUILayout.EndVertical();

            // End horizontal layout if using half-width and at the end of a row
            if (useHalfWidth && mcpClients.clients.IndexOf(mcpClient) % 2 == 1)
            {
                EditorGUILayout.EndHorizontal();
                EditorGUILayout.Space(5);
            }
            // Add space and end the horizontal layout if last item is odd
            else if (useHalfWidth && mcpClients.clients.IndexOf(mcpClient) == mcpClients.clients.Count - 1)
            {
                EditorGUILayout.EndHorizontal();
                EditorGUILayout.Space(5);
            }
        }

        private void DrawStatusDot(Rect statusRect, Color statusColor)
        {
            Rect dotRect = new(statusRect.x + 6, statusRect.y + 4, 12, 12);
            Vector3 center = new(dotRect.x + dotRect.width / 2, dotRect.y + dotRect.height / 2, 0);
            float radius = dotRect.width / 2;

            // Draw the main dot
            Handles.color = statusColor;
            Handles.DrawSolidDisc(center, Vector3.forward, radius);

            // Draw the border
            Color borderColor = new(statusColor.r * 0.7f, statusColor.g * 0.7f, statusColor.b * 0.7f);
            Handles.color = borderColor;
            Handles.DrawWireDisc(center, Vector3.forward, radius);
        }

        private void OnGUI()
        {
            scrollPosition = EditorGUILayout.BeginScrollView(scrollPosition);

            EditorGUILayout.Space(10);
            // Title with improved styling
            Rect titleRect = EditorGUILayout.GetControlRect(false, 30);
            EditorGUI.DrawRect(new Rect(titleRect.x, titleRect.y, titleRect.width, titleRect.height), new Color(0.2f, 0.2f, 0.2f, 0.1f));
            GUI.Label(new Rect(titleRect.x + 10, titleRect.y + 6, titleRect.width - 20, titleRect.height),
                "MCP Editor", EditorStyles.boldLabel);
            EditorGUILayout.Space(10);

            // Python Server Status Section
            EditorGUILayout.BeginVertical(EditorStyles.helpBox);
            EditorGUILayout.LabelField("Python Server Status", EditorStyles.boldLabel);

            // Status indicator with colored dot
            var statusRect = EditorGUILayout.BeginHorizontal(GUILayout.Height(20));
            DrawStatusDot(statusRect, pythonServerStatusColor);
            EditorGUILayout.LabelField("      " + pythonServerStatus);
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.LabelField($"Unity Port: {unityPort}");
            EditorGUILayout.LabelField($"MCP Port: {mcpPort}");
            EditorGUILayout.HelpBox("Your MCP client (e.g. Cursor or Claude Desktop) will start the server automatically when you start it.", MessageType.Info);
            EditorGUILayout.EndVertical();

            EditorGUILayout.Space(10);

            // Unity Bridge Section
            EditorGUILayout.BeginVertical(EditorStyles.helpBox);
            EditorGUILayout.LabelField("Unity MCP Bridge", EditorStyles.boldLabel);
            EditorGUILayout.LabelField($"Status: {(isUnityBridgeRunning ? "Running" : "Stopped")}");
            EditorGUILayout.LabelField($"Port: {unityPort}");

            if (GUILayout.Button(isUnityBridgeRunning ? "Stop Bridge" : "Start Bridge"))
            {
                ToggleUnityBridge();
            }
            EditorGUILayout.EndVertical();

            foreach (McpClient mcpClient in mcpClients.clients)
            {
                EditorGUILayout.Space(10);
                ConfigurationSection(mcpClient);
            }

            EditorGUILayout.EndScrollView();
        }

        private void ToggleUnityBridge()
        {
            if (isUnityBridgeRunning)
            {
                UnityMCPBridge.Stop();
            }
            else
            {
                UnityMCPBridge.Start();
            }

            isUnityBridgeRunning = !isUnityBridgeRunning;
        }


        private string GetPythonDirectory(List<string> possiblePaths)
        {
            foreach (var path in possiblePaths)
            {
                // Skip wildcard paths for now
                if (path.Contains("*")) continue;

                if (File.Exists(path))
                {
                    return Path.GetDirectoryName(path);
                }
            }

            foreach (var path in possiblePaths)
            {
                if (!path.Contains("*")) continue;

                string directoryPath = Path.GetDirectoryName(path);
                string searchPattern = Path.GetFileName(Path.GetDirectoryName(path));
                string parentDir = Path.GetDirectoryName(directoryPath);

                if (Directory.Exists(parentDir))
                {
                    var matchingDirs = Directory.GetDirectories(parentDir, searchPattern);

                    foreach (var dir in matchingDirs)
                    {
                        string candidatePath = Path.Combine(dir, "Python", "server.py");

                        if (File.Exists(candidatePath))
                        {
                            return Path.GetDirectoryName(candidatePath);
                        }
                    }
                }
            }

            return null;
        }

        private string WriteToConfig(string pythonDir, string configPath)
        {
            // Create configuration object for unityMCP
            var unityMCPConfig = new MCPConfigServer
            {
                command = "uv",
                args = new[]
                {
                    "--directory",
                    pythonDir,
                    "run",
                    "server.py"
                }
            };

            var jsonSettings = new JsonSerializerSettings
            {
                Formatting = Formatting.Indented
            };

            // Read existing config if it exists
            string existingJson = "{}";
            if (File.Exists(configPath))
            {
                try
                {
                    existingJson = File.ReadAllText(configPath);
                }
                catch (Exception e)
                {
                    UnityEngine.Debug.LogWarning($"Error reading existing config: {e.Message}.");
                }
            }

            // Parse the existing JSON while preserving all properties
            dynamic existingConfig = JsonConvert.DeserializeObject(existingJson);
            if (existingConfig == null)
            {
                existingConfig = new Newtonsoft.Json.Linq.JObject();
            }

            // Ensure mcpServers object exists
            if (existingConfig.mcpServers == null)
            {
                existingConfig.mcpServers = new Newtonsoft.Json.Linq.JObject();
            }

            // Add/update unityMCP while preserving other servers
            existingConfig.mcpServers.unityMCP = JsonConvert.DeserializeObject<Newtonsoft.Json.Linq.JToken>(
                JsonConvert.SerializeObject(unityMCPConfig)
            );

            // Write the merged configuration back to file
            string mergedJson = JsonConvert.SerializeObject(existingConfig, jsonSettings);
            File.WriteAllText(configPath, mergedJson);

            return "Configured successfully";
        }

        private void ShowManualConfigurationInstructions(string configPath, McpClient mcpClient)
        {
            mcpClient.SetStatus(McpStatus.Error, "Manual configuration required");

            ShowManualInstructionsWindow(configPath, mcpClient);
        }

        // New method to show manual instructions without changing status
        private void ShowManualInstructionsWindow(string configPath, McpClient mcpClient)
        {
            // Get the Python directory path using Package Manager API
            string pythonDir = FindPackagePythonDirectory();

            // Create the manual configuration message
            var jsonConfig = new MCPConfig
            {
                mcpServers = new MCPConfigServers
                {
                    unityMCP = new MCPConfigServer
                    {
                        command = "uv",
                        args = new[]
                        {
                            "--directory",
                            pythonDir,
                            "run",
                            "server.py"
                        }
                    }
                }
            };

            var jsonSettings = new JsonSerializerSettings
            {
                Formatting = Formatting.Indented
            };
            string manualConfigJson = JsonConvert.SerializeObject(jsonConfig, jsonSettings);

            ManualConfigEditorWindow.ShowWindow(configPath, manualConfigJson, mcpClient);
        }

        private string FindPackagePythonDirectory()
        {
            string pythonDir = "/path/to/your/unity-mcp/Python";

            try
            {
                // Try to find the package using Package Manager API
                var request = UnityEditor.PackageManager.Client.List();
                while (!request.IsCompleted) { } // Wait for the request to complete

                if (request.Status == UnityEditor.PackageManager.StatusCode.Success)
                {
                    foreach (var package in request.Result)
                    {
                        if (package.name == "com.justinpbarnett.unity-mcp")
                        {
                            string packagePath = package.resolvedPath;
                            string potentialPythonDir = Path.Combine(packagePath, "Python");

                            if (Directory.Exists(potentialPythonDir) &&
                                File.Exists(Path.Combine(potentialPythonDir, "server.py")))
                            {
                                return potentialPythonDir;
                            }
                        }
                    }
                }
                else if (request.Error != null)
                {
                    UnityEngine.Debug.LogError("Failed to list packages: " + request.Error.message);
                }

                // If not found via Package Manager, try manual approaches
                // First check for local installation
                string[] possibleDirs = {
                    Path.GetFullPath(Path.Combine(Application.dataPath, "unity-mcp", "Python"))
                };

                foreach (var dir in possibleDirs)
                {
                    if (Directory.Exists(dir) && File.Exists(Path.Combine(dir, "server.py")))
                    {
                        return dir;
                    }
                }

                // If still not found, return the placeholder path
                UnityEngine.Debug.LogWarning("Could not find Python directory, using placeholder path");
            }
            catch (Exception e)
            {
                UnityEngine.Debug.LogError($"Error finding package path: {e.Message}");
            }

            return pythonDir;
        }

        private string ConfigureMcpClient(McpClient mcpClient)
        {
            try
            {
                // Determine the config file path based on OS
                string configPath;

                if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                {
                    configPath = mcpClient.windowsConfigPath;
                }
                else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX) || RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
                {
                    configPath = mcpClient.linuxConfigPath;
                }
                else
                {
                    return "Unsupported OS";
                }

                // Create directory if it doesn't exist
                Directory.CreateDirectory(Path.GetDirectoryName(configPath));

                // Find the server.py file location
                string pythonDir = GetPythonDirectory(possiblePaths);

                if (pythonDir == null || !File.Exists(Path.Combine(pythonDir, "server.py")))
                {
                    ShowManualInstructionsWindow(configPath, mcpClient);
                    return "Manual Configuration Required";
                }

                string result = WriteToConfig(pythonDir, configPath);

                // Update the client status after successful configuration
                if (result == "Configured successfully")
                {
                    mcpClient.SetStatus(McpStatus.Configured);
                }

                return result;
            }
            catch (Exception e)
            {
                // Determine the config file path based on OS for error message
                string configPath = "";
                if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                {
                    configPath = mcpClient.windowsConfigPath;
                }
                else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX) || RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
                {
                    configPath = mcpClient.linuxConfigPath;
                }

                ShowManualInstructionsWindow(configPath, mcpClient);
                UnityEngine.Debug.LogError($"Failed to configure {mcpClient.name}: {e.Message}\n{e.StackTrace}");
                return $"Failed to configure {mcpClient.name}";
            }
        }


        private void ShowCursorManualConfigurationInstructions(string configPath, McpClient mcpClient)
        {
            mcpClient.SetStatus(McpStatus.Error, "Manual configuration required");

            // Get the Python directory path using Package Manager API
            string pythonDir = FindPackagePythonDirectory();

            // Create the manual configuration message
            var jsonConfig = new MCPConfig
            {
                mcpServers = new MCPConfigServers
                {
                    unityMCP = new MCPConfigServer
                    {
                        command = "uv",
                        args = new[]
                        {
                            "--directory",
                            pythonDir,
                            "run",
                            "server.py"
                        }
                    }
                }
            };

            var jsonSettings = new JsonSerializerSettings
            {
                Formatting = Formatting.Indented
            };
            string manualConfigJson = JsonConvert.SerializeObject(jsonConfig, jsonSettings);

            ManualConfigEditorWindow.ShowWindow(configPath, manualConfigJson, mcpClient);
        }

        private void CheckMcpConfiguration(McpClient mcpClient)
        {
            try
            {
                string configPath;
                if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
                {
                    configPath = mcpClient.windowsConfigPath;
                }
                else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX) || RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
                {
                    configPath = mcpClient.linuxConfigPath;
                }
                else
                {
                    mcpClient.SetStatus(McpStatus.UnsupportedOS);
                    return;
                }

                if (!File.Exists(configPath))
                {
                    mcpClient.SetStatus(McpStatus.NotConfigured);
                    return;
                }

                string configJson = File.ReadAllText(configPath);
                var config = JsonConvert.DeserializeObject<MCPConfig>(configJson);

                if (config?.mcpServers?.unityMCP != null)
                {
                    string pythonDir = GetPythonDirectory(possiblePaths);
                    if (pythonDir != null && Array.Exists(config.mcpServers.unityMCP.args, arg => arg.Contains(pythonDir, StringComparison.Ordinal)))
                    {
                        mcpClient.SetStatus(McpStatus.Configured);
                    }
                    else
                    {
                        mcpClient.SetStatus(McpStatus.IncorrectPath);
                    }
                }
                else
                {
                    mcpClient.SetStatus(McpStatus.MissingConfig);
                }
            }
            catch (Exception e)
            {
                mcpClient.SetStatus(McpStatus.Error, e.Message);
            }
        }
    }
}