using Newtonsoft.Json.Linq;
using NUnit.Framework;
using MCPForUnity.Editor.Helpers;
using MCPForUnity.Editor.Models;

namespace MCPForUnityTests.Editor.Windows
{
    public class ManualConfigJsonBuilderTests
    {
        [Test]
        public void VSCode_ManualJson_HasServersEnvType_NoDisabled()
        {
            var client = new McpClient { name = "VSCode", mcpType = McpTypes.VSCode };
            string json = ConfigJsonBuilder.BuildManualConfigJson("/usr/bin/uv", "/path/to/server", client);

            var root = JObject.Parse(json);
            var unity = (JObject)root.SelectToken("servers.unityMCP");
            Assert.NotNull(unity, "Expected servers.unityMCP node");
            Assert.AreEqual("/usr/bin/uv", (string)unity["command"]);
            CollectionAssert.AreEqual(new[] { "run", "--directory", "/path/to/server", "server.py" }, unity["args"].ToObject<string[]>());
            Assert.AreEqual("stdio", (string)unity["type"], "VSCode should include type=stdio");
            Assert.NotNull(unity["env"], "env should be included");
            Assert.IsNull(unity["disabled"], "disabled should not be added for VSCode");
        }

        [Test]
        public void Windsurf_ManualJson_HasMcpServersEnv_DisabledFalse()
        {
            var client = new McpClient { name = "Windsurf", mcpType = McpTypes.Windsurf };
            string json = ConfigJsonBuilder.BuildManualConfigJson("/usr/bin/uv", "/path/to/server", client);

            var root = JObject.Parse(json);
            var unity = (JObject)root.SelectToken("mcpServers.unityMCP");
            Assert.NotNull(unity, "Expected mcpServers.unityMCP node");
            Assert.NotNull(unity["env"], "env should be included");
            Assert.AreEqual(false, (bool)unity["disabled"], "disabled:false should be added for Windsurf");
            Assert.IsNull(unity["type"], "type should not be added for non-VSCode clients");
        }

        [Test]
        public void Cursor_ManualJson_HasMcpServersEnv_NoDisabled()
        {
            var client = new McpClient { name = "Cursor", mcpType = McpTypes.Cursor };
            string json = ConfigJsonBuilder.BuildManualConfigJson("/usr/bin/uv", "/path/to/server", client);

            var root = JObject.Parse(json);
            var unity = (JObject)root.SelectToken("mcpServers.unityMCP");
            Assert.NotNull(unity, "Expected mcpServers.unityMCP node");
            Assert.NotNull(unity["env"], "env should be included");
            Assert.IsNull(unity["disabled"], "disabled should not be added for Cursor");
            Assert.IsNull(unity["type"], "type should not be added for non-VSCode clients");
        }
    }
}
