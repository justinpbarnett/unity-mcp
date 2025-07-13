using System;
using System.IO;
using System.Runtime.InteropServices;
using Newtonsoft.Json;
using UnityEditor;
using UnityEngine;
using UnityMcpBridge.Editor.Data;
using UnityMcpBridge.Editor.Helpers;
using UnityMcpBridge.Editor.Models;

namespace UnityMcpBridge.Editor.Windows
{
    public class UnityMcpEditorWindow : EditorWindow
    {
        private bool isUnityBridgeRunning = false;
        private Vector2 scrollPosition;
        private string pythonServerInstallationStatus = "Not Installed";
        private Color pythonServerInstallationStatusColor = Color.red;
        private const int unityPort = 6400; // Hardcoded Unity port
        private const int mcpPort = 6500; // Hardcoded MCP port
        private readonly McpClients mcpClients = new();

        [MenuItem("Window/Unity MCP")]
        public static void ShowWindow()
        {
            GetWindow<UnityMcpEditorWindow>("MCP Editor");
        }

        private void OnEnable()
        {
            UpdatePythonServerInstallationStatus();

            isUnityBridgeRunning = UnityMcpBridge.IsRunning;
            foreach (McpClient mcpClient in mcpClients.clients)
            {
                CheckMcpConfiguration(mcpClient);
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
                _ => Color.red, // Default to red for error states or not configured
            };
        }

        private void UpdatePythonServerInstallationStatus()
        {
            string serverPath = ServerInstaller.GetServerPath();

            if (File.Exists(Path.Combine(serverPath, "server.py")))
            {
                string installedVersion = ServerInstaller.GetInstalledVersion();
                string latestVersion = ServerInstaller.GetLatestVersion();

                if (ServerInstaller.IsNewerVersion(latestVersion, installedVersion))
                {
                    pythonServerInstallationStatus = "Newer Version Available";
                    pythonServerInstallationStatusColor = Color.yellow;
                }
                else
                {
                    pythonServerInstallationStatus = "Up to Date";
                    pythonServerInstallationStatusColor = Color.green;
                }
            }
            else
            {
                pythonServerInstallationStatus = "Not Installed";
                pythonServerInstallationStatusColor = Color.red;
            }
        }

        private void ConfigurationSection(McpClient mcpClient)
        {
            // Calculate if we should use half-width layout
            // Minimum width for half-width layout is 400 pixels
            bool useHalfWidth = position.width >= 800;
            float sectionWidth = useHalfWidth ? (position.width / 2) - 15 : position.width - 20;

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
            GUI.Label(
                new Rect(
                    headerRect.x + 8,
                    headerRect.y + 4,
                    headerRect.width - 16,
                    headerRect.height
                ),
                mcpClient.name + " Configuration",
                EditorStyles.boldLabel
            );
            EditorGUILayout.Space(5);

            // Status indicator with colored dot
            Rect statusRect = EditorGUILayout.BeginHorizontal(GUILayout.Height(20));
            Color statusColor = GetStatusColor(mcpClient.status);

            // Draw status dot
            DrawStatusDot(statusRect, statusColor);

            // Status text with some padding
            EditorGUILayout.LabelField(
                new GUIContent("      " + mcpClient.configStatus),
                GUILayout.Height(20),
                GUILayout.MinWidth(100)
            );
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space(8);

            // Configure button with improved styling
            GUIStyle buttonStyle = new(GUI.skin.button)
            {
                padding = new RectOffset(15, 15, 5, 5),
                margin = new RectOffset(10, 10, 5, 5),
            };

            // Create muted button style for Manual Setup
            GUIStyle mutedButtonStyle = new(buttonStyle);

            if (
                GUILayout.Button(
                    $"Auto Configure {mcpClient.name}",
                    buttonStyle,
                    GUILayout.Height(28)
                )
            )
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
            else if (
                useHalfWidth
                && mcpClients.clients.IndexOf(mcpClient) == mcpClients.clients.Count - 1
            )
            {
                EditorGUILayout.EndHorizontal();
                EditorGUILayout.Space(5);
            }
        }

