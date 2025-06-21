# Unity MCP Bridge 自定义工具扩展指南
# Unity MCP Bridge Custom Tool Extension Guide

## 概述 / Overview

Unity MCP Bridge 现在支持动态扩展功能！用户可以在自己的Unity项目中创建自定义MCP工具，而无需修改Unity MCP Bridge的源码。

Unity MCP Bridge now supports dynamic extensions! Users can create custom MCP tools in their own Unity projects without modifying the Unity MCP Bridge source code.

## 如何创建自定义工具 / How to Create Custom Tools

### 1. 实现 IUnityMcpTool 接口 / Implement IUnityMcpTool Interface

创建一个实现 `IUnityMcpTool` 接口的类：

Create a class that implements the `IUnityMcpTool` interface:

```csharp
using Newtonsoft.Json.Linq;
using UnityMcpBridge.Editor.Models;
using UnityMcpBridge.Editor.Helpers;

namespace YourNamespace
{
    public class MyCustomTool : IUnityMcpTool
    {
        // 唯一的命令类型标识符 / Unique command type identifier
        public string CommandType => "my_custom_command";
        
        // 工具描述 / Tool description
        public string Description => "我的自定义MCP工具 / My custom MCP tool";
        
        // 处理命令的主要方法 / Main method to handle commands
        public object HandleCommand(JObject parameters)
        {
            try
            {
                // 解析参数 / Parse parameters
                string action = parameters["action"]?.ToString();
                
                // 实现你的逻辑 / Implement your logic
                switch (action)
                {
                    case "hello":
                        return Response.Success(new { message = "Hello from custom tool!" });
                    
                    default:
                        return Response.Error($"Unknown action: {action}");
                }
            }
            catch (Exception ex)
            {
                return Response.Error($"Error: {ex.Message}");
            }
        }
    }
}
```

### 2. 自动发现和注册 / Automatic Discovery and Registration

Unity MCP Bridge 会在启动时自动扫描所有程序集，发现并注册实现了 `IUnityMcpTool` 接口的类。不需要额外的注册代码！

Unity MCP Bridge automatically scans all assemblies at startup, discovers and registers classes that implement the `IUnityMcpTool` interface. No additional registration code needed!

### 3. 在Python MCP Server中使用 / Using in Python MCP Server

在你的Python MCP服务器中，你可以直接调用自定义工具：

In your Python MCP server, you can directly call custom tools:

```python
# 调用自定义工具 / Call custom tool
result = await ctx.bridge.unity_editor.send_command({
    "type": "my_custom_command",
    "params": {
        "action": "hello"
    }
})
```

## 示例工具 / Example Tools

本目录包含了两个完整的示例工具：

This directory contains two complete example tools:

### 1. ProjectInfoTool 项目信息工具

- **命令类型 / Command Type**: `project_info`
- **功能 / Features**: 
  - 获取项目摘要 / Get project summary
  - 资源统计 / Asset statistics
  - 项目设置 / Project settings
  - 场景信息 / Scene information
  - 包信息 / Package information

**使用示例 / Usage Example**:
```python
# 获取项目摘要 / Get project summary
result = await ctx.bridge.unity_editor.send_command({
    "type": "project_info",
    "params": {"action": "summary"}
})

# 获取资源统计 / Get asset statistics
result = await ctx.bridge.unity_editor.send_command({
    "type": "project_info", 
    "params": {"action": "assets"}
})
```

### 2. EditorUITool 编辑器UI工具

- **命令类型 / Command Type**: `editor_ui`
- **功能 / Features**:
  - 窗口管理 / Window management
  - 选择操作 / Selection operations
  - 布局控制 / Layout control
  - 通知显示 / Notification display
  - 对话框创建 / Dialog creation

**使用示例 / Usage Example**:
```python
# 获取打开的窗口 / Get open windows
result = await ctx.bridge.unity_editor.send_command({
    "type": "editor_ui",
    "params": {"action": "get_windows"}
})

# 显示通知 / Show notification
result = await ctx.bridge.unity_editor.send_command({
    "type": "editor_ui",
    "params": {
        "action": "show_notification",
        "message": "Hello from MCP!",
        "duration": 5.0
    }
})
```

## 最佳实践 / Best Practices

### 1. 命名约定 / Naming Conventions

- 使用描述性的命令类型名称 / Use descriptive command type names
- 避免与现有工具冲突 / Avoid conflicts with existing tools
- 使用一致的命名风格 / Use consistent naming style

### 2. 错误处理 / Error Handling

```csharp
public object HandleCommand(JObject parameters)
{
    try
    {
        // 你的逻辑 / Your logic
        return Response.Success(result);
    }
    catch (Exception ex)
    {
        return Response.Error($"执行失败: {ex.Message}");
    }
}
```

### 3. 参数验证 / Parameter Validation

