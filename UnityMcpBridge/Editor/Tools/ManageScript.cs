using System;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityMcpBridge.Editor.Helpers;

using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using System.Collections.Generic;

namespace UnityMcpBridge.Editor.Tools
{
    /// <summary>
    /// Handles CRUD operations for C# scripts within the Unity project.
    /// </summary>
    public static class ManageScript
    {
        /// <summary>
        /// Main handler for script management actions.
        /// </summary>
        public static object HandleCommand(JObject @params)
        {
            // Extract parameters
            string action = @params["action"]?.ToString().ToLower();
            string name = @params["name"]?.ToString();
            string path = @params["path"]?.ToString(); // Relative to Assets/
            string contents = null;

            // Check if we have base64 encoded contents
            bool contentsEncoded = @params["contentsEncoded"]?.ToObject<bool>() ?? false;
            if (contentsEncoded && @params["encodedContents"] != null)
            {
                try
                {
                    contents = DecodeBase64(@params["encodedContents"].ToString());
                }
                catch (Exception e)
                {
                    return Response.Error($"Failed to decode script contents: {e.Message}");
                }
            }
            else
            {
                contents = @params["contents"]?.ToString();
            }

            string scriptType = @params["scriptType"]?.ToString(); // For templates/validation
            string namespaceName = @params["namespace"]?.ToString(); // For organizing code

            // Validate required parameters
            if (string.IsNullOrEmpty(action))
            {
                return Response.Error("Action parameter is required.");
            }
            if (string.IsNullOrEmpty(name))
            {
                return Response.Error("Name parameter is required.");
            }
            // Basic name validation (alphanumeric, underscores, cannot start with number)
            if (!Regex.IsMatch(name, @"^[a-zA-Z_][a-zA-Z0-9_]*$"))
            {
                return Response.Error(
                    $"Invalid script name: '{name}'. Use only letters, numbers, underscores, and don't start with a number."
                );
            }

            // Ensure path is relative to Assets/, removing any leading "Assets/"
            // Set default directory to "Scripts" if path is not provided
            string relativeDir = path ?? "Scripts"; // Default to "Scripts" if path is null
            if (!string.IsNullOrEmpty(relativeDir))
            {
                relativeDir = relativeDir.Replace('\\', '/').Trim('/');
                if (relativeDir.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase))
                {
                    relativeDir = relativeDir.Substring("Assets/".Length).TrimStart('/');
                }
            }
            // Handle empty string case explicitly after processing
            if (string.IsNullOrEmpty(relativeDir))
            {
                relativeDir = "Scripts"; // Ensure default if path was provided as "" or only "/" or "Assets/"
            }

            // Construct paths
            string scriptFileName = $"{name}.cs";
            string fullPathDir = Path.Combine(Application.dataPath, relativeDir); // Application.dataPath ends in "Assets"
            string fullPath = Path.Combine(fullPathDir, scriptFileName);
            string relativePath = Path.Combine("Assets", relativeDir, scriptFileName)
                .Replace('\\', '/'); // Ensure "Assets/" prefix and forward slashes

            // Ensure the target directory exists for create/update
            if (action == "create" || action == "update")
            {
                try
                {
                    Directory.CreateDirectory(fullPathDir);
                }
                catch (Exception e)
                {
                    return Response.Error(
                        $"Could not create directory '{fullPathDir}': {e.Message}"
                    );
                }
            }

            // Route to specific action handlers
            switch (action)
            {
                case "create":
                    return CreateScript(
                        fullPath,
                        relativePath,
                        name,
                        contents,
                        scriptType,
                        namespaceName
                    );
                case "read":
                    return ReadScript(fullPath, relativePath);
                case "update":
                    return UpdateScript(fullPath, relativePath, name, contents);
                case "delete":
                    return DeleteScript(fullPath, relativePath);
                default:
                    return Response.Error(
                        $"Unknown action: '{action}'. Valid actions are: create, read, update, delete."
                    );
            }
        }

        /// <summary>
        /// Decode base64 string to normal text
        /// </summary>
        private static string DecodeBase64(string encoded)
        {
            byte[] data = Convert.FromBase64String(encoded);
            return System.Text.Encoding.UTF8.GetString(data);
        }

