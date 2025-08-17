using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;
using UnityMcpBridge.Editor.Helpers;
using System.Threading;
using System.Security.Cryptography;

#if USE_ROSLYN
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Formatting;
#endif

#if UNITY_EDITOR
using UnityEditor.Compilation;
#endif


namespace UnityMcpBridge.Editor.Tools
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
        /// Resolves a directory under Assets/, preventing traversal and escaping.
        /// Returns fullPathDir on disk and canonical 'Assets/...' relative path.
        /// </summary>
        private static bool TryResolveUnderAssets(string relDir, out string fullPathDir, out string relPathSafe)
        {
            string assets = Application.dataPath.Replace('\\', '/');

            // Normalize caller path: allow both "Scripts/..." and "Assets/Scripts/..."
            string rel = (relDir ?? "Scripts").Replace('\\', '/').Trim();
            if (string.IsNullOrEmpty(rel)) rel = "Scripts";
            if (rel.StartsWith("Assets/", StringComparison.OrdinalIgnoreCase)) rel = rel.Substring(7);
            rel = rel.TrimStart('/');

            string targetDir = Path.Combine(assets, rel).Replace('\\', '/');
            string full = Path.GetFullPath(targetDir).Replace('\\', '/');

            bool underAssets = full.StartsWith(assets + "/", StringComparison.OrdinalIgnoreCase)
                               || string.Equals(full, assets, StringComparison.OrdinalIgnoreCase);
            if (!underAssets)
            {
                fullPathDir = null;
                relPathSafe = null;
                return false;
            }

            // Best-effort symlink guard: if directory is a reparse point/symlink, reject
            try
            {
                var di = new DirectoryInfo(full);
                if (di.Exists)
                {
                    var attrs = di.Attributes;
                    if ((attrs & FileAttributes.ReparsePoint) != 0)
                    {
                        fullPathDir = null;
                        relPathSafe = null;
                        return false;
                    }
                }
            }
            catch { /* best effort; proceed */ }

            fullPathDir = full;
            string tail = full.Length > assets.Length ? full.Substring(assets.Length).TrimStart('/') : string.Empty;
            relPathSafe = ("Assets/" + tail).TrimEnd('/');
            return true;
        }
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

            // Resolve and harden target directory under Assets/
            if (!TryResolveUnderAssets(path, out string fullPathDir, out string relPathSafeDir))
            {
                return Response.Error($"Invalid path. Target directory must be within 'Assets/'. Provided: '{(path ?? "(null)")}'");
            }

            // Construct file paths
            string scriptFileName = $"{name}.cs";
            string fullPath = Path.Combine(fullPathDir, scriptFileName);
            string relativePath = Path.Combine(relPathSafeDir, scriptFileName).Replace('\\', '/');

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
                    Debug.LogWarning("manage_script.read is deprecated; prefer resources/read. Serving read for backward compatibility.");
                    return ReadScript(fullPath, relativePath);
                case "update":
                    Debug.LogWarning("manage_script.update is deprecated; prefer apply_text_edits. Serving update for backward compatibility.");
                    return UpdateScript(fullPath, relativePath, name, contents);
                case "delete":
                    return DeleteScript(fullPath, relativePath);
                case "apply_text_edits":
                {
                    var textEdits = @params["edits"] as JArray;
                    string precondition = @params["precondition_sha256"]?.ToString();
                    return ApplyTextEdits(fullPath, relativePath, name, textEdits, precondition);
                }
                case "validate":
                {
                    string level = @params["level"]?.ToString()?.ToLowerInvariant() ?? "standard";
                    var chosen = level switch
                    {
                        "basic" => ValidationLevel.Basic,
                        "standard" => ValidationLevel.Standard,
                        "strict" => ValidationLevel.Strict,
                        "comprehensive" => ValidationLevel.Comprehensive,
                        _ => ValidationLevel.Standard
                    };
                    string fileText;
                    try { fileText = File.ReadAllText(fullPath); }
                    catch (Exception ex) { return Response.Error($"Failed to read script: {ex.Message}"); }

                    bool ok = ValidateScriptSyntax(fileText, chosen, out string[] diagsRaw);
                    var diags = (diagsRaw ?? Array.Empty<string>()).Select(s =>
                    {
                        var m = Regex.Match(s, @"^(ERROR|WARNING|INFO): (.*?)(?: \(Line (\d+)\))?$");
                        string severity = m.Success ? m.Groups[1].Value.ToLowerInvariant() : "info";
                        string message = m.Success ? m.Groups[2].Value : s;
                        int lineNum = m.Success && int.TryParse(m.Groups[3].Value, out var l) ? l : 0;
                        return new { line = lineNum, col = 0, severity, message };
                    }).ToArray();

                    var result = new { diagnostics = diags };
                    return ok ? Response.Success("Validation completed.", result)
                               : Response.Error("Validation failed.", result);
                }
                case "edit":
                    Debug.LogWarning("manage_script.edit is deprecated; prefer apply_text_edits. Serving structured edit for backward compatibility.");
                    var structEdits = @params["edits"] as JArray;
                    var options = @params["options"] as JObject;
                    return EditScript(fullPath, relativePath, name, structEdits, options);
                default:
                    return Response.Error(
                        $"Unknown action: '{action}'. Valid actions are: create, delete, apply_text_edits, validate, read (deprecated), update (deprecated), edit (deprecated)."
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
                // Atomic-ish create
                var enc = System.Text.Encoding.UTF8;
                var tmp = fullPath + ".tmp";
                File.WriteAllText(tmp, contents, enc);
                try
                {
                    // Prefer atomic move within same volume
                    File.Move(tmp, fullPath);
                }
                catch (IOException)
                {
                    // Cross-volume or other IO constraint: fallback to copy
                    File.Copy(tmp, fullPath, overwrite: true);
                    try { File.Delete(tmp); } catch { }
                }

                var uri = $"unity://path/{relativePath}";
                var ok = Response.Success(
                    $"Script '{name}.cs' created successfully at '{relativePath}'.",
                    new { uri, scheduledRefresh = true }
                );

                // Schedule heavy work AFTER replying
                ManageScriptRefreshHelpers.ScheduleScriptRefresh(relativePath);
                return ok;
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
                var uri = $"unity://path/{relativePath}";
                var responseData = new
                {
                    uri,
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
                // Safe write with atomic replace when available
                var encoding = System.Text.Encoding.UTF8;
                string tempPath = fullPath + ".tmp";
                File.WriteAllText(tempPath, contents, encoding);

                string backupPath = fullPath + ".bak";
                try
                {
                    File.Replace(tempPath, fullPath, backupPath);
                    // Clean up backup to avoid stray assets inside the project
                    try
                    {
                        if (File.Exists(backupPath))
                            File.Delete(backupPath);
                    }
                    catch
                    {
                        // ignore failures deleting the backup
                    }
                }
                catch (PlatformNotSupportedException)
                {
                    File.Copy(tempPath, fullPath, true);
                    try { File.Delete(tempPath); } catch { }
                    try { if (File.Exists(backupPath)) File.Delete(backupPath); } catch { }
                }
                catch (IOException)
                {
                    // Cross-volume moves can throw IOException; fallback to copy
                    File.Copy(tempPath, fullPath, true);
                    try { File.Delete(tempPath); } catch { }
                    try { if (File.Exists(backupPath)) File.Delete(backupPath); } catch { }
                }

                // Prepare success response BEFORE any operation that can trigger a domain reload
                var uri = $"unity://path/{relativePath}";
                var ok = Response.Success(
                    $"Script '{name}.cs' updated successfully at '{relativePath}'.",
                    new { uri, path = relativePath, scheduledRefresh = true }
                );

                // Schedule a debounced import/compile on next editor tick to avoid stalling the reply
                ManageScriptRefreshHelpers.ScheduleScriptRefresh(relativePath);

                return ok;
            }
            catch (Exception e)
            {
                return Response.Error($"Failed to update script '{relativePath}': {e.Message}");
            }
        }

        /// <summary>
        /// Apply simple text edits specified by line/column ranges. Applies transactionally and validates result.
        /// </summary>
        private const int MaxEditPayloadBytes = 15 * 1024;

        private static object ApplyTextEdits(
            string fullPath,
            string relativePath,
            string name,
            JArray edits,
            string preconditionSha256)
        {
            if (!File.Exists(fullPath))
                return Response.Error($"Script not found at '{relativePath}'.");
            // Refuse edits if the target is a symlink
            try
            {
                var attrs = File.GetAttributes(fullPath);
                if ((attrs & FileAttributes.ReparsePoint) != 0)
                    return Response.Error("Refusing to edit a symlinked script path.");
            }
            catch
            {
                // If checking attributes fails, proceed without the symlink guard
            }
            if (edits == null || edits.Count == 0)
                return Response.Error("No edits provided.");

            string original;
            try { original = File.ReadAllText(fullPath); }
            catch (Exception ex) { return Response.Error($"Failed to read script: {ex.Message}"); }

            string currentSha = ComputeSha256(original);
            if (!string.IsNullOrEmpty(preconditionSha256) && !preconditionSha256.Equals(currentSha, StringComparison.OrdinalIgnoreCase))
            {
                return Response.Error("stale_file", new { status = "stale_file", expected_sha256 = preconditionSha256, current_sha256 = currentSha });
            }

            // Convert edits to absolute index ranges
            var spans = new List<(int start, int end, string text)>();
            long totalBytes = 0;
            foreach (var e in edits)
            {
                try
                {
                    int sl = Math.Max(1, e.Value<int>("startLine"));
                    int sc = Math.Max(1, e.Value<int>("startCol"));
                    int el = Math.Max(1, e.Value<int>("endLine"));
                    int ec = Math.Max(1, e.Value<int>("endCol"));
                    string newText = e.Value<string>("newText") ?? string.Empty;

                    if (!TryIndexFromLineCol(original, sl, sc, out int sidx))
                        return Response.Error($"apply_text_edits: start out of range (line {sl}, col {sc})");
                    if (!TryIndexFromLineCol(original, el, ec, out int eidx))
                        return Response.Error($"apply_text_edits: end out of range (line {el}, col {ec})");
                    if (eidx < sidx) (sidx, eidx) = (eidx, sidx);

                    spans.Add((sidx, eidx, newText));
                    checked
                    {
                        totalBytes += System.Text.Encoding.UTF8.GetByteCount(newText);
                    }
                }
                catch (Exception ex)
                {
                    return Response.Error($"Invalid edit payload: {ex.Message}");
                }
            }

            if (totalBytes > MaxEditPayloadBytes)
            {
                return Response.Error("too_large", new { status = "too_large", limitBytes = MaxEditPayloadBytes, hint = "split into smaller edits" });
            }

            // Ensure non-overlap and apply from back to front
            spans = spans.OrderByDescending(t => t.start).ToList();
            for (int i = 1; i < spans.Count; i++)
            {
                if (spans[i].end > spans[i - 1].start)
                    return Response.Error("Edits overlap; split into separate calls or adjust ranges.");
            }

            string working = original;
            foreach (var sp in spans)
            {
                working = working.Remove(sp.start, sp.end - sp.start).Insert(sp.start, sp.text ?? string.Empty);
            }

            if (!CheckBalancedDelimiters(working, out int line, out char expected))
            {
                int startLine = Math.Max(1, line - 5);
                int endLine = line + 5;
                string hint = $"unbalanced_braces at line {line}. Call resources/read for lines {startLine}-{endLine} and resend a smaller apply_text_edits that restores balance.";
                return Response.Error(hint, new { status = "unbalanced_braces", line, expected = expected.ToString() });
            }

#if USE_ROSLYN
            var tree = CSharpSyntaxTree.ParseText(working);
            var diagnostics = tree.GetDiagnostics().Where(d => d.Severity == DiagnosticSeverity.Error).Take(3)
                .Select(d => new {
                    line = d.Location.GetLineSpan().StartLinePosition.Line + 1,
                    col = d.Location.GetLineSpan().StartLinePosition.Character + 1,
                    code = d.Id,
                    message = d.GetMessage()
                }).ToArray();
            if (diagnostics.Length > 0)
            {
                return Response.Error("syntax_error", new { status = "syntax_error", diagnostics });
            }

            // Optional formatting
            try
            {
                var root = tree.GetRoot();
                var workspace = new AdhocWorkspace();
                root = Microsoft.CodeAnalysis.Formatting.Formatter.Format(root, workspace);
                working = root.ToFullString();
            }
            catch { }
#endif

            string newSha = ComputeSha256(working);

            // Atomic write and schedule refresh
            try
            {
                var enc = System.Text.Encoding.UTF8;
                var tmp = fullPath + ".tmp";
                File.WriteAllText(tmp, working, enc);
                string backup = fullPath + ".bak";
                try
                {
                    File.Replace(tmp, fullPath, backup);
                    try { if (File.Exists(backup)) File.Delete(backup); } catch { /* ignore */ }
                }
                catch (PlatformNotSupportedException)
                {
                    File.Copy(tmp, fullPath, true);
                    try { File.Delete(tmp); } catch { }
                    try { if (File.Exists(backup)) File.Delete(backup); } catch { }
                }
                catch (IOException)
                {
                    File.Copy(tmp, fullPath, true);
                    try { File.Delete(tmp); } catch { }
                    try { if (File.Exists(backup)) File.Delete(backup); } catch { }
                }

                ManageScriptRefreshHelpers.ScheduleScriptRefresh(relativePath);
                return Response.Success(
                    $"Applied {spans.Count} text edit(s) to '{relativePath}'.",
                    new
                    {
                        applied = spans.Count,
                        unchanged = 0,
                        sha256 = newSha,
                        uri = $"unity://path/{relativePath}",
                        scheduledRefresh = true
                    }
                );
            }
            catch (Exception ex)
            {
                return Response.Error($"Failed to write edits: {ex.Message}");
            }
        }

        private static bool TryIndexFromLineCol(string text, int line1, int col1, out int index)
        {
            // 1-based line/col to absolute index (0-based), col positions are counted in code points
            int line = 1, col = 1;
            for (int i = 0; i <= text.Length; i++)
            {
                if (line == line1 && col == col1)
                {
                    index = i;
                    return true;
                }
                if (i == text.Length) break;
                char c = text[i];
                if (c == '\r')
                {
                    // Treat CRLF as a single newline; skip the LF if present
                    if (i + 1 < text.Length && text[i + 1] == '\n')
                        i++;
                    line++;
                    col = 1;
                }
                else if (c == '\n')
                {
                    line++;
                    col = 1;
                }
                else
                {
                    col++;
                }
            }
            index = -1;
            return false;
        }

        private static string ComputeSha256(string contents)
        {
            using (var sha = SHA256.Create())
            {
                var bytes = System.Text.Encoding.UTF8.GetBytes(contents);
                var hash = sha.ComputeHash(bytes);
                return BitConverter.ToString(hash).Replace("-", string.Empty).ToLowerInvariant();
            }
        }

        private static bool CheckBalancedDelimiters(string text, out int line, out char expected)
        {
            var braceStack = new Stack<int>();
            var parenStack = new Stack<int>();
            var bracketStack = new Stack<int>();
            bool inString = false, inChar = false, inSingle = false, inMulti = false, escape = false;
            line = 1; expected = '\0';

            for (int i = 0; i < text.Length; i++)
            {
                char c = text[i];
                char next = i + 1 < text.Length ? text[i + 1] : '\0';

                if (c == '\n') { line++; if (inSingle) inSingle = false; }

                if (escape) { escape = false; continue; }

                if (inString)
                {
                    if (c == '\\') { escape = true; }
                    else if (c == '"') inString = false;
                    continue;
                }
                if (inChar)
                {
                    if (c == '\\') { escape = true; }
                    else if (c == '\'') inChar = false;
                    continue;
                }
                if (inSingle) continue;
                if (inMulti)
                {
                    if (c == '*' && next == '/') { inMulti = false; i++; }
                    continue;
                }

                if (c == '"') { inString = true; continue; }
                if (c == '\'') { inChar = true; continue; }
                if (c == '/' && next == '/') { inSingle = true; i++; continue; }
                if (c == '/' && next == '*') { inMulti = true; i++; continue; }

                switch (c)
                {
                    case '{': braceStack.Push(line); break;
                    case '}':
                        if (braceStack.Count == 0) { expected = '{'; return false; }
                        braceStack.Pop();
                        break;
                    case '(': parenStack.Push(line); break;
                    case ')':
                        if (parenStack.Count == 0) { expected = '('; return false; }
                        parenStack.Pop();
                        break;
                    case '[': bracketStack.Push(line); break;
                    case ']':
                        if (bracketStack.Count == 0) { expected = '['; return false; }
                        bracketStack.Pop();
                        break;
                }
            }

            if (braceStack.Count > 0) { line = braceStack.Peek(); expected = '}'; return false; }
            if (parenStack.Count > 0) { line = parenStack.Peek(); expected = ')'; return false; }
            if (bracketStack.Count > 0) { line = bracketStack.Peek(); expected = ']'; return false; }

            return true;
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
                        $"Script '{Path.GetFileName(relativePath)}' moved to trash successfully.",
                        new { deleted = true }
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
        /// Structured edits (AST-backed where available) on existing scripts.
        /// Supports class-level replace/delete with Roslyn span computation if USE_ROSLYN is defined,
        /// otherwise falls back to a conservative balanced-brace scan.
        /// </summary>
        private static object EditScript(
            string fullPath,
            string relativePath,
            string name,
            JArray edits,
            JObject options)
        {
            if (!File.Exists(fullPath))
                return Response.Error($"Script not found at '{relativePath}'.");
            // Refuse edits if the target is a symlink
            try
            {
                var attrs = File.GetAttributes(fullPath);
                if ((attrs & FileAttributes.ReparsePoint) != 0)
                    return Response.Error("Refusing to edit a symlinked script path.");
            }
            catch
            {
                // ignore failures checking attributes and proceed
            }
            if (edits == null || edits.Count == 0)
                return Response.Error("No edits provided.");

            string original;
            try { original = File.ReadAllText(fullPath); }
            catch (Exception ex) { return Response.Error($"Failed to read script: {ex.Message}"); }

            string working = original;

            try
            {
                var replacements = new List<(int start, int length, string text)>();
                int appliedCount = 0;

                // Apply mode: atomic (default) computes all spans against original and applies together.
                // Sequential applies each edit immediately to the current working text (useful for dependent edits).
                string applyMode = options?["applyMode"]?.ToString()?.ToLowerInvariant();
                bool applySequentially = applyMode == "sequential";

                foreach (var e in edits)
                {
                    var op = (JObject)e;
                    var mode = (op.Value<string>("mode") ?? op.Value<string>("op") ?? string.Empty).ToLowerInvariant();

                    switch (mode)
                    {
                        case "replace_class":
                        {
                            string className = op.Value<string>("className");
                            string ns = op.Value<string>("namespace");
                            string replacement = ExtractReplacement(op);

                            if (string.IsNullOrWhiteSpace(className))
                                return Response.Error("replace_class requires 'className'.");
                            if (replacement == null)
                                return Response.Error("replace_class requires 'replacement' (inline or base64).");

                            if (!TryComputeClassSpan(working, className, ns, out var spanStart, out var spanLength, out var why))
                                return Response.Error($"replace_class failed: {why}");

                            if (!ValidateClassSnippet(replacement, className, out var vErr))
                                return Response.Error($"Replacement snippet invalid: {vErr}");

                            if (applySequentially)
                            {
                                working = working.Remove(spanStart, spanLength).Insert(spanStart, NormalizeNewlines(replacement));
                                appliedCount++;
                            }
                            else
                            {
                                replacements.Add((spanStart, spanLength, NormalizeNewlines(replacement)));
                            }
                            break;
                        }

                        case "delete_class":
                        {
                            string className = op.Value<string>("className");
                            string ns = op.Value<string>("namespace");
                            if (string.IsNullOrWhiteSpace(className))
                                return Response.Error("delete_class requires 'className'.");

                            if (!TryComputeClassSpan(working, className, ns, out var s, out var l, out var why))
                                return Response.Error($"delete_class failed: {why}");

                            if (applySequentially)
                            {
                                working = working.Remove(s, l);
                                appliedCount++;
                            }
                            else
                            {
                                replacements.Add((s, l, string.Empty));
                            }
                            break;
                        }

                        case "replace_method":
                        {
                            string className = op.Value<string>("className");
                            string ns = op.Value<string>("namespace");
                            string methodName = op.Value<string>("methodName");
                            string replacement = ExtractReplacement(op);
                            string returnType = op.Value<string>("returnType");
                            string parametersSignature = op.Value<string>("parametersSignature");
                            string attributesContains = op.Value<string>("attributesContains");

                            if (string.IsNullOrWhiteSpace(className)) return Response.Error("replace_method requires 'className'.");
                            if (string.IsNullOrWhiteSpace(methodName)) return Response.Error("replace_method requires 'methodName'.");
                            if (replacement == null) return Response.Error("replace_method requires 'replacement' (inline or base64).");

                            if (!TryComputeClassSpan(working, className, ns, out var clsStart, out var clsLen, out var whyClass))
                                return Response.Error($"replace_method failed to locate class: {whyClass}");

                            if (!TryComputeMethodSpan(working, clsStart, clsLen, methodName, returnType, parametersSignature, attributesContains, out var mStart, out var mLen, out var whyMethod))
                            {
                                bool hasDependentInsert = edits.Any(j => j is JObject jo &&
                                    string.Equals(jo.Value<string>("className"), className, StringComparison.Ordinal) &&
                                    string.Equals(jo.Value<string>("methodName"), methodName, StringComparison.Ordinal) &&
                                    ((jo.Value<string>("mode") ?? jo.Value<string>("op") ?? string.Empty).ToLowerInvariant() == "insert_method"));
                                string hint = hasDependentInsert && !applySequentially ? " Hint: This batch inserts this method. Use options.applyMode='sequential' or split into separate calls." : string.Empty;
                                return Response.Error($"replace_method failed: {whyMethod}.{hint}");
                            }

                            if (applySequentially)
                            {
                                working = working.Remove(mStart, mLen).Insert(mStart, NormalizeNewlines(replacement));
                                appliedCount++;
                            }
                            else
                            {
                                replacements.Add((mStart, mLen, NormalizeNewlines(replacement)));
                            }
                            break;
                        }

                        case "delete_method":
                        {
                            string className = op.Value<string>("className");
                            string ns = op.Value<string>("namespace");
                            string methodName = op.Value<string>("methodName");
                            string returnType = op.Value<string>("returnType");
                            string parametersSignature = op.Value<string>("parametersSignature");
                            string attributesContains = op.Value<string>("attributesContains");

                            if (string.IsNullOrWhiteSpace(className)) return Response.Error("delete_method requires 'className'.");
                            if (string.IsNullOrWhiteSpace(methodName)) return Response.Error("delete_method requires 'methodName'.");

                            if (!TryComputeClassSpan(working, className, ns, out var clsStart, out var clsLen, out var whyClass))
                                return Response.Error($"delete_method failed to locate class: {whyClass}");

                            if (!TryComputeMethodSpan(working, clsStart, clsLen, methodName, returnType, parametersSignature, attributesContains, out var mStart, out var mLen, out var whyMethod))
                            {
                                bool hasDependentInsert = edits.Any(j => j is JObject jo &&
                                    string.Equals(jo.Value<string>("className"), className, StringComparison.Ordinal) &&
                                    string.Equals(jo.Value<string>("methodName"), methodName, StringComparison.Ordinal) &&
                                    ((jo.Value<string>("mode") ?? jo.Value<string>("op") ?? string.Empty).ToLowerInvariant() == "insert_method"));
                                string hint = hasDependentInsert && !applySequentially ? " Hint: This batch inserts this method. Use options.applyMode='sequential' or split into separate calls." : string.Empty;
                                return Response.Error($"delete_method failed: {whyMethod}.{hint}");
                            }

                            if (applySequentially)
                            {
                                working = working.Remove(mStart, mLen);
                                appliedCount++;
                            }
                            else
                            {
                                replacements.Add((mStart, mLen, string.Empty));
                            }
                            break;
                        }

                        case "insert_method":
                        {
                            string className = op.Value<string>("className");
                            string ns = op.Value<string>("namespace");
                            string position = (op.Value<string>("position") ?? "end").ToLowerInvariant();
                            string afterMethodName = op.Value<string>("afterMethodName");
                            string afterReturnType = op.Value<string>("afterReturnType");
                            string afterParameters = op.Value<string>("afterParametersSignature");
                            string afterAttributesContains = op.Value<string>("afterAttributesContains");
                            string snippet = ExtractReplacement(op);

                            if (string.IsNullOrWhiteSpace(className)) return Response.Error("insert_method requires 'className'.");
                            if (snippet == null) return Response.Error("insert_method requires 'replacement' (inline or base64) containing a full method declaration.");

                            if (!TryComputeClassSpan(working, className, ns, out var clsStart, out var clsLen, out var whyClass))
                                return Response.Error($"insert_method failed to locate class: {whyClass}");

                            if (position == "after")
                            {
                                if (string.IsNullOrEmpty(afterMethodName)) return Response.Error("insert_method with position='after' requires 'afterMethodName'.");
                                if (!TryComputeMethodSpan(working, clsStart, clsLen, afterMethodName, afterReturnType, afterParameters, afterAttributesContains, out var aStart, out var aLen, out var whyAfter))
                                    return Response.Error($"insert_method(after) failed to locate anchor method: {whyAfter}");
                                int insAt = aStart + aLen;
                                string text = NormalizeNewlines("\n\n" + snippet.TrimEnd() + "\n");
                                if (applySequentially)
                                {
                                    working = working.Insert(insAt, text);
                                    appliedCount++;
                                }
                                else
                                {
                                    replacements.Add((insAt, 0, text));
                                }
                            }
                            else if (!TryFindClassInsertionPoint(working, clsStart, clsLen, position, out var insAt, out var whyIns))
                                return Response.Error($"insert_method failed: {whyIns}");
                            else
                            {
                                string text = NormalizeNewlines("\n\n" + snippet.TrimEnd() + "\n");
                                if (applySequentially)
                                {
                                    working = working.Insert(insAt, text);
                                    appliedCount++;
                                }
                                else
                                {
                                    replacements.Add((insAt, 0, text));
                                }
                            }
                            break;
                        }

                        default:
                            return Response.Error($"Unknown edit mode: '{mode}'. Allowed: replace_class, delete_class, replace_method, delete_method, insert_method.");
                    }
                }

                if (!applySequentially)
                {
                    if (HasOverlaps(replacements))
                        return Response.Error("Edits overlap; split into separate calls or adjust targets.");

                    foreach (var r in replacements.OrderByDescending(r => r.start))
                        working = working.Remove(r.start, r.length).Insert(r.start, r.text);
                    appliedCount = replacements.Count;
                }

                // Validate result using override from options if provided; otherwise GUI strictness
                var level = GetValidationLevelFromGUI();
                try
                {
                    var validateOpt = options?["validate"]?.ToString()?.ToLowerInvariant();
                    if (!string.IsNullOrEmpty(validateOpt))
                    {
                        level = validateOpt switch
                        {
                            "basic" => ValidationLevel.Basic,
                            "standard" => ValidationLevel.Standard,
                            "comprehensive" => ValidationLevel.Comprehensive,
                            "strict" => ValidationLevel.Strict,
                            _ => level
                        };
                    }
                }
                catch { /* ignore option parsing issues */ }
                if (!ValidateScriptSyntax(working, level, out var errors))
                    return Response.Error("Script validation failed:\n" + string.Join("\n", errors ?? Array.Empty<string>()));
                else if (errors != null && errors.Length > 0)
                    Debug.LogWarning($"Script validation warnings for {name}:\n" + string.Join("\n", errors));

                // Atomic write with backup; schedule refresh
                var enc = System.Text.Encoding.UTF8;
                var tmp = fullPath + ".tmp";
                File.WriteAllText(tmp, working, enc);
                string backup = fullPath + ".bak";
                try
                {
                    File.Replace(tmp, fullPath, backup);
                    try { if (File.Exists(backup)) File.Delete(backup); } catch { /* ignore */ }
                }
                catch (PlatformNotSupportedException)
                {
                    File.Copy(tmp, fullPath, true);
                    try { File.Delete(tmp); } catch { }
                    try { if (File.Exists(backup)) File.Delete(backup); } catch { }
                }
                catch (IOException)
                {
                    File.Copy(tmp, fullPath, true);
                    try { File.Delete(tmp); } catch { }
                    try { if (File.Exists(backup)) File.Delete(backup); } catch { }
                }

                // Decide refresh behavior
                string refreshMode = options?["refresh"]?.ToString()?.ToLowerInvariant();
                bool immediate = refreshMode == "immediate" || refreshMode == "sync";

                var ok = Response.Success(
                    $"Applied {appliedCount} structured edit(s) to '{relativePath}'.",
                    new { path = relativePath, editsApplied = appliedCount, scheduledRefresh = !immediate }
                );

                if (immediate)
                {
                    // Force on main thread
                    EditorApplication.delayCall += () =>
                    {
                        AssetDatabase.ImportAsset(
                            relativePath,
                            ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate
                        );
#if UNITY_EDITOR
                        UnityEditor.Compilation.CompilationPipeline.RequestScriptCompilation();
#endif
                    };
                }
                else
                {
                    ManageScriptRefreshHelpers.ScheduleScriptRefresh(relativePath);
                }
                return ok;
            }
            catch (Exception ex)
            {
                return Response.Error($"Edit failed: {ex.Message}");
            }
        }

        private static bool HasOverlaps(IEnumerable<(int start, int length, string text)> list)
        {
            var arr = list.OrderBy(x => x.start).ToArray();
            for (int i = 1; i < arr.Length; i++)
            {
                if (arr[i - 1].start + arr[i - 1].length > arr[i].start)
                    return true;
            }
            return false;
        }

        private static string ExtractReplacement(JObject op)
        {
            var inline = op.Value<string>("replacement");
            if (!string.IsNullOrEmpty(inline)) return inline;

            var b64 = op.Value<string>("replacementBase64");
            if (!string.IsNullOrEmpty(b64))
            {
                try { return System.Text.Encoding.UTF8.GetString(Convert.FromBase64String(b64)); }
                catch { return null; }
            }
            return null;
        }

        private static string NormalizeNewlines(string t)
        {
            if (string.IsNullOrEmpty(t)) return t;
            return t.Replace("\r\n", "\n").Replace("\r", "\n");
        }

        private static bool ValidateClassSnippet(string snippet, string expectedName, out string err)
        {
#if USE_ROSLYN
            try
            {
                var tree = CSharpSyntaxTree.ParseText(snippet);
                var root = tree.GetRoot();
                var classes = root.DescendantNodes().OfType<Microsoft.CodeAnalysis.CSharp.Syntax.ClassDeclarationSyntax>().ToList();
                if (classes.Count != 1) { err = "snippet must contain exactly one class declaration"; return false; }
                // Optional: enforce expected name
                // if (classes[0].Identifier.ValueText != expectedName) { err = $"snippet declares '{classes[0].Identifier.ValueText}', expected '{expectedName}'"; return false; }
                err = null; return true;
            }
            catch (Exception ex) { err = ex.Message; return false; }
#else
            if (string.IsNullOrWhiteSpace(snippet) || !snippet.Contains("class ")) { err = "no 'class' keyword found in snippet"; return false; }
            err = null; return true;
#endif
        }

        private static bool TryComputeClassSpan(string source, string className, string ns, out int start, out int length, out string why)
        {
#if USE_ROSLYN
            try
            {
                var tree = CSharpSyntaxTree.ParseText(source);
                var root = tree.GetRoot();
                var classes = root.DescendantNodes()
                    .OfType<Microsoft.CodeAnalysis.CSharp.Syntax.ClassDeclarationSyntax>()
                    .Where(c => c.Identifier.ValueText == className);

                if (!string.IsNullOrEmpty(ns))
                {
                    classes = classes.Where(c =>
                        (c.FirstAncestorOrSelf<Microsoft.CodeAnalysis.CSharp.Syntax.NamespaceDeclarationSyntax>()?.Name?.ToString() ?? "") == ns
                        || (c.FirstAncestorOrSelf<Microsoft.CodeAnalysis.CSharp.Syntax.FileScopedNamespaceDeclarationSyntax>()?.Name?.ToString() ?? "") == ns);
                }

                var list = classes.ToList();
                if (list.Count == 0) { start = length = 0; why = $"class '{className}' not found" + (ns != null ? $" in namespace '{ns}'" : ""); return false; }
                if (list.Count > 1) { start = length = 0; why = $"class '{className}' matched {list.Count} declarations (partial/nested?). Disambiguate."; return false; }

                var cls = list[0];
                var span = cls.FullSpan; // includes attributes & leading trivia
                start = span.Start; length = span.Length; why = null; return true;
            }
            catch
            {
                // fall back below
            }
#endif
            return TryComputeClassSpanBalanced(source, className, ns, out start, out length, out why);
        }

        private static bool TryComputeClassSpanBalanced(string source, string className, string ns, out int start, out int length, out string why)
        {
            start = length = 0; why = null;
            var idx = IndexOfClassToken(source, className);
            if (idx < 0) { why = $"class '{className}' not found (balanced scan)"; return false; }

            if (!string.IsNullOrEmpty(ns) && !AppearsWithinNamespaceHeader(source, idx, ns))
            { why = $"class '{className}' not under namespace '{ns}' (balanced scan)"; return false; }

            // Include modifiers/attributes on the same line: back up to the start of line
            int lineStart = idx;
            while (lineStart > 0 && source[lineStart - 1] != '\n' && source[lineStart - 1] != '\r') lineStart--;

            int i = idx;
            while (i < source.Length && source[i] != '{') i++;
            if (i >= source.Length) { why = "no opening brace after class header"; return false; }

            int depth = 0; bool inStr = false, inChar = false, inSL = false, inML = false, esc = false;
            int startSpan = lineStart;
            for (; i < source.Length; i++)
            {
                char c = source[i];
                char n = i + 1 < source.Length ? source[i + 1] : '\0';

                if (inSL) { if (c == '\n') inSL = false; continue; }
                if (inML) { if (c == '*' && n == '/') { inML = false; i++; } continue; }
                if (inStr) { if (!esc && c == '"') inStr = false; esc = (!esc && c == '\\'); continue; }
                if (inChar) { if (!esc && c == '\'') inChar = false; esc = (!esc && c == '\\'); continue; }

                if (c == '/' && n == '/') { inSL = true; i++; continue; }
                if (c == '/' && n == '*') { inML = true; i++; continue; }
                if (c == '"') { inStr = true; continue; }
                if (c == '\'') { inChar = true; continue; }

                if (c == '{') { depth++; }
                else if (c == '}')
                {
                    depth--;
                    if (depth == 0) { start = startSpan; length = (i - startSpan) + 1; return true; }
                    if (depth < 0) { why = "brace underflow"; return false; }
                }
            }
            why = "unterminated class block"; return false;
        }

        private static bool TryComputeMethodSpan(
            string source,
            int classStart,
            int classLength,
            string methodName,
            string returnType,
            string parametersSignature,
            string attributesContains,
            out int start,
            out int length,
            out string why)
        {
            start = length = 0; why = null;
            int searchStart = classStart;
            int searchEnd = Math.Min(source.Length, classStart + classLength);

            // 1) Find the method header using a stricter regex (allows optional attributes above)
            string rtPattern = string.IsNullOrEmpty(returnType) ? @"[^\s]+" : Regex.Escape(returnType).Replace("\\ ", "\\s+");
            string namePattern = Regex.Escape(methodName);
            string paramsPattern = string.IsNullOrEmpty(parametersSignature) ? @"[\s\S]*?" : Regex.Escape(parametersSignature);
            string pattern =
                @"(?m)^[\t ]*(?:\[[^\]]+\][\t ]*)*[\t ]*" +
                @"(?:(?:public|private|protected|internal|static|virtual|override|sealed|async|extern|unsafe|new|partial|readonly|volatile|event|abstract|ref|in|out)\s+)*" +
                rtPattern + @"[\t ]+" + namePattern + @"\s*(?:<[^>]+>)?\s*\(" + paramsPattern + @"\)";

            string slice = source.Substring(searchStart, searchEnd - searchStart);
            var headerMatch = Regex.Match(slice, pattern, RegexOptions.Multiline);
            if (!headerMatch.Success)
            {
                why = $"method '{methodName}' header not found in class"; return false;
            }
            int headerIndex = searchStart + headerMatch.Index;

            // Optional attributes filter: look upward from headerIndex for contiguous attribute lines
            if (!string.IsNullOrEmpty(attributesContains))
            {
                int attrScanStart = headerIndex;
                while (attrScanStart > searchStart)
                {
                    int prevNl = source.LastIndexOf('\n', attrScanStart - 1);
                    if (prevNl < 0 || prevNl < searchStart) break;
                    string prevLine = source.Substring(prevNl + 1, attrScanStart - (prevNl + 1));
                    if (prevLine.TrimStart().StartsWith("[")) { attrScanStart = prevNl; continue; }
                    break;
                }
                string attrBlock = source.Substring(attrScanStart, headerIndex - attrScanStart);
                if (attrBlock.IndexOf(attributesContains, StringComparison.Ordinal) < 0)
                {
                    why = $"method '{methodName}' found but attributes filter did not match"; return false;
                }
            }

            // backtrack to the very start of header/attributes to include in span
            int lineStart = headerIndex;
            while (lineStart > searchStart && source[lineStart - 1] != '\n' && source[lineStart - 1] != '\r') lineStart--;
            // If previous lines are attributes, include them
            int attrStart = lineStart;
            int probe = lineStart - 1;
            while (probe > searchStart)
            {
                int prevNl = source.LastIndexOf('\n', probe);
                if (prevNl < 0 || prevNl < searchStart) break;
                string prev = source.Substring(prevNl + 1, attrStart - (prevNl + 1));
                if (prev.TrimStart().StartsWith("[")) { attrStart = prevNl + 1; probe = prevNl - 1; }
                else break;
            }

            // 2) Walk from the end of signature to detect body style ('{' or '=> ...;') and compute end
            // Find the '(' that belongs to the method signature, not attributes
            int nameTokenIdx = IndexOfTokenWithin(source, methodName, headerIndex, searchEnd);
            if (nameTokenIdx < 0) { why = $"method '{methodName}' token not found after header"; return false; }
            int sigOpenParen = IndexOfTokenWithin(source, "(", nameTokenIdx, searchEnd);
            if (sigOpenParen < 0) { why = "method parameter list '(' not found"; return false; }

            int i = sigOpenParen;
            int parenDepth = 0; bool inStr = false, inChar = false, inSL = false, inML = false, esc = false;
            for (; i < searchEnd; i++)
            {
                char c = source[i];
                char n = i + 1 < searchEnd ? source[i + 1] : '\0';
                if (inSL) { if (c == '\n') inSL = false; continue; }
                if (inML) { if (c == '*' && n == '/') { inML = false; i++; } continue; }
                if (inStr) { if (!esc && c == '"') inStr = false; esc = (!esc && c == '\\'); continue; }
                if (inChar) { if (!esc && c == '\'') inChar = false; esc = (!esc && c == '\\'); continue; }

                if (c == '/' && n == '/') { inSL = true; i++; continue; }
                if (c == '/' && n == '*') { inML = true; i++; continue; }
                if (c == '"') { inStr = true; continue; }
                if (c == '\'') { inChar = true; continue; }

                if (c == '(') parenDepth++;
                if (c == ')') { parenDepth--; if (parenDepth == 0) { i++; break; } }
            }

            // After params: detect expression-bodied or block-bodied
            // Skip whitespace/comments
            for (; i < searchEnd; i++)
            {
                char c = source[i];
                char n = i + 1 < searchEnd ? source[i + 1] : '\0';
                if (char.IsWhiteSpace(c)) continue;
                if (c == '/' && n == '/') { while (i < searchEnd && source[i] != '\n') i++; continue; }
                if (c == '/' && n == '*') { i += 2; while (i + 1 < searchEnd && !(source[i] == '*' && source[i + 1] == '/')) i++; i++; continue; }
                break;
            }

            // Tolerate generic constraints between params and body: multiple 'where T : ...'
            for (;;)
            {
                // Skip whitespace/comments before checking for 'where'
                for (; i < searchEnd; i++)
                {
                    char c = source[i];
                    char n = i + 1 < searchEnd ? source[i + 1] : '\0';
                    if (char.IsWhiteSpace(c)) continue;
                    if (c == '/' && n == '/') { while (i < searchEnd && source[i] != '\n') i++; continue; }
                    if (c == '/' && n == '*') { i += 2; while (i + 1 < searchEnd && !(source[i] == '*' && source[i + 1] == '/')) i++; i++; continue; }
                    break;
                }

                // Check word-boundary 'where'
                bool hasWhere = false;
                if (i + 5 <= searchEnd)
                {
                    hasWhere = source[i] == 'w' && source[i + 1] == 'h' && source[i + 2] == 'e' && source[i + 3] == 'r' && source[i + 4] == 'e';
                    if (hasWhere)
                    {
                        // Left boundary
                        if (i - 1 >= 0)
                        {
                            char lb = source[i - 1];
                            if (char.IsLetterOrDigit(lb) || lb == '_') hasWhere = false;
                        }
                        // Right boundary
                        if (hasWhere && i + 5 < searchEnd)
                        {
                            char rb = source[i + 5];
                            if (char.IsLetterOrDigit(rb) || rb == '_') hasWhere = false;
                        }
                    }
                }
                if (!hasWhere) break;

                // Advance past the entire where-constraint clause until we hit '{' or '=>' or ';'
                i += 5; // past 'where'
                while (i < searchEnd)
                {
                    char c = source[i];
                    char n = i + 1 < searchEnd ? source[i + 1] : '\0';
                    if (c == '{' || c == ';' || (c == '=' && n == '>')) break;
                    // Skip comments inline
                    if (c == '/' && n == '/') { while (i < searchEnd && source[i] != '\n') i++; continue; }
                    if (c == '/' && n == '*') { i += 2; while (i + 1 < searchEnd && !(source[i] == '*' && source[i + 1] == '/')) i++; i++; continue; }
                    i++;
                }
            }

            // Re-check for expression-bodied after constraints
            if (i < searchEnd - 1 && source[i] == '=' && source[i + 1] == '>')
            {
                // expression-bodied method: seek to terminating semicolon
                int j = i;
                bool done = false;
                while (j < searchEnd)
                {
                    char c = source[j];
                    if (c == ';') { done = true; break; }
                    j++;
                }
                if (!done) { why = "unterminated expression-bodied method"; return false; }
                start = attrStart; length = (j - attrStart) + 1; return true;
            }

            if (i >= searchEnd || source[i] != '{') { why = "no opening brace after method signature"; return false; }

            int depth = 0; inStr = false; inChar = false; inSL = false; inML = false; esc = false;
            int startSpan = attrStart;
            for (; i < searchEnd; i++)
            {
                char c = source[i];
                char n = i + 1 < searchEnd ? source[i + 1] : '\0';
                if (inSL) { if (c == '\n') inSL = false; continue; }
                if (inML) { if (c == '*' && n == '/') { inML = false; i++; } continue; }
                if (inStr) { if (!esc && c == '"') inStr = false; esc = (!esc && c == '\\'); continue; }
                if (inChar) { if (!esc && c == '\'') inChar = false; esc = (!esc && c == '\\'); continue; }

                if (c == '/' && n == '/') { inSL = true; i++; continue; }
                if (c == '/' && n == '*') { inML = true; i++; continue; }
                if (c == '"') { inStr = true; continue; }
                if (c == '\'') { inChar = true; continue; }

                if (c == '{') depth++;
                else if (c == '}')
                {
                    depth--;
                    if (depth == 0) { start = startSpan; length = (i - startSpan) + 1; return true; }
                    if (depth < 0) { why = "brace underflow in method"; return false; }
                }
            }
            why = "unterminated method block"; return false;
        }

        private static int IndexOfTokenWithin(string s, string token, int start, int end)
        {
            int idx = s.IndexOf(token, start, StringComparison.Ordinal);
            return (idx >= 0 && idx < end) ? idx : -1;
        }

        private static bool TryFindClassInsertionPoint(string source, int classStart, int classLength, string position, out int insertAt, out string why)
        {
            insertAt = 0; why = null;
            int searchStart = classStart;
            int searchEnd = Math.Min(source.Length, classStart + classLength);

            if (position == "start")
            {
                // find first '{' after class header, insert just after with a newline
                int i = IndexOfTokenWithin(source, "{", searchStart, searchEnd);
                if (i < 0) { why = "could not find class opening brace"; return false; }
                insertAt = i + 1; return true;
            }
            else // end
            {
                // walk to matching closing brace of class and insert just before it
                int i = IndexOfTokenWithin(source, "{", searchStart, searchEnd);
                if (i < 0) { why = "could not find class opening brace"; return false; }
                int depth = 0; bool inStr = false, inChar = false, inSL = false, inML = false, esc = false;
                for (; i < searchEnd; i++)
                {
                    char c = source[i];
                    char n = i + 1 < searchEnd ? source[i + 1] : '\0';
                    if (inSL) { if (c == '\n') inSL = false; continue; }
                    if (inML) { if (c == '*' && n == '/') { inML = false; i++; } continue; }
                    if (inStr) { if (!esc && c == '"') inStr = false; esc = (!esc && c == '\\'); continue; }
                    if (inChar) { if (!esc && c == '\'') inChar = false; esc = (!esc && c == '\\'); continue; }

                    if (c == '/' && n == '/') { inSL = true; i++; continue; }
                    if (c == '/' && n == '*') { inML = true; i++; continue; }
                    if (c == '"') { inStr = true; continue; }
                    if (c == '\'') { inChar = true; continue; }

                    if (c == '{') depth++;
                    else if (c == '}')
                    {
                        depth--;
                        if (depth == 0) { insertAt = i; return true; }
                        if (depth < 0) { why = "brace underflow while scanning class"; return false; }
                    }
                }
                why = "could not find class closing brace"; return false;
            }
        }

        private static int IndexOfClassToken(string s, string className)
        {
            // simple token search; could be tightened with Regex for word boundaries
            var pattern = "class " + className;
            return s.IndexOf(pattern, StringComparison.Ordinal);
        }

        private static bool AppearsWithinNamespaceHeader(string s, int pos, string ns)
        {
            int from = Math.Max(0, pos - 2000);
            var slice = s.Substring(from, pos - from);
            return slice.Contains("namespace " + ns);
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
            string savedLevel = EditorPrefs.GetString("UnityMCP_ScriptValidationLevel", "standard");
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
            // Advanced Roslyn-based validation: only run for Standard+; fail on Roslyn errors
            if (level >= ValidationLevel.Standard)
            {
                if (!ValidateScriptSyntaxRoslyn(contents, level, errorList))
                {
                    errors = errorList.ToArray();
                    return false;
                }
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

// Debounced refresh/compile scheduler to coalesce bursts of edits
static class RefreshDebounce
{
    private static int _pending;
    private static readonly object _lock = new object();
    private static readonly HashSet<string> _paths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    // The timestamp of the most recent schedule request.
    private static DateTime _lastRequest;

    // Guard to ensure we only have a single ticking callback running.
    private static bool _scheduled;

    public static void Schedule(string relPath, TimeSpan window)
    {
        // Record that work is pending and track the path in a threadsafe way.
        Interlocked.Exchange(ref _pending, 1);
        lock (_lock)
        {
            _paths.Add(relPath);
            _lastRequest = DateTime.UtcNow;

            // If a debounce timer is already scheduled it will pick up the new request.
            if (_scheduled)
                return;

            _scheduled = true;
        }

        // Kick off a ticking callback that waits until the window has elapsed
        // from the last request before performing the refresh.
        EditorApplication.delayCall += () => Tick(window);
    }

    private static void Tick(TimeSpan window)
    {
        bool ready;
        lock (_lock)
        {
            // Only proceed once the debounce window has fully elapsed.
            ready = (DateTime.UtcNow - _lastRequest) >= window;
            if (ready)
            {
                _scheduled = false;
            }
        }

        if (!ready)
        {
            // Window has not yet elapsed; check again on the next editor tick.
            EditorApplication.delayCall += () => Tick(window);
            return;
        }

        if (Interlocked.Exchange(ref _pending, 0) == 1)
        {
            string[] toImport;
            lock (_lock) { toImport = _paths.ToArray(); _paths.Clear(); }
            foreach (var p in toImport)
                AssetDatabase.ImportAsset(p, ImportAssetOptions.ForceUpdate);
#if UNITY_EDITOR
            UnityEditor.Compilation.CompilationPipeline.RequestScriptCompilation();
#endif
            // Fallback if needed:
            // AssetDatabase.Refresh();
        }
    }
}

static class ManageScriptRefreshHelpers
{
    public static void ScheduleScriptRefresh(string relPath)
    {
        RefreshDebounce.Schedule(relPath, TimeSpan.FromMilliseconds(200));
    }
}

