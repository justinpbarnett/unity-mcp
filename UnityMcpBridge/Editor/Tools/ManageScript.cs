using System;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using MCPForUnity.Editor.Helpers;

#if USE_ROSLYN
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
#endif

#if UNITY_EDITOR
using UnityEditor.Compilation;
#endif


namespace MCPForUnity.Editor.Tools
{
    /// <summary>
    /// Handles CRUD operations for C# scripts within the Unity project.
    /// 
    /// ROSLYN INSTALLATION GUIDE:
    /// To enable advanced syntax validation with Roslyn compiler services:
    /// 
    /// 1. Install Microsoft.CodeAnalysis.CSharp NuGet package:
    ///    - Open Package Manager in Unity
    ///    - Follow the instruction on https://github.com/GlitchEnzo/NuGetForUnity
    ///    
    /// 2. Open NuGet Package Manager and Install Microsoft.CodeAnalysis.CSharp:
    ///    
    /// 3. Alternative: Manual DLL installation:
    ///    - Download Microsoft.CodeAnalysis.CSharp.dll and dependencies
    ///    - Place in Assets/Plugins/ folder
    ///    - Ensure .NET compatibility settings are correct
    ///    
    /// 4. Define USE_ROSLYN symbol:
    ///    - Go to Player Settings > Scripting Define Symbols
    ///    - Add "USE_ROSLYN" to enable Roslyn-based validation
    ///    
    /// 5. Restart Unity after installation
    /// 
    /// Note: Without Roslyn, the system falls back to basic structural validation.
    /// Roslyn provides full C# compiler diagnostics with line numbers and detailed error messages.
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

            // Validate syntax with detailed error reporting using GUI setting
            ValidationLevel validationLevel = GetValidationLevelFromGUI();
            bool isValid = ValidateScriptSyntax(contents, validationLevel, out string[] validationErrors);
            if (!isValid)
            {
                string errorMessage = "Script validation failed:\n" + string.Join("\n", validationErrors);
                return Response.Error(errorMessage);
            }
            else if (validationErrors != null && validationErrors.Length > 0)
            {
                // Log warnings but don't block creation
                Debug.LogWarning($"Script validation warnings for {name}:\n" + string.Join("\n", validationErrors));
            }