        /// <summary>
        /// Encode text to base64 string
        /// </summary>
        private static string EncodeBase64(string text)
        {
            byte[] data = System.Text.Encoding.UTF8.GetBytes(text);
            return Convert.ToBase64String(data);
        }

        private static object CreateScript(
            string fullPath,
            string relativePath,
            string name,
            string contents,
            string scriptType,
            string namespaceName
        )
        {
            // Check if script already exists
            if (File.Exists(fullPath))
            {
                return Response.Error(
                    $"Script already exists at '{relativePath}'. Use 'update' action to modify."
                );
            }

            // Generate default content if none provided
            if (string.IsNullOrEmpty(contents))
            {
                contents = GenerateDefaultScriptContent(name, scriptType, namespaceName);
            }

            // Validate syntax (basic check)
            if (!ValidateScriptSyntax(contents))
            {
                // Optionally return a specific error or warning about syntax
                // return Response.Error("Provided script content has potential syntax errors.");
                Debug.LogWarning($"Potential syntax error in script being created: {name}");
            }

            try
            {
                File.WriteAllText(fullPath, contents);
                AssetDatabase.ImportAsset(relativePath);
                AssetDatabase.Refresh(); // Ensure Unity recognizes the new script
                return Response.Success(
                    $"Script '{name}.cs' created successfully at '{relativePath}'.",
                    new { path = relativePath }
                );
            }
            catch (Exception e)
            {
                return Response.Error($"Failed to create script '{relativePath}': {e.Message}");
            }
        }

        private static object ReadScript(string fullPath, string relativePath)
        {
            if (!File.Exists(fullPath))
            {
                return Response.Error($"Script not found at '{relativePath}'.");
            }

            try
            {
                string contents = File.ReadAllText(fullPath);

                // Return both normal and encoded contents for larger files
                bool isLarge = contents.Length > 10000; // If content is large, include encoded version
                var responseData = new
                {
                    path = relativePath,
                    contents = contents,
                    // For large files, also include base64-encoded version
                    encodedContents = isLarge ? EncodeBase64(contents) : null,
                    contentsEncoded = isLarge,
                };

                return Response.Success(
                    $"Script '{Path.GetFileName(relativePath)}' read successfully.",
                    responseData
                );
            }
            catch (Exception e)
            {
                return Response.Error($"Failed to read script '{relativePath}': {e.Message}");
            }
        }

        private static object UpdateScript(
            string fullPath,
            string relativePath,
            string name,
            string contents
        )
        {
            if (!File.Exists(fullPath))
            {
                return Response.Error(
                    $"Script not found at '{relativePath}'. Use 'create' action to add a new script."
                );
            }
            if (string.IsNullOrEmpty(contents))
            {
                return Response.Error("Content is required for the 'update' action.");
            }

            // Validate syntax (basic check)
            if (!ValidateScriptSyntax(contents) && ValidateScriptSyntax(contents, out var errors))
            {
                // Optionally return a specific error or warning about syntax
                // return Response.Error("Provided script content has potential syntax errors.");
                 Debug.LogWarning($"Potential syntax error in script being updated: {name}");
                // Consider if this should be a hard error or just a warning
                // Log errors to console for debugging
                foreach (var error in errors)
                {
                    Debug.LogError($"Syntax error in script '{name}': {error}");
                }
                return Response.ReviseNeeded(
                    $"Script '{name}.cs' has potential syntax errors. Please revise.",
                    new { errors = errors }
                );
            }

            try
            {
                File.WriteAllText(fullPath, contents);
                AssetDatabase.ImportAsset(relativePath); // Re-import to reflect changes
                AssetDatabase.Refresh();
                return Response.Success(
                    $"Script '{name}.cs' updated successfully at '{relativePath}'.",
                    new { path = relativePath }
                );
            }
            catch (Exception e)
            {
                return Response.Error($"Failed to update script '{relativePath}': {e.Message}");
            }
        }

        private static object DeleteScript(string fullPath, string relativePath)
        {
            if (!File.Exists(fullPath))
            {
                return Response.Error($"Script not found at '{relativePath}'. Cannot delete.");
            }

