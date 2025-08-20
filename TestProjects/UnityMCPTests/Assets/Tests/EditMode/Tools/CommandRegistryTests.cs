using System;
using Newtonsoft.Json;
using NUnit.Framework;
using MCPForUnity.Editor.Tools;

namespace MCPForUnityTests.Editor.Tools
{
    public class CommandRegistryTests
    {
        [Test]
        public void GetHandler_ReturnsNull_ForUnknownCommand()
        {
            var unknown = "HandleDoesNotExist";
            var handler = CommandRegistry.GetHandler(unknown);
            Assert.IsNull(handler, "Expected null handler for unknown command name.");
        }

        [Test]
        public void GetHandler_ReturnsManageGameObjectHandler()
        {
            var handler = CommandRegistry.GetHandler("HandleManageGameObject");
            Assert.IsNotNull(handler, "Expected a handler for HandleManageGameObject.");

            var methodInfo = handler.Method;
            Assert.AreEqual("HandleCommand", methodInfo.Name, "Handler method name should be HandleCommand.");
            Assert.AreEqual(typeof(ManageGameObject), methodInfo.DeclaringType, "Handler should be declared on ManageGameObject.");
            Assert.IsNull(handler.Target, "Handler should be a static method (no target instance).");
        }
    }
}
