# Unity MCP Bridge Custom Tool Extension Guide

## Overview

Unity MCP Bridge now supports dynamic extensions! Users can create custom MCP tools in their own Unity projects without modifying the Unity MCP Bridge source code.

## How to Create Custom Tools

### 1. Implement IUnityMcpTool Interface

Create a class that implements the `IUnityMcpTool` interface:

```csharp
using Newtonsoft.Json.Linq;
using UnityMcpBridge.Editor.Models;
using UnityMcpBridge.Editor.Helpers;

namespace YourNamespace
{
    public class MyCustomTool : IUnityMcpTool
    {
        // Unique command type identifier
        public string CommandType => "my_custom_command";
        
        // Tool description
        public string Description => "My custom MCP tool";
        
        // Main method to handle commands
        public object HandleCommand(JObject parameters)
        {
            try
            {
                // Parse parameters
                string action = parameters["action"]?.ToString();
                
                // Implement your logic
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

### 2. Automatic Discovery and Registration

Unity MCP Bridge automatically scans all assemblies at startup, discovers and registers classes that implement the `IUnityMcpTool` interface. No additional registration code needed!

### 3. Using in Python MCP Server

In your Python MCP server, you can directly call custom tools:

```python
# Call custom tool
result = await ctx.bridge.unity_editor.send_command({
    "type": "my_custom_command",
    "params": {
        "action": "hello"
    }
})
```

## Example Tools

This directory contains two complete example tools:

### 1. ProjectInfoTool

- **Command Type**: `project_info`
- **Features**: 
  - Get project summary
  - Asset statistics
  - Project settings
  - Scene information
  - Package information

**Usage Example**:
```python
# Get project summary
result = await ctx.bridge.unity_editor.send_command({
    "type": "project_info",
    "params": {"action": "summary"}
})

# Get asset statistics
result = await ctx.bridge.unity_editor.send_command({
    "type": "project_info", 
    "params": {"action": "assets"}
})
```

### 2. EditorUITool

- **Command Type**: `editor_ui`
- **Features**:
  - Window management
  - Selection operations
  - Layout control
  - Notification display
  - Dialog creation

**Usage Example**:
```python
# Get open windows
result = await ctx.bridge.unity_editor.send_command({
    "type": "editor_ui",
    "params": {"action": "get_windows"}
})

# Show notification
result = await ctx.bridge.unity_editor.send_command({
    "type": "editor_ui",
    "params": {
        "action": "show_notification",
        "message": "Hello from MCP!",
        "duration": 5.0
    }
})
```

## Best Practices

### 1. Naming Conventions

- Use descriptive command type names
- Avoid conflicts with existing tools
- Use consistent naming style

### 2. Error Handling

```csharp
public object HandleCommand(JObject parameters)
{
    try
    {
        // Your logic
        return Response.Success(result);
    }
    catch (Exception ex)
    {
        return Response.Error($"Execution failed: {ex.Message}");
    }
}
```

### 3. Parameter Validation

```csharp
public object HandleCommand(JObject parameters)
{
    string action = parameters["action"]?.ToString();
    if (string.IsNullOrEmpty(action))
    {
        return Response.Error("action parameter is required");
    }
    
    // Continue processing
}
```

### 4. Documentation

Write clear documentation for your custom tools, including:

- List of supported actions
- Parameter descriptions
- Return value format
- Usage examples

## Debugging Tips

### 1. View Registered Tools

You can check which tools have been successfully registered through Unity Console:

```
[DynamicToolRegistry] Registered tool 'project_info' from ProjectInfoTool - Get detailed Unity project information...
```

### 2. Force Reload

During development, you can force re-scan and reload tools:

```csharp
// Call from Unity Editor menu or shortcut
UnityMcpBridge.Editor.Tools.DynamicToolRegistry.ForceReload();
```

### 3. Logging

Add appropriate logging in your tools:

```csharp
Debug.Log($"[MyCustomTool] Processing action: {action}");
Debug.LogError($"[MyCustomTool] Error: {ex.Message}");
```

## Advanced Usage

### 1. Accessing Unity APIs

Your custom tools can access all Unity Editor APIs:

```csharp
// Scene operations
var scene = EditorSceneManager.GetActiveScene();

// Asset operations
var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);

// Selection operations
Selection.activeGameObject = someGameObject;

// UI operations
EditorUtility.DisplayDialog("Title", "Message", "OK");
```

### 2. Asynchronous Operations

For time-consuming operations, handle asynchronous calls properly:

```csharp
public object HandleCommand(JObject parameters)
{
    // Note: MCP calls are synchronous, but you can handle async operations internally
    
    var request = AssetDatabase.StartAssetEditing();
    // ... Batch operations
    AssetDatabase.StopAssetEditing();
    
    return Response.Success("Operation completed");
}
```

### 3. State Management

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
                return Response.Success("State set");
                
            case "get_state":
                string getKey = parameters["key"]?.ToString();
                return Response.Success(new { value = _state.GetValueOrDefault(getKey) });
        }
    }
}
```

## FAQ

### Q: My custom tool is not being registered?

A: Check the following:
1. Class correctly implements `IUnityMcpTool` interface
2. `CommandType` returns non-empty string
3. Class is public and not abstract
4. Check Unity Console for error messages

### Q: How to debug my custom tools?

A: Use the following methods:
1. Add `Debug.Log` in `HandleCommand` method
2. Use Unity's debugger
3. Check returned error messages

### Q: Can tools be added dynamically at runtime?

A: The current implementation scans once at editor startup. For dynamic addition, call `DynamicToolRegistry.ForceReload()`.

---

Now you can start creating your own custom MCP tools! Reference the example code, be creative, and extend Unity MCP Bridge's functionality.