        private void DrawStatusDot(Rect statusRect, Color statusColor)
        {
            Rect dotRect = new(statusRect.x + 6, statusRect.y + 4, 12, 12);
            Vector3 center = new(
                dotRect.x + (dotRect.width / 2),
                dotRect.y + (dotRect.height / 2),
                0
            );
            float radius = dotRect.width / 2;

            // Draw the main dot
            Handles.color = statusColor;
            Handles.DrawSolidDisc(center, Vector3.forward, radius);

            // Draw the border
            Color borderColor = new(
                statusColor.r * 0.7f,
                statusColor.g * 0.7f,
                statusColor.b * 0.7f
            );
            Handles.color = borderColor;
            Handles.DrawWireDisc(center, Vector3.forward, radius);
        }

        private void OnGUI()
        {
            scrollPosition = EditorGUILayout.BeginScrollView(scrollPosition);

            EditorGUILayout.Space(10);
            // Title with improved styling
            Rect titleRect = EditorGUILayout.GetControlRect(false, 30);
            EditorGUI.DrawRect(
                new Rect(titleRect.x, titleRect.y, titleRect.width, titleRect.height),
                new Color(0.2f, 0.2f, 0.2f, 0.1f)
            );
            GUI.Label(
                new Rect(titleRect.x + 10, titleRect.y + 6, titleRect.width - 20, titleRect.height),
                "MCP Editor",
                EditorStyles.boldLabel
            );
            EditorGUILayout.Space(10);

            // Python Server Installation Status Section
            EditorGUILayout.BeginVertical(EditorStyles.helpBox);
            EditorGUILayout.LabelField("Python Server Status", EditorStyles.boldLabel);

            // Status indicator with colored dot
            Rect installStatusRect = EditorGUILayout.BeginHorizontal(GUILayout.Height(20));
            DrawStatusDot(installStatusRect, pythonServerInstallationStatusColor);
            EditorGUILayout.LabelField("      " + pythonServerInstallationStatus);
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.LabelField($"Unity Port: {unityPort}");
            EditorGUILayout.LabelField($"MCP Port: {mcpPort}");
            EditorGUILayout.HelpBox(
                "Your MCP client (e.g. Cursor or Claude Desktop) will start the server automatically when you start it.",
                MessageType.Info
            );
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
                UnityMcpBridge.Stop();
            }
            else
            {
                UnityMcpBridge.Start();
            }

            isUnityBridgeRunning = !isUnityBridgeRunning;
        }