            try
            {
                File.WriteAllText(fullPath, contents, new System.Text.UTF8Encoding(false));
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

            // Validate syntax with detailed error reporting using GUI setting
            ValidationLevel validationLevel = GetValidationLevelFromGUI();
            bool isValid = ValidateScriptSyntax(contents, validationLevel, out string[] validationErrors);
            if (!isValid)
            {
                string errorMessage = "Script validation failed:\n" + string.Join("\n", validationErrors);
                return Response.Error(errorMessage);
            }
            else if (validationErrors != null && validationErrors.Length > 0)
            {
                // Log warnings but don't block update
                Debug.LogWarning($"Script validation warnings for {name}:\n" + string.Join("\n", validationErrors));
            }

            try
            {
                File.WriteAllText(fullPath, contents, new System.Text.UTF8Encoding(false));
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
        /// Gets the validation level from the GUI settings
        /// </summary>
        private static ValidationLevel GetValidationLevelFromGUI()
        {
            string savedLevel = EditorPrefs.GetString("MCPForUnity_ScriptValidationLevel", "standard");
            return savedLevel.ToLower() switch
            {
                "basic" => ValidationLevel.Basic,
                "standard" => ValidationLevel.Standard,
                "comprehensive" => ValidationLevel.Comprehensive,
                "strict" => ValidationLevel.Strict,
                _ => ValidationLevel.Standard // Default fallback
            };
        }

        /// <summary>
        /// Validates C# script syntax using multiple validation layers.
        /// </summary>
        private static bool ValidateScriptSyntax(string contents)
        {
            return ValidateScriptSyntax(contents, ValidationLevel.Standard, out _);
        }

        /// <summary>
        /// Advanced syntax validation with detailed diagnostics and configurable strictness.
        /// </summary>
        private static bool ValidateScriptSyntax(string contents, ValidationLevel level, out string[] errors)
        {
            var errorList = new System.Collections.Generic.List<string>();
            errors = null;

            if (string.IsNullOrEmpty(contents))
            {
                return true; // Empty content is valid
            }

            // Basic structural validation
            if (!ValidateBasicStructure(contents, errorList))
            {
                errors = errorList.ToArray();
                return false;
            }

#if USE_ROSLYN
            // Advanced Roslyn-based validation
            if (!ValidateScriptSyntaxRoslyn(contents, level, errorList))
            {
                errors = errorList.ToArray();
                return level != ValidationLevel.Standard; //TODO: Allow standard to run roslyn right now, might formalize it in the future
            }
#endif

            // Unity-specific validation
            if (level >= ValidationLevel.Standard)
            {
                ValidateScriptSyntaxUnity(contents, errorList);
            }

            // Semantic analysis for common issues
            if (level >= ValidationLevel.Comprehensive)
            {
                ValidateSemanticRules(contents, errorList);
            }

#if USE_ROSLYN
            // Full semantic compilation validation for Strict level
            if (level == ValidationLevel.Strict)
            {
                if (!ValidateScriptSemantics(contents, errorList))
                {
                    errors = errorList.ToArray();
                    return false; // Strict level fails on any semantic errors
                }
            }
#endif

            errors = errorList.ToArray();
            return errorList.Count == 0 || (level != ValidationLevel.Strict && !errorList.Any(e => e.StartsWith("ERROR:")));
        }

        /// <summary>
        /// Validation strictness levels
        /// </summary>
        private enum ValidationLevel
        {
            Basic,        // Only syntax errors
            Standard,     // Syntax + Unity best practices
            Comprehensive, // All checks + semantic analysis
            Strict        // Treat all issues as errors
        }

        /// <summary>
        /// Validates basic code structure (braces, quotes, comments)
        /// </summary>
        private static bool ValidateBasicStructure(string contents, System.Collections.Generic.List<string> errors)
        {
            bool isValid = true;
            int braceBalance = 0;
            int parenBalance = 0;
            int bracketBalance = 0;
            bool inStringLiteral = false;
            bool inCharLiteral = false;
            bool inSingleLineComment = false;
            bool inMultiLineComment = false;
            bool escaped = false;

            for (int i = 0; i < contents.Length; i++)
            {
                char c = contents[i];
                char next = i + 1 < contents.Length ? contents[i + 1] : '\0';

                // Handle escape sequences
                if (escaped)
                {
                    escaped = false;
                    continue;
                }

                if (c == '\\' && (inStringLiteral || inCharLiteral))
                {
                    escaped = true;
                    continue;
                }

                // Handle comments
                if (!inStringLiteral && !inCharLiteral)
                {
                    if (c == '/' && next == '/' && !inMultiLineComment)
                    {
                        inSingleLineComment = true;
                        continue;
                    }
                    if (c == '/' && next == '*' && !inSingleLineComment)
                    {
                        inMultiLineComment = true;
                        i++; // Skip next character
                        continue;
                    }
                    if (c == '*' && next == '/' && inMultiLineComment)
                    {
                        inMultiLineComment = false;
                        i++; // Skip next character
                        continue;
                    }
                }

                if (c == '\n')
                {
                    inSingleLineComment = false;
                    continue;
                }

                if (inSingleLineComment || inMultiLineComment)
                    continue;

                // Handle string and character literals
                if (c == '"' && !inCharLiteral)
                {
                    inStringLiteral = !inStringLiteral;
                    continue;
                }
                if (c == '\'' && !inStringLiteral)
                {
                    inCharLiteral = !inCharLiteral;
                    continue;
                }

                if (inStringLiteral || inCharLiteral)
                    continue;

                // Count brackets and braces
                switch (c)
                {
                    case '{': braceBalance++; break;
                    case '}': braceBalance--; break;
                    case '(': parenBalance++; break;
                    case ')': parenBalance--; break;
                    case '[': bracketBalance++; break;
                    case ']': bracketBalance--; break;
                }

                // Check for negative balances (closing without opening)
                if (braceBalance < 0)
                {
                    errors.Add("ERROR: Unmatched closing brace '}'");
                    isValid = false;
                }
                if (parenBalance < 0)
                {
                    errors.Add("ERROR: Unmatched closing parenthesis ')'");
                    isValid = false;
                }
                if (bracketBalance < 0)
                {
                    errors.Add("ERROR: Unmatched closing bracket ']'");
                    isValid = false;
                }
            }

            // Check final balances
            if (braceBalance != 0)
            {
                errors.Add($"ERROR: Unbalanced braces (difference: {braceBalance})");
                isValid = false;
            }
            if (parenBalance != 0)
            {
                errors.Add($"ERROR: Unbalanced parentheses (difference: {parenBalance})");
                isValid = false;
            }
            if (bracketBalance != 0)
            {
                errors.Add($"ERROR: Unbalanced brackets (difference: {bracketBalance})");
                isValid = false;
            }
            if (inStringLiteral)
            {
                errors.Add("ERROR: Unterminated string literal");
                isValid = false;
            }
            if (inCharLiteral)
            {
                errors.Add("ERROR: Unterminated character literal");
                isValid = false;
            }
            if (inMultiLineComment)
            {
                errors.Add("WARNING: Unterminated multi-line comment");
            }

            return isValid;
        }

#if USE_ROSLYN
        /// <summary>
        /// Cached compilation references for performance
        /// </summary>
        private static System.Collections.Generic.List<MetadataReference> _cachedReferences = null;
        private static DateTime _cacheTime = DateTime.MinValue;
        private static readonly TimeSpan CacheExpiry = TimeSpan.FromMinutes(5);

        /// <summary>
        /// Validates syntax using Roslyn compiler services
        /// </summary>
        private static bool ValidateScriptSyntaxRoslyn(string contents, ValidationLevel level, System.Collections.Generic.List<string> errors)
        {
            try
            {
                var syntaxTree = CSharpSyntaxTree.ParseText(contents);
                var diagnostics = syntaxTree.GetDiagnostics();
                
                bool hasErrors = false;
                foreach (var diagnostic in diagnostics)
                {
                    string severity = diagnostic.Severity.ToString().ToUpper();
                    string message = $"{severity}: {diagnostic.GetMessage()}";
                    
                    if (diagnostic.Severity == DiagnosticSeverity.Error)
                    {
                        hasErrors = true;
                    }
                    
                    // Include warnings in comprehensive mode
                    if (level >= ValidationLevel.Standard || diagnostic.Severity == DiagnosticSeverity.Error) //Also use Standard for now
                    {
                        var location = diagnostic.Location.GetLineSpan();
                        if (location.IsValid)
                        {
                            message += $" (Line {location.StartLinePosition.Line + 1})";
                        }
                        errors.Add(message);
                    }
                }
                
                return !hasErrors;
            }
            catch (Exception ex)
            {
                errors.Add($"ERROR: Roslyn validation failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Validates script semantics using full compilation context to catch namespace, type, and method resolution errors
        /// </summary>
        private static bool ValidateScriptSemantics(string contents, System.Collections.Generic.List<string> errors)
        {
            try
            {
                // Get compilation references with caching
                var references = GetCompilationReferences();
                if (references == null || references.Count == 0)
                {
                    errors.Add("WARNING: Could not load compilation references for semantic validation");
                    return true; // Don't fail if we can't get references
                }

                // Create syntax tree
                var syntaxTree = CSharpSyntaxTree.ParseText(contents);

                // Create compilation with full context
                var compilation = CSharpCompilation.Create(
                    "TempValidation",
                    new[] { syntaxTree },
                    references,
                    new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary)
                );

                // Get semantic diagnostics - this catches all the issues you mentioned!
                var diagnostics = compilation.GetDiagnostics();
                
                bool hasErrors = false;
                foreach (var diagnostic in diagnostics)
                {
                    if (diagnostic.Severity == DiagnosticSeverity.Error)
                    {
                        hasErrors = true;
                        var location = diagnostic.Location.GetLineSpan();
                        string locationInfo = location.IsValid ? 
                            $" (Line {location.StartLinePosition.Line + 1}, Column {location.StartLinePosition.Character + 1})" : "";
                        
                        // Include diagnostic ID for better error identification
                        string diagnosticId = !string.IsNullOrEmpty(diagnostic.Id) ? $" [{diagnostic.Id}]" : "";
                        errors.Add($"ERROR: {diagnostic.GetMessage()}{diagnosticId}{locationInfo}");
                    }
                    else if (diagnostic.Severity == DiagnosticSeverity.Warning)
                    {
                        var location = diagnostic.Location.GetLineSpan();
                        string locationInfo = location.IsValid ? 
                            $" (Line {location.StartLinePosition.Line + 1}, Column {location.StartLinePosition.Character + 1})" : "";
                        
                        string diagnosticId = !string.IsNullOrEmpty(diagnostic.Id) ? $" [{diagnostic.Id}]" : "";
                        errors.Add($"WARNING: {diagnostic.GetMessage()}{diagnosticId}{locationInfo}");
                    }
                }
                
                return !hasErrors;
            }
            catch (Exception ex)
            {
                errors.Add($"ERROR: Semantic validation failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Gets compilation references with caching for performance
        /// </summary>
        private static System.Collections.Generic.List<MetadataReference> GetCompilationReferences()
        {
            // Check cache validity
            if (_cachedReferences != null && DateTime.Now - _cacheTime < CacheExpiry)
            {
                return _cachedReferences;
            }

            try
            {
                var references = new System.Collections.Generic.List<MetadataReference>();

                // Core .NET assemblies
                references.Add(MetadataReference.CreateFromFile(typeof(object).Assembly.Location)); // mscorlib/System.Private.CoreLib
                references.Add(MetadataReference.CreateFromFile(typeof(System.Linq.Enumerable).Assembly.Location)); // System.Linq
                references.Add(MetadataReference.CreateFromFile(typeof(System.Collections.Generic.List<>).Assembly.Location)); // System.Collections

                // Unity assemblies
                try
                {
                    references.Add(MetadataReference.CreateFromFile(typeof(UnityEngine.Debug).Assembly.Location)); // UnityEngine
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"Could not load UnityEngine assembly: {ex.Message}");
                }

#if UNITY_EDITOR
                try
                {
                    references.Add(MetadataReference.CreateFromFile(typeof(UnityEditor.Editor).Assembly.Location)); // UnityEditor
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"Could not load UnityEditor assembly: {ex.Message}");
                }

                // Get Unity project assemblies
                try
                {
                    var assemblies = CompilationPipeline.GetAssemblies();
                    foreach (var assembly in assemblies)
                    {
                        if (File.Exists(assembly.outputPath))
                        {
                            references.Add(MetadataReference.CreateFromFile(assembly.outputPath));
                        }
                    }
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"Could not load Unity project assemblies: {ex.Message}");
                }
#endif

                // Cache the results
                _cachedReferences = references;
                _cacheTime = DateTime.Now;

                return references;
            }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to get compilation references: {ex.Message}");
                return new System.Collections.Generic.List<MetadataReference>();
            }
        }
#else
        private static bool ValidateScriptSyntaxRoslyn(string contents, ValidationLevel level, System.Collections.Generic.List<string> errors)
        {
            // Fallback when Roslyn is not available
            return true;
        }
#endif

        /// <summary>
        /// Validates Unity-specific coding rules and best practices
        /// //TODO: Naive Unity Checks and not really yield any results, need to be improved
        /// </summary>
        private static void ValidateScriptSyntaxUnity(string contents, System.Collections.Generic.List<string> errors)
        {
            // Check for common Unity anti-patterns
            if (contents.Contains("FindObjectOfType") && contents.Contains("Update()"))
            {
                errors.Add("WARNING: FindObjectOfType in Update() can cause performance issues");
            }

            if (contents.Contains("GameObject.Find") && contents.Contains("Update()"))
            {
                errors.Add("WARNING: GameObject.Find in Update() can cause performance issues");
            }

            // Check for proper MonoBehaviour usage
            if (contents.Contains(": MonoBehaviour") && !contents.Contains("using UnityEngine"))
            {
                errors.Add("WARNING: MonoBehaviour requires 'using UnityEngine;'");
            }

            // Check for SerializeField usage
            if (contents.Contains("[SerializeField]") && !contents.Contains("using UnityEngine"))
            {
                errors.Add("WARNING: SerializeField requires 'using UnityEngine;'");
            }

            // Check for proper coroutine usage
            if (contents.Contains("StartCoroutine") && !contents.Contains("IEnumerator"))
            {
                errors.Add("WARNING: StartCoroutine typically requires IEnumerator methods");
            }

            // Check for Update without FixedUpdate for physics
            if (contents.Contains("Rigidbody") && contents.Contains("Update()") && !contents.Contains("FixedUpdate()"))
            {
                errors.Add("WARNING: Consider using FixedUpdate() for Rigidbody operations");
            }

            // Check for missing null checks on Unity objects
            if (contents.Contains("GetComponent<") && !contents.Contains("!= null"))
            {
                errors.Add("WARNING: Consider null checking GetComponent results");
            }

            // Check for proper event function signatures
            if (contents.Contains("void Start(") && !contents.Contains("void Start()"))
            {
                errors.Add("WARNING: Start() should not have parameters");
            }

            if (contents.Contains("void Update(") && !contents.Contains("void Update()"))
            {
                errors.Add("WARNING: Update() should not have parameters");
            }

            // Check for inefficient string operations
            if (contents.Contains("Update()") && contents.Contains("\"") && contents.Contains("+"))
            {
                errors.Add("WARNING: String concatenation in Update() can cause garbage collection issues");
            }
        }

        /// <summary>
        /// Validates semantic rules and common coding issues
        /// </summary>
        private static void ValidateSemanticRules(string contents, System.Collections.Generic.List<string> errors)
        {
            // Check for potential memory leaks
            if (contents.Contains("new ") && contents.Contains("Update()"))
            {
                errors.Add("WARNING: Creating objects in Update() may cause memory issues");
            }

            // Check for magic numbers
            var magicNumberPattern = new Regex(@"\b\d+\.?\d*f?\b(?!\s*[;})\]])");
            var matches = magicNumberPattern.Matches(contents);
            if (matches.Count > 5)
            {
                errors.Add("WARNING: Consider using named constants instead of magic numbers");
            }

            // Check for long methods (simple line count check)
            var methodPattern = new Regex(@"(public|private|protected|internal)?\s*(static)?\s*\w+\s+\w+\s*\([^)]*\)\s*{");
            var methodMatches = methodPattern.Matches(contents);
            foreach (Match match in methodMatches)
            {
                int startIndex = match.Index;
                int braceCount = 0;
                int lineCount = 0;
                bool inMethod = false;

                for (int i = startIndex; i < contents.Length; i++)
                {
                    if (contents[i] == '{')
                    {
                        braceCount++;
                        inMethod = true;
                    }
                    else if (contents[i] == '}')
                    {
                        braceCount--;
                        if (braceCount == 0 && inMethod)
                            break;
                    }
                    else if (contents[i] == '\n' && inMethod)
                    {
                        lineCount++;
                    }
                }

                if (lineCount > 50)
                {
                    errors.Add("WARNING: Method is very long, consider breaking it into smaller methods");
                    break; // Only report once
                }
            }

            // Check for proper exception handling
            if (contents.Contains("catch") && contents.Contains("catch()"))
            {
                errors.Add("WARNING: Empty catch blocks should be avoided");
            }

            // Check for proper async/await usage
            if (contents.Contains("async ") && !contents.Contains("await"))
            {
                errors.Add("WARNING: Async method should contain await or return Task");
            }

            // Check for hardcoded tags and layers
            if (contents.Contains("\"Player\"") || contents.Contains("\"Enemy\""))
            {
                errors.Add("WARNING: Consider using constants for tags instead of hardcoded strings");
            }
        }

        //TODO: A easier way for users to update incorrect scripts (now duplicated with the updateScript method and need to also update server side, put aside for now)
        /// <summary>
        /// Public method to validate script syntax with configurable validation level
        /// Returns detailed validation results including errors and warnings
        /// </summary>
        // public static object ValidateScript(JObject @params)
        // {
        //     string contents = @params["contents"]?.ToString();
        //     string validationLevel = @params["validationLevel"]?.ToString() ?? "standard";

        //     if (string.IsNullOrEmpty(contents))
        //     {
        //         return Response.Error("Contents parameter is required for validation.");
        //     }

        //     // Parse validation level
        //     ValidationLevel level = ValidationLevel.Standard;
        //     switch (validationLevel.ToLower())
        //     {
        //         case "basic": level = ValidationLevel.Basic; break;
        //         case "standard": level = ValidationLevel.Standard; break;
        //         case "comprehensive": level = ValidationLevel.Comprehensive; break;
        //         case "strict": level = ValidationLevel.Strict; break;
        //         default:
        //             return Response.Error($"Invalid validation level: '{validationLevel}'. Valid levels are: basic, standard, comprehensive, strict.");
        //     }

        //     // Perform validation
        //     bool isValid = ValidateScriptSyntax(contents, level, out string[] validationErrors);

        //     var errors = validationErrors?.Where(e => e.StartsWith("ERROR:")).ToArray() ?? new string[0];
        //     var warnings = validationErrors?.Where(e => e.StartsWith("WARNING:")).ToArray() ?? new string[0];

        //     var result = new
        //     {
        //         isValid = isValid,
        //         validationLevel = validationLevel,
        //         errorCount = errors.Length,
        //         warningCount = warnings.Length,
        //         errors = errors,
        //         warnings = warnings,
        //         summary = isValid 
        //             ? (warnings.Length > 0 ? $"Validation passed with {warnings.Length} warnings" : "Validation passed with no issues")
        //             : $"Validation failed with {errors.Length} errors and {warnings.Length} warnings"
        //     };

        //     if (isValid)
        //     {
        //         return Response.Success("Script validation completed successfully.", result);
        //     }
        //     else
        //     {
        //         return Response.Error("Script validation failed.", result);
        //     }
        // }
    }
}

