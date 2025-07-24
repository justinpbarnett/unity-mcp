using System;
using System.IO;
using System.Linq;
using System.Net;
using System.Runtime.InteropServices;
using UnityEngine;

namespace UnityMcpBridge.Editor.Helpers
{
    public static class ServerInstaller
    {
        private const string RootFolder = "UnityMCP";
        private const string ServerFolder = "UnityMcpServer";
        private const string BranchName = "master";
        private const string GitUrl = "https://github.com/justinpbarnett/unity-mcp.git";
        private const string PyprojectUrl =
            "https://raw.githubusercontent.com/justinpbarnett/unity-mcp/refs/heads/"
            + BranchName
            + "/UnityMcpServer/src/pyproject.toml";

        /// <summary>
        /// Ensures the unity-mcp-server is installed and up to date.
        /// </summary>
        public static void EnsureServerInstalled()
        {
            try
            {
                string saveLocation = GetSaveLocation();

                if (!IsServerInstalled(saveLocation))
                {
                    InstallServer(saveLocation);
                }
                else
                {
                    string installedVersion = GetInstalledVersion();
                    string latestVersion = GetLatestVersion();

                    if (IsNewerVersion(latestVersion, installedVersion))
                    {
                        UpdateServer(saveLocation);
                        Debug.Log($"Unity MCP Server updated from version {installedVersion} to {latestVersion}");
                    }
                    else 
                    {
                        Debug.Log($"Unity MCP Server is up to date (version {installedVersion})");
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to ensure server installation: {ex.Message}");
            }
        }

        public static string GetServerPath()
        {
            return Path.Combine(GetSaveLocation(), ServerFolder, "src");
        }

        /// <summary>
        /// Gets the platform-specific save location for the server.
        /// </summary>
        private static string GetSaveLocation()
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    "AppData",
                    "Local",
                    "Programs",
                    RootFolder
                );
            }
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux))
            {
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    "bin",
                    RootFolder
                );
            }
            else if (RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
            {
                string path = "/usr/local/bin";
                return !Directory.Exists(path) || !IsDirectoryWritable(path)
                    ? Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                        "Applications",
                        RootFolder
                    )
                    : Path.Combine(path, RootFolder);
            }
            throw new Exception("Unsupported operating system.");
        }

        private static bool IsDirectoryWritable(string path)
        {
            try
            {
                File.Create(Path.Combine(path, "test.txt")).Dispose();
                File.Delete(Path.Combine(path, "test.txt"));
                return true;
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Checks if the server is installed at the specified location.
        /// </summary>
        /// <param name="location">The base directory where the server should be installed</param>
        /// <returns>True if the server is properly installed, false otherwise</returns>
        private static bool IsServerInstalled(string location)
        {
            try
            {
                if (!Directory.Exists(location))
                {
                    return false;
                }
                
                string pyprojectPath = Path.Combine(location, ServerFolder, "src", "pyproject.toml");
                string serverPyPath = Path.Combine(location, ServerFolder, "src", "server.py");
                
                // Check both files to ensure a complete installation
                bool hasRequiredFiles = File.Exists(pyprojectPath) && File.Exists(serverPyPath);
                
                // Additional check: Verify git directory exists for updates
                bool hasGitDir = Directory.Exists(Path.Combine(location, ".git"));
                
                if (!hasRequiredFiles && hasGitDir)
                {
                    // If git exists but files are missing, we have a broken installation
                    Debug.LogWarning($"Found partial installation at {location}. Some required files are missing.");
                }
                
                return hasRequiredFiles;
            }
            catch (Exception ex)
            {
                Debug.LogError($"Error checking server installation: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Installs the server by cloning only the UnityMcpServer folder from the repository and setting up dependencies.
        /// </summary>
        private static void InstallServer(string location)
        {
            Debug.Log($"Installing Unity MCP Server to {location}");
            
            try
            {
                // Create the src directory where the server code will reside
                Directory.CreateDirectory(location);

                // Initialize git repo in the src directory
                RunCommand("git", $"init", workingDirectory: location);

                // Add remote
                RunCommand("git", $"remote add origin {GitUrl}", workingDirectory: location);

                // Configure sparse checkout
                RunCommand("git", "config core.sparseCheckout true", workingDirectory: location);

                // Set sparse checkout path to only include UnityMcpServer folder
                string sparseCheckoutPath = Path.Combine(location, ".git", "info", "sparse-checkout");
                File.WriteAllText(sparseCheckoutPath, $"{ServerFolder}/");

                // Fetch and checkout the branch
                RunCommand("git", $"fetch --depth=1 origin {BranchName}", workingDirectory: location);
                RunCommand("git", $"checkout {BranchName}", workingDirectory: location);
                
                Debug.Log("Unity MCP Server installation completed successfully");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to install Unity MCP Server: {ex.Message}");
                
                // Clean up failed installation to prevent partial installs
                try
                {
                    if (Directory.Exists(location))
                    {
                        Directory.Delete(location, true);
                    }
                }
                catch (Exception cleanupEx)
                {
                    Debug.LogError($"Failed to clean up after installation error: {cleanupEx.Message}");
                }
                
                throw; // Rethrow to be caught by EnsureServerInstalled
            }
        }

        /// <summary>
        /// Fetches the currently installed version from the local pyproject.toml file.
        /// </summary>
        public static string GetInstalledVersion()
        {
            try
            {
                string pyprojectPath = Path.Combine(
                    GetSaveLocation(),
                    ServerFolder,
                    "src",
                    "pyproject.toml"
                );
                
                if (!File.Exists(pyprojectPath))
                {
                    Debug.LogWarning($"pyproject.toml not found at {pyprojectPath}");
                    return "0.0.0"; // Return a baseline version if file doesn't exist
                }
                
                return ParseVersionFromPyproject(File.ReadAllText(pyprojectPath));
            }
            catch (Exception ex)
            {
                Debug.LogError($"Error getting installed version: {ex.Message}");
                return "0.0.0"; // Return a baseline version on error
            }
        }

        /// <summary>
        /// Fetches the latest version from the GitHub pyproject.toml file.
        /// </summary>
        public static string GetLatestVersion()
        {
            try
            {
                using WebClient webClient = new();
                string pyprojectContent = webClient.DownloadString(PyprojectUrl);
                return ParseVersionFromPyproject(pyprojectContent);
            }
            catch (WebException webEx)
            {
                Debug.LogError($"Failed to download latest version: {webEx.Message}. Check your internet connection.");
                return GetInstalledVersion(); // Fall back to installed version
            }
            catch (Exception ex)
            {
                Debug.LogError($"Error getting latest version: {ex.Message}");
                return GetInstalledVersion(); // Fall back to installed version
            }
        }

        /// <summary>
        /// Updates the server by pulling the latest changes for the UnityMcpServer folder only.
        /// </summary>
        private static void UpdateServer(string location)
        {
            Debug.Log("Updating Unity MCP Server...");
            
            try
            {
                RunCommand("git", $"pull origin {BranchName}", workingDirectory: location);
                Debug.Log("Unity MCP Server update completed successfully");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to update Unity MCP Server: {ex.Message}");
                throw; // Rethrow to be caught by EnsureServerInstalled
            }
        }

        /// <summary>
        /// Parses the version number from pyproject.toml content.
        /// </summary>
        /// <param name="content">The content of pyproject.toml file</param>
        /// <returns>Version string or "0.0.0" if not found</returns>
        private static string ParseVersionFromPyproject(string content)
        {
            try
            {
                if (string.IsNullOrEmpty(content))
                {
                    Debug.LogWarning("Empty pyproject.toml content");
                    return "0.0.0";
                }
                
                foreach (string line in content.Split('\n'))
                {
                    if (line.Trim().StartsWith("version ="))
                    {
                        string[] parts = line.Split('=');
                        if (parts.Length == 2)
                        {
                            string version = parts[1].Trim().Trim('"', '\'');
                            
                            // Validate version format (should be like x.y.z)
                            if (System.Text.RegularExpressions.Regex.IsMatch(version, @"^\d+\.\d+\.\d+$"))
                            {
                                return version;
                            }
                            else
                            {
                                Debug.LogWarning($"Invalid version format in pyproject.toml: {version}");
                            }
                        }
                    }
                }
                
                Debug.LogWarning("Version not found in pyproject.toml");
                return "0.0.0";
            }
            catch (Exception ex)
            {
                Debug.LogError($"Error parsing pyproject.toml: {ex.Message}");
                return "0.0.0";
            }
        }

        /// <summary>
        /// Compares two version strings to determine if the latest is newer.
        /// </summary>
        public static bool IsNewerVersion(string latest, string installed)
        {
            int[] latestParts = latest.Split('.').Select(int.Parse).ToArray();
            int[] installedParts = installed.Split('.').Select(int.Parse).ToArray();
            for (int i = 0; i < Math.Min(latestParts.Length, installedParts.Length); i++)
            {
                if (latestParts[i] > installedParts[i])
                {
                    return true;
                }

                if (latestParts[i] < installedParts[i])
                {
                    return false;
                }
            }
            return latestParts.Length > installedParts.Length;
        }

        /// <summary>
        /// Runs a command-line process and handles output/errors.
        /// </summary>
        private static void RunCommand(
            string command,
            string arguments,
            string workingDirectory = null
        )
        {
            System.Diagnostics.Process process = new()
            {
                StartInfo = new System.Diagnostics.ProcessStartInfo
                {
                    FileName = command,
                    Arguments = arguments,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WorkingDirectory = workingDirectory ?? string.Empty,
                },
            };
            process.Start();
            string output = process.StandardOutput.ReadToEnd();
            string error = process.StandardError.ReadToEnd();
            process.WaitForExit();
            if (process.ExitCode != 0)
            {
                throw new Exception(
                    $"Command failed: {command} {arguments}\nOutput: {output}\nError: {error}"
                );
            }
        }
    }
}