        private string WriteToConfig(string pythonDir, string configPath)
        {
            // Convert pythonDir to WSL path if running on Windows
            string finalPythonDir = RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
                ? PathConverter.WindowsPathToWslPath(pythonDir)
                : pythonDir;

            // Create configuration object for unityMCP
            McpConfigServer unityMCPConfig = new()
            {
                command = "uv",
                args = new[] { "--directory", finalPythonDir, "run", "server.py" },
            };

            JsonSerializerSettings jsonSettings = new() { Formatting = Formatting.Indented };

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
                    Debug.LogWarning($"Error reading existing config: {e.Message}.");
                }
            }

            // Parse the existing JSON while preserving all properties
            dynamic existingConfig = JsonConvert.DeserializeObject(existingJson);
            existingConfig ??= new Newtonsoft.Json.Linq.JObject();

            // Ensure mcpServers object exists
            if (existingConfig.mcpServers == null)
            {
                existingConfig.mcpServers = new Newtonsoft.Json.Linq.JObject();
            }

            // Add/update unityMCP while preserving other servers
            existingConfig.mcpServers.unityMCP =
                JsonConvert.DeserializeObject<Newtonsoft.Json.Linq.JToken>(
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

            // Convert pythonDir to WSL path if running on Windows
            string finalPythonDir = RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
                ? PathConverter.WindowsPathToWslPath(pythonDir)
                : pythonDir;

            // Create the manual configuration message
            McpConfig jsonConfig = new()
            {
                mcpServers = new McpConfigServers
                {
                    unityMCP = new McpConfigServer
                    {
                        command = "uv",
                        args = new[] { "--directory", finalPythonDir, "run", "server.py" },
                    },
                },
            };

            JsonSerializerSettings jsonSettings = new() { Formatting = Formatting.Indented };
            string manualConfigJson = JsonConvert.SerializeObject(jsonConfig, jsonSettings);

            ManualConfigEditorWindow.ShowWindow(configPath, manualConfigJson, mcpClient);
        }

        private string FindPackagePythonDirectory()
        {
            string pythonDir = ServerInstaller.GetServerPath();

            try
            {
                // Try to find the package using Package Manager API
                UnityEditor.PackageManager.Requests.ListRequest request =
                    UnityEditor.PackageManager.Client.List();
                while (!request.IsCompleted) { } // Wait for the request to complete

                if (request.Status == UnityEditor.PackageManager.StatusCode.Success)
                {
                    foreach (UnityEditor.PackageManager.PackageInfo package in request.Result)
                    {
                        if (package.name == "com.justinpbarnett.unity-mcp")
                        {
                            string packagePath = package.resolvedPath;
                            string potentialPythonDir = Path.Combine(packagePath, "Python");

                            if (
                                Directory.Exists(potentialPythonDir)
                                && File.Exists(Path.Combine(potentialPythonDir, "server.py"))
                            )
                            {
                                return potentialPythonDir;
                            }
                        }
                    }
                }
                else if (request.Error != null)
                {
                    Debug.LogError("Failed to list packages: " + request.Error.message);
                }

                // If not found via Package Manager, try manual approaches
                // First check for local installation
                string[] possibleDirs =
                {
                    Path.GetFullPath(Path.Combine(Application.dataPath, "unity-mcp", "Python")),
                };

                foreach (string dir in possibleDirs)
                {
                    if (Directory.Exists(dir) && File.Exists(Path.Combine(dir, "server.py")))
                    {
                        return dir;
                    }
                }

                // If still not found, return the placeholder path
                Debug.LogWarning("Could not find Python directory, using placeholder path");
            }
            catch (Exception e)
            {
                Debug.LogError($"Error finding package path: {e.Message}");
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
                else if (
                    RuntimeInformation.IsOSPlatform(OSPlatform.OSX)
                    || RuntimeInformation.IsOSPlatform(OSPlatform.Linux)
                )
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
                string pythonDir = ServerInstaller.GetServerPath();

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
                else if (
                    RuntimeInformation.IsOSPlatform(OSPlatform.OSX)
                    || RuntimeInformation.IsOSPlatform(OSPlatform.Linux)
                )
                {
                    configPath = mcpClient.linuxConfigPath;
                }

                ShowManualInstructionsWindow(configPath, mcpClient);
                Debug.LogError(
                    $"Failed to configure {mcpClient.name}: {e.Message}\n{e.StackTrace}"
                );
                return $"Failed to configure {mcpClient.name}";
            }
        }

        private void ShowCursorManualConfigurationInstructions(
            string configPath,
            McpClient mcpClient
        )
        {
            mcpClient.SetStatus(McpStatus.Error, "Manual configuration required");

            // Get the Python directory path using Package Manager API
            string pythonDir = FindPackagePythonDirectory();

            // Create the manual configuration message
            McpConfig jsonConfig = new()
            {
                mcpServers = new McpConfigServers
                {
                    unityMCP = new McpConfigServer
                    {
                        command = "uv",
                        args = new[] { "--directory", pythonDir, "run", "server.py" },
                    },
                },
            };

            JsonSerializerSettings jsonSettings = new() { Formatting = Formatting.Indented };
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
                else if (
                    RuntimeInformation.IsOSPlatform(OSPlatform.OSX)
                    || RuntimeInformation.IsOSPlatform(OSPlatform.Linux)
                )
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
                McpConfig config = JsonConvert.DeserializeObject<McpConfig>(configJson);

                if (config?.mcpServers?.unityMCP != null)
                {
                    string pythonDir = ServerInstaller.GetServerPath();
                    // Convert pythonDir to WSL path for comparison if running on Windows
                    string comparisonPythonDir = RuntimeInformation.IsOSPlatform(OSPlatform.Windows)
                        ? PathConverter.WindowsPathToWslPath(pythonDir)
                        : pythonDir;

                    if (
                        pythonDir != null
                        && Array.Exists(
                            config.mcpServers.unityMCP.args,
                            arg => arg.Contains(comparisonPythonDir, StringComparison.Ordinal)
                        )
                    )
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
