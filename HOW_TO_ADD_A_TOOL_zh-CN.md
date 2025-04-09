# Unity MCP 服务器

本目录包含 Unity MCP 服务器实现，它提供了 Python 和 Unity 编辑器功能之间的桥接。

## 添加新工具

要向 MCP 服务器添加新工具，请按照以下步骤操作：

### 1. 创建 C# Command Handler

首先，在 `Editor/Commands` 目录中创建或修改Command Handler：

```csharp
// 示例：NewCommandHandler.cs
public static class NewCommandHandler
{
    public static object HandleNewCommand(JObject @params)
    {
        // 提取参数
        string param1 = (string)@params["param1"];
        int param2 = (int)@params["param2"];

        // 实现 Unity 端上的功能
        // ...

        // 返回结果
        return new {
            message = "操作成功",
            result = someResult
        };
    }
}
```

### 2. 注册 Command Handler

将您的命令处理器添加到 `Editor/Commands` 目录中的 `CommandRegistry.cs`：

```csharp
public static class CommandRegistry
{
    private static readonly Dictionary<string, Func<JObject, object>> _handlers = new()
    {
        // ... 现有 Handlers  ...
        { "NEW_COMMAND", NewCommandHandler.HandleNewCommand }
    };
}
```

### 3. 创建 Python 工具

向 `Python/tools` 目录中的 Python 模块中添加您的工具：

```python
@mcp.tool()
def new_tool(
    ctx: Context,
    param1: str,
    param2: int
) -> str:
    """工具功能的描述。

    参数：
        ctx: MCP 上下文
        param1: param1 的描述
        param2: param2 的描述

    返回：
        str: 成功消息或错误详情
    """
    try:
        response = get_unity_connection().send_command("NEW_COMMAND", {
            "param1": param1,
            "param2": param2
        })
        return response.get("message", "操作成功")
    except Exception as e:
        return f"执行操作时出错：{str(e)}"
```

### 4. 注册工具

确保您的工具在适当的注册函数中注册：

```python
# 在 Python/tools/__init__.py 中
def register_all_tools(mcp):
    register_scene_tools(mcp)
    register_script_tools(mcp)
    register_material_tools(mcp)
    # 如果必要，在这里添加你的新工具的注册
```

### 5. 更新 Prompt

如果您的工具应该暴露给用户，请更新 `Python/server.py` 中的 Prompt：

```python
@mcp.prompt()
def asset_creation_strategy() -> str:
    return (
        "遵循以下 Unity 最佳实践：\n\n"
        "1. **您的类别**：\n"
        "   - 使用 `new_tool(param1, param2)` 来执行某些操作\n"
        # ... 提示的其余部分 ...
    )
```

## 最佳实践

1. **存在性检查**：

   - 在创建或更新对象、脚本、资源或材质之前，**始终检查**它们是否存在
   - 使用适当的搜索工具（`find_objects_by_name`、`list_scripts`、`get_asset_list`）来验证存在性
   - 处理两种情况：当不存在时创建，当存在时更新
   - 当未找到预期资源时，实现适当的错误处理

2. **错误处理**：

   - 在 Python 工具中始终包含 try-catch 块
   - 在 C# 处理器中验证参数
   - 返回有意义的错误消息

3. **文档**：

   - 为 C# 处理器添加 XML 文档
   - 在 Python 工具中包含详细的文档字符串
   - 使用清晰的使用说明更新提示信息

4. **参数验证**：

   - 在 Python 和 C# 两端验证参数
   - 使用适当的类型（str, int, float, List 等）
   - 在适当时提供默认值

5. **测试**：

   - 在 Unity 编辑器和 Python 环境中测试工具
   - 验证预期的错误处理结果
   - 检查工具与现有功能的集成

6. **代码管理**：
   - 在适当的处理器类中管理相关工具
   - 保持工具专注和单一用途
   - 遵循现有的命名约定

## 实现示例

以下是添加新工具的完整示例：

1. **C# Handler**（`Editor/Commands/ExampleHandler.cs`）：

```csharp
public static class ExampleHandler
{
    public static object CreatePrefab(JObject @params)
    {
        string prefabName = (string)@params["prefab_name"];
        string template = (string)@params["template"];
        bool overwrite = @params["overwrite"] != null ? (bool)@params["overwrite"] : false;

        // 检查预制体是否已存在
        string prefabPath = $"Assets/Prefabs/{prefabName}.prefab";
        bool prefabExists = System.IO.File.Exists(prefabPath);

        if (prefabExists && !overwrite)
        {
            return new {
                message = $"预制体已存在：{prefabName}。使用 overwrite=true 替换它。",
                exists = true,
                path = prefabPath
            };
        }

        // 实现
        GameObject prefab = new GameObject(prefabName);
        // ... 设置预制体 ...

        return new {
            message = prefabExists ? $"已更新预制体：{prefabName}" : $"已创建预制体：{prefabName}",
            exists = prefabExists,
            path = prefabPath
        };
    }
}
```

2. **Python 工具**（`Python/tools/example_tools.py`）：

```python
@mcp.tool()
def create_prefab(
    ctx: Context,
    prefab_name: str,
    template: str = "default",
    overwrite: bool = False
) -> str:
    """在项目中创建新预制体或更新现有预制体。

    参数：
        ctx: MCP 上下文
        prefab_name: 新预制体的名称
        template: 要使用的模板（默认："default"）
        overwrite: 是否覆盖现有预制体（默认：False）

    返回：
        str: 成功消息或错误详情
    """
    try:
        # 首先检查预制体是否已存在
        assets = get_unity_connection().send_command("GET_ASSET_LIST", {
            "type": "Prefab",
            "search_pattern": prefab_name,
            "folder": "Assets/Prefabs"
        }).get("assets", [])
        
        prefab_exists = any(asset.get("name") == prefab_name for asset in assets)
        
        if prefab_exists and not overwrite:
            return f"预制体 '{prefab_name}' 已存在。使用 overwrite=True 替换它。"
            
        # 创建或更新预制体
        response = get_unity_connection().send_command("CREATE_PREFAB", {
            "prefab_name": prefab_name,
            "template": template,
            "overwrite": overwrite
        })
        
        return response.get("message", "预制体操作成功完成")
    except Exception as e:
        return f"预制体操作出错：{str(e)}"
```

3. **更新提示信息**：

```python
"1. **预制体管理**：\n"
"   - 在创建预制体之前始终检查它是否存在\n"
"   - 使用 `create_prefab(prefab_name, template, overwrite=False)` 创建或更新预制体\n"
```

## 故障排除

如果您遇到问题：

1. 检查 Unity 控制台中的 C# 错误
2. 验证 Python 和 C# 之间的 command name 匹配
3. 确保所有参数都正确序列化
4. 检查 Python 日志中的连接问题
5. 验证工具在两个环境中都正确注册