            try
            {
                // Use AssetDatabase.MoveAssetToTrash for safer deletion (allows undo)
                bool deleted = AssetDatabase.MoveAssetToTrash(relativePath);
                if (deleted)
                {
                    AssetDatabase.Refresh();
                    return Response.Success(
                        $"Script '{Path.GetFileName(relativePath)}' moved to trash successfully."
                    );
                }
                else
                {
                    // Fallback or error if MoveAssetToTrash fails
                    return Response.Error(
                        $"Failed to move script '{relativePath}' to trash. It might be locked or in use."
                    );
                }
            }
            catch (Exception e)
            {
                return Response.Error($"Error deleting script '{relativePath}': {e.Message}");
            }
        }

        /// <summary>
        /// Generates basic C# script content based on name and type.
        /// </summary>
        private static string GenerateDefaultScriptContent(
            string name,
            string scriptType,
            string namespaceName
        )
        {
            string usingStatements = "using UnityEngine;\nusing System.Collections;\n";
            string classDeclaration;
            string body =
                "\n    // Use this for initialization\n    void Start() {\n\n    }\n\n    // Update is called once per frame\n    void Update() {\n\n    }\n";

            string baseClass = "";
            if (!string.IsNullOrEmpty(scriptType))
            {
                if (scriptType.Equals("MonoBehaviour", StringComparison.OrdinalIgnoreCase))
                    baseClass = " : MonoBehaviour";
                else if (scriptType.Equals("ScriptableObject", StringComparison.OrdinalIgnoreCase))
                {
                    baseClass = " : ScriptableObject";
                    body = ""; // ScriptableObjects don't usually need Start/Update
                }
                else if (
                    scriptType.Equals("Editor", StringComparison.OrdinalIgnoreCase)
                    || scriptType.Equals("EditorWindow", StringComparison.OrdinalIgnoreCase)
                )
                {
                    usingStatements += "using UnityEditor;\n";
                    if (scriptType.Equals("Editor", StringComparison.OrdinalIgnoreCase))
                        baseClass = " : Editor";
                    else
                        baseClass = " : EditorWindow";
                    body = ""; // Editor scripts have different structures
                }
                // Add more types as needed
            }

            classDeclaration = $"public class {name}{baseClass}";

            string fullContent = $"{usingStatements}\n";
            bool useNamespace = !string.IsNullOrEmpty(namespaceName);

            if (useNamespace)
            {
                fullContent += $"namespace {namespaceName}\n{{\n";
                // Indent class and body if using namespace
                classDeclaration = "    " + classDeclaration;
                body = string.Join("\n", body.Split('\n').Select(line => "    " + line));
            }

            fullContent += $"{classDeclaration}\n{{\n{body}\n}}";

            if (useNamespace)
            {
                fullContent += "\n}"; // Close namespace
            }

            return fullContent.Trim() + "\n"; // Ensure a trailing newline
        }

        /// <summary>
        /// Performs a very basic syntax validation (checks for balanced braces).
        /// TODO: Implement more robust syntax checking if possible.
        /// </summary>
        private static bool ValidateScriptSyntax(string contents)
        {
            if (string.IsNullOrEmpty(contents))
                return true; // Empty is technically valid?

            int braceBalance = 0;
            foreach (char c in contents)
            {
                if (c == '{')
                    braceBalance++;
                else if (c == '}')
                    braceBalance--;
            }

            return braceBalance == 0;
            // This is extremely basic. A real C# parser/compiler check would be ideal
            // but is complex to implement directly here.
        }

        /// <summary>
        /// Performs syntax validation using Roslyn (C# compiler platform).
        /// </summary>
        public static bool ValidateScriptSyntax(string contents, out List<string> errors)
        {
            errors = new List<string>();

            if (string.IsNullOrWhiteSpace(contents))
                return true; // empty content considered valid

            SyntaxTree syntaxTree = CSharpSyntaxTree.ParseText(contents);
            var diagnostics = syntaxTree.GetDiagnostics();

            bool hasErrors = diagnostics.Any(d => d.Severity == DiagnosticSeverity.Error);

            if (hasErrors)
            {
                errors = diagnostics
                    .Where(d => d.Severity == DiagnosticSeverity.Error)
                    .Select(d => d.ToString())
                    .ToList();
            }

            return !hasErrors;
        }
    }
}