```csharp
public object HandleCommand(JObject parameters)
{
    string action = parameters["action"]?.ToString();
    if (string.IsNullOrEmpty(action))
    {
        return Response.Error("action 参数是必需的");
    }
    
    // 继续处理 / Continue processing
}
```

### 4. 文档化 / Documentation

为你的自定义工具编写清晰的文档，包括：
Write clear documentation for your custom tools, including:

- 支持的action列表 / List of supported actions
- 参数说明 / Parameter descriptions
- 返回值格式 / Return value format
- 使用示例 / Usage examples

## 调试技巧 / Debugging Tips

### 1. 查看已注册的工具 / View Registered Tools

你可以通过Unity控制台查看哪些工具已被成功注册：

You can check which tools have been successfully registered through Unity Console:

```
[DynamicToolRegistry] Registered tool 'project_info' from ProjectInfoTool - 获取Unity项目的详细信息...
```

### 2. 强制重新加载 / Force Reload

在开发过程中，你可以强制重新扫描和加载工具：

During development, you can force re-scan and reload tools:

```csharp
// 在Unity编辑器的菜单或快捷键中调用 / Call from Unity Editor menu or shortcut
UnityMcpBridge.Editor.Tools.DynamicToolRegistry.ForceReload();
```

### 3. 日志记录 / Logging

在你的工具中添加适当的日志记录：

Add appropriate logging in your tools:

```csharp
Debug.Log($"[MyCustomTool] Processing action: {action}");
Debug.LogError($"[MyCustomTool] Error: {ex.Message}");
```

## 高级用法 / Advanced Usage

### 1. 访问Unity API / Accessing Unity APIs

你的自定义工具可以访问所有Unity Editor API：

Your custom tools can access all Unity Editor APIs:

```csharp
// 场景操作 / Scene operations
var scene = EditorSceneManager.GetActiveScene();

// 资源操作 / Asset operations
var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);

// 选择操作 / Selection operations
Selection.activeGameObject = someGameObject;

// UI操作 / UI operations
EditorUtility.DisplayDialog("Title", "Message", "OK");
```

### 2. 异步操作 / Asynchronous Operations

对于需要时间的操作，合理处理异步调用：

For time-consuming operations, handle asynchronous calls properly:

```csharp
public object HandleCommand(JObject parameters)
{
    // 注意：MCP调用是同步的，但可以在内部处理异步操作
    // Note: MCP calls are synchronous, but you can handle async operations internally
    
    var request = AssetDatabase.StartAssetEditing();
    // ... 批量操作 / Batch operations
    AssetDatabase.StopAssetEditing();
    
    return Response.Success("操作完成");
}
```

### 3. 状态管理 / State Management

可以在工具类中维护状态信息：

You can maintain state information in tool classes:

```csharp
public class StatefulTool : IUnityMcpTool
{
    private static Dictionary<string, object> _state = new Dictionary<string, object>();
    
    public object HandleCommand(JObject parameters)
    {
        string action = parameters["action"]?.ToString();
        
        switch (action)
        {
            case "set_state":
                string key = parameters["key"]?.ToString();
                object value = parameters["value"]?.ToObject<object>();
                _state[key] = value;
                return Response.Success("状态已设置");
                
            case "get_state":
                string getKey = parameters["key"]?.ToString();
                return Response.Success(new { value = _state.GetValueOrDefault(getKey) });
        }
    }
}
```

## 常见问题 / FAQ

### Q: 我的自定义工具没有被注册？
### Q: My custom tool is not being registered?

A: 检查以下几点 / Check the following:
1. 类是否正确实现了 `IUnityMcpTool` 接口 / Class correctly implements `IUnityMcpTool` interface
2. `CommandType` 是否返回非空字符串 / `CommandType` returns non-empty string
3. 类是否为公共类且不是抽象类 / Class is public and not abstract
4. 查看Unity控制台是否有错误信息 / Check Unity Console for error messages

### Q: 如何调试我的自定义工具？
### Q: How to debug my custom tools?

A: 使用以下方法 / Use the following methods:
1. 在 `HandleCommand` 方法中添加 `Debug.Log` / Add `Debug.Log` in `HandleCommand` method
2. 使用Unity的调试器 / Use Unity's debugger
3. 检查返回的错误信息 / Check returned error messages

### Q: 可以在运行时动态添加工具吗？
### Q: Can tools be added dynamically at runtime?

A: 当前实现在编辑器启动时扫描一次。如需动态添加，可调用 `DynamicToolRegistry.ForceReload()`。

The current implementation scans once at editor startup. For dynamic addition, call `DynamicToolRegistry.ForceReload()`.

---

现在你可以开始创建自己的自定义MCP工具了！参考示例代码，发挥创意，扩展Unity MCP Bridge的功能。

Now you can start creating your own custom MCP tools! Reference the example code, be creative, and extend Unity MCP Bridge's functionality.