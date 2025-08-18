using System;
using System.Collections.Generic; // Added for HashSet
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using MCPForUnity.Editor.Helpers; // For Response class

namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Handles executing Unity Editor menu items by path.
    /// </summary>
    public static class ExecuteMenuItem
    {
        // Basic blacklist to prevent accidental execution of potentially disruptive menu items.
        // This can be expanded based on needs.
        private static readonly HashSet<string> _menuPathBlacklist = new HashSet<string>(
            StringComparer.OrdinalIgnoreCase
        )
        {
            "File/Quit",
            // Add other potentially dangerous items like "Edit/Preferences...", "File/Build Settings..." if needed
        };

        /// <summary>
        /// Main handler for executing menu items or getting available ones.
        /// </summary>
        public static object HandleCommand(JObject @params)
        {
            string action = @params["action"]?.ToString().ToLower() ?? "execute"; // Default action

            try
            {
                switch (action)
                {
                    case "execute":
                        return ExecuteItem(@params);
                    case "get_available_menus":
                        // Getting a comprehensive list of *all* menu items dynamically is very difficult
                        // and often requires complex reflection or maintaining a manual list.
                        // Returning a placeholder/acknowledgement for now.
                        Debug.LogWarning(
                            "[ExecuteMenuItem] 'get_available_menus' action is not fully implemented. Dynamically listing all menu items is complex."
                        );
                        // Returning an empty list as per the refactor plan's requirements.
                        return Response.Success(
                            "'get_available_menus' action is not fully implemented. Returning empty list.",
                            new List<string>()
                        );
                    // TODO: Consider implementing a basic list of common/known menu items or exploring reflection techniques if this feature becomes critical.
                    default:
                        return Response.Error(
                            $"Unknown action: '{action}'. Valid actions are 'execute', 'get_available_menus'."
                        );
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"[ExecuteMenuItem] Action '{action}' failed: {e}");
                return Response.Error($"Internal error processing action '{action}': {e.Message}");
            }
        }

        /// <summary>
        /// Executes a specific menu item.
        /// </summary>
        private static object ExecuteItem(JObject @params)
        {
            // Try both naming conventions: snake_case and camelCase
            string menuPath = @params["menu_path"]?.ToString() ?? @params["menuPath"]?.ToString();

            // string alias = @params["alias"]?.ToString(); // TODO: Implement alias mapping based on refactor plan requirements.
            // JObject parameters = @params["parameters"] as JObject; // TODO: Investigate parameter passing (often not directly supported by ExecuteMenuItem).

            if (string.IsNullOrWhiteSpace(menuPath))
            {
                return Response.Error("Required parameter 'menu_path' or 'menuPath' is missing or empty.");
            }

            // Validate against blacklist
            if (_menuPathBlacklist.Contains(menuPath))
            {
                return Response.Error(
                    $"Execution of menu item '{menuPath}' is blocked for safety reasons."
                );
            }

            // TODO: Implement alias lookup here if needed (Map alias to actual menuPath).
            // if (!string.IsNullOrEmpty(alias)) { menuPath = LookupAlias(alias); if(menuPath == null) return Response.Error(...); }

            // TODO: Handle parameters ('parameters' object) if a viable method is found.
            // This is complex as EditorApplication.ExecuteMenuItem doesn't take arguments directly.
            // It might require finding the underlying EditorWindow or command if parameters are needed.

            try
            {
                // Attempt to execute the menu item on the main thread using delayCall for safety.
                EditorApplication.delayCall += () =>
                {
                    try
                    {
                        bool executed = EditorApplication.ExecuteMenuItem(menuPath);
                        // Log potential failure inside the delayed call.
                        if (!executed)
                        {
                            Debug.LogError(
                                $"[ExecuteMenuItem] Failed to find or execute menu item via delayCall: '{menuPath}'. It might be invalid, disabled, or context-dependent."
                            );
                        }
                    }
                    catch (Exception delayEx)
                    {
                        Debug.LogError(
                            $"[ExecuteMenuItem] Exception during delayed execution of '{menuPath}': {delayEx}"
                        );
                    }
                };

                // Report attempt immediately, as execution is delayed.
                return Response.Success(
                    $"Attempted to execute menu item: '{menuPath}'. Check Unity logs for confirmation or errors."
                );
            }
            catch (Exception e)
            {
                // Catch errors during setup phase.
                Debug.LogError(
                    $"[ExecuteMenuItem] Failed to setup execution for '{menuPath}': {e}"
                );
                return Response.Error(
                    $"Error setting up execution for menu item '{menuPath}': {e.Message}"
                );
            }
        }

        // TODO: Add helper for alias lookup if implementing aliases.
        // private static string LookupAlias(string alias) { ... return actualMenuPath or null ... }
    }
}

