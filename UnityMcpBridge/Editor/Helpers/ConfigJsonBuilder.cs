using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using MCPForUnity.Editor.Models;

namespace MCPForUnity.Editor.Helpers
{
    public static class ConfigJsonBuilder
    {
        public static string BuildManualConfigJson(string uvPath, string pythonDir, McpClient client)
        {
            var root = new JObject();
            bool isVSCode = client?.mcpType == McpTypes.VSCode;
            JObject container;
            if (isVSCode)
            {
                container = EnsureObject(root, "servers");
            }
            else
            {
                container = EnsureObject(root, "mcpServers");
            }

            var unity = new JObject
            {
                ["command"] = uvPath,
                ["args"] = JArray.FromObject(new[] { "run", "--directory", pythonDir, "server.py" })
            };

            // VSCode requires transport type
            if (isVSCode)
            {
                unity["type"] = "stdio";
            }

            // Always include env {}
            unity["env"] = new JObject();

            // Only for Windsurf/Kiro (not for VSCode client)
            if (client != null && (client.mcpType == McpTypes.Windsurf || client.mcpType == McpTypes.Kiro))
            {
                unity["disabled"] = false;
            }

            container["unityMCP"] = unity;

            return root.ToString(Formatting.Indented);
        }

        public static JObject ApplyUnityServerToExistingConfig(JObject root, string uvPath, string serverSrc, McpClient client)
        {
            if (root == null) root = new JObject();
            bool isVSCode = client?.mcpType == McpTypes.VSCode;
            JObject container = isVSCode ? EnsureObject(root, "servers") : EnsureObject(root, "mcpServers");
            JObject unity = container["unityMCP"] as JObject ?? new JObject();

            unity["command"] = uvPath;
            unity["args"] = JArray.FromObject(new[] { "run", "--directory", serverSrc, "server.py" });

            // VSCode transport type
            if (isVSCode)
            {
                unity["type"] = "stdio";
            }

            // Ensure env exists
            if (unity["env"] == null)
            {
                unity["env"] = new JObject();
            }

            // Only add disabled:false for Windsurf/Kiro
            if (client != null && (client.mcpType == McpTypes.Windsurf || client.mcpType == McpTypes.Kiro))
            {
                if (unity["disabled"] == null)
                {
                    unity["disabled"] = false;
                }
            }

            container["unityMCP"] = unity;
            return root;
        }

        private static JObject EnsureObject(JObject parent, string name)
        {
            if (parent[name] is JObject o) return o;
            var created = new JObject();
            parent[name] = created;
            return created;
        }
    }
}
