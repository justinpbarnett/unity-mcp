using System;
using System.IO;
using System.Runtime.InteropServices;

namespace UnityMcpBridge.Editor.Helpers
{
    public static class PathConverter
    {
        /// <summary>
        /// Converts a Windows path to a WSL (Windows Subsystem for Linux) path.
        /// </summary>
        /// <param name="windowsPath">The Windows path to convert (e.g., "C:\Users\User\Documents").</param>
        /// <returns>The corresponding WSL path (e.g., "/mnt/c/Users/User/Documents").</returns>
        public static string WindowsPathToWslPath(string windowsPath)
        {
            if (string.IsNullOrEmpty(windowsPath))
            {
                return windowsPath;
            }

            // Replace backslashes with forward slashes
            string wslPath = windowsPath.Replace("\\", "/");

            // Convert drive letter (e.g., C:/ to /mnt/c/)
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows) && wslPath.Length >= 2 && wslPath[1] == ':')
            {
                char driveLetter = char.ToLower(wslPath[0]);
                wslPath = $"/mnt/{driveLetter}{wslPath.Substring(2)}";
            }

            return wslPath;
        }

        /// <summary>
        /// Converts a WSL path to a Windows path.
        /// </summary>
        /// <param name="wslPath">The WSL path to convert (e.g., "/mnt/c/Users/User/Documents").</param>
        /// <returns>The corresponding Windows path (e.g., "C:\Users\User\Documents").</returns>
        public static string WslPathToWindowsPath(string wslPath)
        {
            if (string.IsNullOrEmpty(wslPath))
            {
                return wslPath;
            }

            // Replace forward slashes with backslashes
            string windowsPath = wslPath.Replace("/", "\\");

            // Convert /mnt/c/ to C:\
            if (windowsPath.StartsWith("\\mnt\\") && windowsPath.Length >= 7 && windowsPath[6] == '\\')
            {
                char driveLetter = char.ToUpper(windowsPath[5]);
                windowsPath = $"{driveLetter}:\\{windowsPath.Substring(7)}";
            }

            return windowsPath;
        }
    }
}
