"""
Custom Tool Creation GUI - Visual interface for creating and configuring MCP tools.
Provides a web-based interface for users to create custom tools without coding.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from pathlib import Path

from enhanced_logging import enhanced_logger, LogContext
from exceptions import ValidationError, ResourceError
from advanced_logging import advanced_log_manager, LogLevel, LogCategory


class ParameterType(Enum):
    """Supported parameter types for custom tools."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    FILE_PATH = "file_path"
    UNITY_OBJECT = "unity_object"
    ENUM = "enum"


class ToolCategory(Enum):
    """Categories for organizing custom tools."""
    ASSET_MANAGEMENT = "asset_management"
    SCENE_MANAGEMENT = "scene_management"
    OBJECT_MANIPULATION = "object_manipulation"
    UTILITY = "utility"
    AUTOMATION = "automation"
    DEBUGGING = "debugging"
    CUSTOM = "custom"


@dataclass
class ParameterDefinition:
    """Definition of a tool parameter."""
    name: str
    type: ParameterType
    description: str = ""
    required: bool = True
    default_value: Any = None
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    enum_values: List[str] = field(default_factory=list)
    unity_object_type: str = None  # For UNITY_OBJECT type


@dataclass
class ToolAction:
    """Definition of a tool action/operation."""
    name: str
    description: str
    unity_command: str
    parameters: List[ParameterDefinition] = field(default_factory=list)
    return_type: str = "object"
    timeout_seconds: int = 30
    requires_unity_focus: bool = False


@dataclass
class CustomToolDefinition:
    """Complete definition of a custom tool."""
    id: str
    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    author: str = "Unknown"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    actions: List[ToolAction] = field(default_factory=list)
    global_parameters: List[ParameterDefinition] = field(default_factory=list)
    icon: str = None
    tags: List[str] = field(default_factory=list)
    enabled: bool = True
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


class CustomToolCreator:
    """Manager for creating and configuring custom MCP tools."""
    
    def __init__(self, tools_directory: str = "UnityMcpServer/custom_tools"):
        self.tools_directory = Path(tools_directory)
        self.tools_directory.mkdir(parents=True, exist_ok=True)
        
        self.custom_tools: Dict[str, CustomToolDefinition] = {}
        self.tool_templates: Dict[str, Dict[str, Any]] = {}
        
        self._load_existing_tools()
        self._load_tool_templates()
    
    def _load_existing_tools(self):
        """Load existing custom tools from disk."""
        
        for tool_file in self.tools_directory.glob("*.json"):
            try:
                with open(tool_file, 'r', encoding='utf-8') as f:
                    tool_data = json.load(f)
                
                tool_def = self._dict_to_tool_definition(tool_data)
                self.custom_tools[tool_def.id] = tool_def
                
                advanced_log_manager.log_advanced(
                    LogLevel.INFO,
                    LogCategory.SYSTEM,
                    f"Loaded custom tool: {tool_def.name}",
                    tool_id=tool_def.id,
                    tool_name=tool_def.name
                )
                
            except Exception as e:
                advanced_log_manager.log_advanced(
                    LogLevel.ERROR,
                    LogCategory.SYSTEM,
                    f"Failed to load custom tool from {tool_file}: {str(e)}",
                    error_type=type(e).__name__
                )
    
    def _load_tool_templates(self):
        """Load tool templates for quick creation."""
        
        self.tool_templates = {
            "basic_asset_tool": {
                "name": "Basic Asset Tool",
                "description": "Template for basic asset operations",
                "category": ToolCategory.ASSET_MANAGEMENT,
                "actions": [
                    {
                        "name": "process_asset",
                        "description": "Process an asset",
                        "unity_command": "ProcessAsset",
                        "parameters": [
                            {
                                "name": "asset_path",
                                "type": ParameterType.FILE_PATH,
                                "description": "Path to the asset",
                                "required": True
                            }
                        ]
                    }
                ]
            },
            "scene_utility": {
                "name": "Scene Utility Tool",
                "description": "Template for scene manipulation tools",
                "category": ToolCategory.SCENE_MANAGEMENT,
                "actions": [
                    {
                        "name": "modify_scene",
                        "description": "Modify scene objects",
                        "unity_command": "ModifyScene",
                        "parameters": [
                            {
                                "name": "scene_name",
                                "type": ParameterType.STRING,
                                "description": "Name of the scene",
                                "required": True
                            },
                            {
                                "name": "operation",
                                "type": ParameterType.ENUM,
                                "description": "Operation to perform",
                                "required": True,
                                "enum_values": ["add", "remove", "modify"]
                            }
                        ]
                    }
                ]
            },
            "automation_script": {
                "name": "Automation Script",
                "description": "Template for automation tools",
                "category": ToolCategory.AUTOMATION,
                "actions": [
                    {
                        "name": "execute_automation",
                        "description": "Execute automation sequence",
                        "unity_command": "ExecuteAutomation",
                        "parameters": [
                            {
                                "name": "steps",
                                "type": ParameterType.ARRAY,
                                "description": "Automation steps to execute",
                                "required": True
                            },
                            {
                                "name": "parallel",
                                "type": ParameterType.BOOLEAN,
                                "description": "Execute steps in parallel",
                                "required": False,
                                "default_value": False
                            }
                        ]
                    }
                ]
            }
        }
    
    def create_tool_from_template(self, template_name: str, tool_name: str, 
                                 customizations: Dict[str, Any] = None) -> str:
        """Create a new tool from a template."""
        
        if template_name not in self.tool_templates:
            raise ValidationError(f"Template '{template_name}' not found")
        
        template = self.tool_templates[template_name].copy()
        
        # Apply customizations
        if customizations:
            template.update(customizations)
        
        # Create tool definition
        tool_def = CustomToolDefinition(
            id=str(uuid.uuid4()),
            name=tool_name,
            description=template.get("description", ""),
            category=ToolCategory(template.get("category", ToolCategory.CUSTOM.value)),
            author=customizations.get("author", "Template User") if customizations else "Template User"
        )
        
        # Add actions from template
        for action_data in template.get("actions", []):
            action = ToolAction(
                name=action_data["name"],
                description=action_data["description"],
                unity_command=action_data["unity_command"],
                parameters=[
                    ParameterDefinition(
                        name=param["name"],
                        type=ParameterType(param["type"]),
                        description=param["description"],
                        required=param.get("required", True),
                        default_value=param.get("default_value"),
                        enum_values=param.get("enum_values", [])
                    )
                    for param in action_data.get("parameters", [])
                ]
            )
            tool_def.actions.append(action)
        
        # Save and register tool
        self.custom_tools[tool_def.id] = tool_def
        self._save_tool(tool_def)
        
        advanced_log_manager.log_advanced(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            f"Created custom tool from template: {tool_name}",
            tool_id=tool_def.id,
            template_name=template_name
        )
        
        return tool_def.id
    
    def create_custom_tool(self, tool_data: Dict[str, Any]) -> str:
        """Create a completely custom tool."""
        
        # Validate tool data
        self._validate_tool_data(tool_data)
        
        # Create tool definition
        tool_def = self._dict_to_tool_definition(tool_data)
        
        # Save and register tool
        self.custom_tools[tool_def.id] = tool_def
        self._save_tool(tool_def)
        
        advanced_log_manager.log_advanced(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            f"Created custom tool: {tool_def.name}",
            tool_id=tool_def.id
        )
        
        return tool_def.id
    
    def update_tool(self, tool_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing custom tool."""
        
        if tool_id not in self.custom_tools:
            raise ValidationError(f"Tool with ID '{tool_id}' not found")
        
        tool_def = self.custom_tools[tool_id]
        
        # Apply updates
        if "name" in updates:
            tool_def.name = updates["name"]
        if "description" in updates:
            tool_def.description = updates["description"]
        if "category" in updates:
            tool_def.category = ToolCategory(updates["category"])
        if "enabled" in updates:
            tool_def.enabled = updates["enabled"]
        if "tags" in updates:
            tool_def.tags = updates["tags"]
        
        tool_def.updated_at = time.time()
        
        # Save changes
        self._save_tool(tool_def)
        
        advanced_log_manager.log_advanced(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            f"Updated custom tool: {tool_def.name}",
            tool_id=tool_id
        )
        
        return True
    
    def delete_tool(self, tool_id: str) -> bool:
        """Delete a custom tool."""
        
        if tool_id not in self.custom_tools:
            raise ValidationError(f"Tool with ID '{tool_id}' not found")
        
        tool_def = self.custom_tools[tool_id]
        
        # Remove from memory
        del self.custom_tools[tool_id]
        
        # Remove file
        tool_file = self.tools_directory / f"{tool_id}.json"
        if tool_file.exists():
            tool_file.unlink()
        
        advanced_log_manager.log_advanced(
            LogLevel.INFO,
            LogCategory.SYSTEM,
            f"Deleted custom tool: {tool_def.name}",
            tool_id=tool_id
        )
        
        return True
    
    def get_tool(self, tool_id: str) -> Optional[CustomToolDefinition]:
        """Get a custom tool by ID."""
        return self.custom_tools.get(tool_id)
    
    def list_tools(self, category: ToolCategory = None, enabled_only: bool = True) -> List[CustomToolDefinition]:
        """List custom tools with optional filtering."""
        
        tools = list(self.custom_tools.values())
        
        if category:
            tools = [tool for tool in tools if tool.category == category]
        
        if enabled_only:
            tools = [tool for tool in tools if tool.enabled]
        
        return sorted(tools, key=lambda t: t.name)
    
    def get_tool_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available tool templates."""
        return self.tool_templates.copy()
    
    def validate_tool_configuration(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool configuration and return validation results."""
        
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            self._validate_tool_data(tool_data)
        except ValidationError as e:
            validation_results["valid"] = False
            validation_results["errors"].append(str(e))
        
        # Additional warnings
        if not tool_data.get("description"):
            validation_results["warnings"].append("Tool description is empty")
        
        if not tool_data.get("actions"):
            validation_results["warnings"].append("Tool has no actions defined")
        
        return validation_results
    
    def generate_tool_code(self, tool_id: str) -> str:
        """Generate Python code for a custom tool."""
        
        tool_def = self.get_tool(tool_id)
        if not tool_def:
            raise ValidationError(f"Tool with ID '{tool_id}' not found")
        
        # Generate Python code
        code_lines = [
            f'"""',
            f'Custom MCP Tool: {tool_def.name}',
            f'Description: {tool_def.description}',
            f'Generated automatically by Custom Tool Creator',
            f'"""',
            '',
            'from mcp import FastMCP',
            'from enhanced_logging import enhanced_logger, LogContext',
            'from exceptions import ValidationError, UnityOperationError',
            'from enhanced_connection import get_enhanced_unity_connection',
            '',
            f'def register_{tool_def.name.lower().replace(" ", "_")}_tools(mcp: FastMCP):',
            f'    """Register {tool_def.name} tools with the MCP server."""',
            ''
        ]
        
        # Generate each action
        for action in tool_def.actions:
            code_lines.extend(self._generate_action_code(tool_def, action))
            code_lines.append('')
        
        return '\n'.join(code_lines)
    
    def _generate_action_code(self, tool_def: CustomToolDefinition, action: ToolAction) -> List[str]:
        """Generate code for a single action."""
        
        func_name = f"{tool_def.name.lower().replace(' ', '_')}_{action.name}"
        
        # Build parameter list
        params = ['ctx: Context']
        for param in action.parameters:
            param_type = self._get_python_type(param.type)
            if not param.required:
                params.append(f'{param.name}: {param_type} = None')
            else:
                params.append(f'{param.name}: {param_type}')
        
        code_lines = [
            f'    @mcp.tool()',
            f'    def {func_name}({", ".join(params)}):',
            f'        """',
            f'        {action.description}',
            f'        """',
            f'        try:',
            f'            # Validate parameters',
            f'            # TODO: Add parameter validation',
            f'            ',
            f'            # Get Unity connection',
            f'            connection = get_enhanced_unity_connection()',
            f'            ',
            f'            # Execute Unity command',
            f'            command = {{',
            f'                "type": "{action.unity_command}",',
        ]
        
        # Add parameters to command
        for param in action.parameters:
            code_lines.append(f'                "{param.name}": {param.name},')
        
        code_lines.extend([
            f'            }}',
            f'            ',
            f'            result = connection.send_command(command)',
            f'            ',
            f'            return {{',
            f'                "success": True,',
            f'                "message": "{action.description} completed successfully",',
            f'                "data": result',
            f'            }}',
            f'            ',
            f'        except Exception as e:',
            f'            enhanced_logger.error(f"Error in {func_name}: {{str(e)}}")',
            f'            return {{',
            f'                "success": False,',
            f'                "error": str(e)',
            f'            }}'
        ])
        
        return code_lines
    
    def _get_python_type(self, param_type: ParameterType) -> str:
        """Get Python type annotation for parameter type."""
        
        type_mapping = {
            ParameterType.STRING: "str",
            ParameterType.INTEGER: "int",
            ParameterType.FLOAT: "float",
            ParameterType.BOOLEAN: "bool",
            ParameterType.ARRAY: "List[Any]",
            ParameterType.OBJECT: "Dict[str, Any]",
            ParameterType.FILE_PATH: "str",
            ParameterType.UNITY_OBJECT: "str",
            ParameterType.ENUM: "str"
        }
        
        return type_mapping.get(param_type, "Any")
    
    def _validate_tool_data(self, tool_data: Dict[str, Any]):
        """Validate tool data structure."""
        
        required_fields = ["name", "description", "category"]
        for field in required_fields:
            if field not in tool_data:
                raise ValidationError(f"Required field '{field}' is missing")
        
        # Validate category
        try:
            ToolCategory(tool_data["category"])
        except ValueError:
            raise ValidationError(f"Invalid category: {tool_data['category']}")
        
        # Validate actions
        if "actions" in tool_data:
            for i, action_data in enumerate(tool_data["actions"]):
                self._validate_action_data(action_data, i)
    
    def _validate_action_data(self, action_data: Dict[str, Any], index: int):
        """Validate action data structure."""
        
        required_fields = ["name", "description", "unity_command"]
        for field in required_fields:
            if field not in action_data:
                raise ValidationError(f"Action {index}: Required field '{field}' is missing")
        
        # Validate parameters
        if "parameters" in action_data:
            for j, param_data in enumerate(action_data["parameters"]):
                self._validate_parameter_data(param_data, index, j)
    
    def _validate_parameter_data(self, param_data: Dict[str, Any], action_index: int, param_index: int):
        """Validate parameter data structure."""
        
        required_fields = ["name", "type", "description"]
        for field in required_fields:
            if field not in param_data:
                raise ValidationError(f"Action {action_index}, Parameter {param_index}: Required field '{field}' is missing")
        
        # Validate parameter type
        try:
            ParameterType(param_data["type"])
        except ValueError:
            raise ValidationError(f"Action {action_index}, Parameter {param_index}: Invalid parameter type: {param_data['type']}")
    
    def _dict_to_tool_definition(self, tool_data: Dict[str, Any]) -> CustomToolDefinition:
        """Convert dictionary to CustomToolDefinition."""
        
        tool_def = CustomToolDefinition(
            id=tool_data.get("id", str(uuid.uuid4())),
            name=tool_data["name"],
            description=tool_data["description"],
            category=ToolCategory(tool_data["category"]),
            version=tool_data.get("version", "1.0.0"),
            author=tool_data.get("author", "Unknown"),
            created_at=tool_data.get("created_at", time.time()),
            updated_at=tool_data.get("updated_at", time.time()),
            icon=tool_data.get("icon"),
            tags=tool_data.get("tags", []),
            enabled=tool_data.get("enabled", True)
        )
        
        # Convert actions
        for action_data in tool_data.get("actions", []):
            action = ToolAction(
                name=action_data["name"],
                description=action_data["description"],
                unity_command=action_data["unity_command"],
                return_type=action_data.get("return_type", "object"),
                timeout_seconds=action_data.get("timeout_seconds", 30),
                requires_unity_focus=action_data.get("requires_unity_focus", False)
            )
            
            # Convert parameters
            for param_data in action_data.get("parameters", []):
                param = ParameterDefinition(
                    name=param_data["name"],
                    type=ParameterType(param_data["type"]),
                    description=param_data["description"],
                    required=param_data.get("required", True),
                    default_value=param_data.get("default_value"),
                    validation_rules=param_data.get("validation_rules", {}),
                    enum_values=param_data.get("enum_values", []),
                    unity_object_type=param_data.get("unity_object_type")
                )
                action.parameters.append(param)
            
            tool_def.actions.append(action)
        
        # Convert global parameters
        for param_data in tool_data.get("global_parameters", []):
            param = ParameterDefinition(
                name=param_data["name"],
                type=ParameterType(param_data["type"]),
                description=param_data["description"],
                required=param_data.get("required", True),
                default_value=param_data.get("default_value"),
                validation_rules=param_data.get("validation_rules", {}),
                enum_values=param_data.get("enum_values", []),
                unity_object_type=param_data.get("unity_object_type")
            )
            tool_def.global_parameters.append(param)
        
        return tool_def
    
    def _save_tool(self, tool_def: CustomToolDefinition):
        """Save tool definition to disk."""
        
        tool_file = self.tools_directory / f"{tool_def.id}.json"
        
        # Convert to dictionary for JSON serialization
        tool_dict = asdict(tool_def)
        
        # Convert enums to strings
        tool_dict["category"] = tool_def.category.value
        for action in tool_dict["actions"]:
            for param in action["parameters"]:
                param["type"] = param["type"].value if hasattr(param["type"], 'value') else param["type"]
        for param in tool_dict["global_parameters"]:
            param["type"] = param["type"].value if hasattr(param["type"], 'value') else param["type"]
        
        try:
            with open(tool_file, 'w', encoding='utf-8') as f:
                json.dump(tool_dict, f, indent=2, default=str)
        except Exception as e:
            raise ResourceError(f"Failed to save tool definition: {str(e)}")


# Global custom tool creator instance
custom_tool_creator = CustomToolCreator()


# Web interface for custom tool creation
def create_web_interface():
    """Create a simple web interface for custom tool creation."""

    html_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unity MCP Custom Tool Creator</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .content {
            padding: 30px;
        }
        .tabs {
            display: flex;
            border-bottom: 2px solid #eee;
            margin-bottom: 30px;
        }
        .tab {
            padding: 15px 25px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 16px;
            color: #666;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }
        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #333;
        }
        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .form-group textarea {
            height: 100px;
            resize: vertical;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn-secondary {
            background: #6c757d;
        }
        .btn-danger {
            background: #dc3545;
        }
        .tool-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .tool-card {
            border: 2px solid #eee;
            border-radius: 8px;
            padding: 20px;
            transition: all 0.3s;
        }
        .tool-card:hover {
            border-color: #667eea;
            transform: translateY(-2px);
        }
        .tool-card h3 {
            margin: 0 0 10px 0;
            color: #333;
        }
        .tool-card p {
            color: #666;
            margin: 0 0 15px 0;
        }
        .tool-card .actions {
            display: flex;
            gap: 10px;
        }
        .template-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .template-card {
            border: 2px solid #eee;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .template-card:hover {
            border-color: #667eea;
            background: #f8f9ff;
        }
        .template-card h4 {
            margin: 0 0 10px 0;
            color: #333;
        }
        .template-card p {
            color: #666;
            margin: 0;
            font-size: 14px;
        }
        .parameter-list {
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 15px;
            margin-top: 10px;
        }
        .parameter-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .parameter-item:last-child {
            margin-bottom: 0;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-enabled {
            background-color: #28a745;
        }
        .status-disabled {
            background-color: #dc3545;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛠️ Unity MCP Custom Tool Creator</h1>
            <p>Create and manage custom MCP tools with a visual interface</p>
        </div>

        <div class="content">
            <div class="tabs">
                <button class="tab active" onclick="showTab('create')">Create Tool</button>
                <button class="tab" onclick="showTab('templates')">Templates</button>
                <button class="tab" onclick="showTab('manage')">Manage Tools</button>
                <button class="tab" onclick="showTab('export')">Export/Import</button>
            </div>

            <!-- Create Tool Tab -->
            <div id="create" class="tab-content active">
                <h2>Create Custom Tool</h2>
                <form id="toolForm">
                    <div class="form-group">
                        <label for="toolName">Tool Name *</label>
                        <input type="text" id="toolName" name="name" required placeholder="My Custom Tool">
                    </div>

                    <div class="form-group">
                        <label for="toolDescription">Description *</label>
                        <textarea id="toolDescription" name="description" required placeholder="Describe what your tool does..."></textarea>
                    </div>

                    <div class="form-group">
                        <label for="toolCategory">Category *</label>
                        <select id="toolCategory" name="category" required>
                            <option value="">Select Category</option>
                            <option value="asset_management">Asset Management</option>
                            <option value="scene_management">Scene Management</option>
                            <option value="object_manipulation">Object Manipulation</option>
                            <option value="utility">Utility</option>
                            <option value="automation">Automation</option>
                            <option value="debugging">Debugging</option>
                            <option value="custom">Custom</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="toolAuthor">Author</label>
                        <input type="text" id="toolAuthor" name="author" placeholder="Your Name">
                    </div>

                    <div class="form-group">
                        <label for="toolTags">Tags (comma-separated)</label>
                        <input type="text" id="toolTags" name="tags" placeholder="unity, automation, custom">
                    </div>

                    <h3>Actions</h3>
                    <div id="actionsList">
                        <!-- Actions will be added dynamically -->
                    </div>
                    <button type="button" class="btn btn-secondary" onclick="addAction()">Add Action</button>

                    <div style="margin-top: 30px;">
                        <button type="submit" class="btn">Create Tool</button>
                        <button type="button" class="btn btn-secondary" onclick="validateTool()">Validate</button>
                    </div>
                </form>
            </div>

            <!-- Templates Tab -->
            <div id="templates" class="tab-content">
                <h2>Tool Templates</h2>
                <p>Start with a pre-built template to quickly create common tool types.</p>

                <div class="template-grid">
                    <div class="template-card" onclick="useTemplate('basic_asset_tool')">
                        <h4>📁 Basic Asset Tool</h4>
                        <p>Template for basic asset operations like processing and manipulation</p>
                    </div>

                    <div class="template-card" onclick="useTemplate('scene_utility')">
                        <h4>🎬 Scene Utility</h4>
                        <p>Template for scene manipulation and management tools</p>
                    </div>

                    <div class="template-card" onclick="useTemplate('automation_script')">
                        <h4>🤖 Automation Script</h4>
                        <p>Template for creating automation and batch processing tools</p>
                    </div>
                </div>
            </div>

            <!-- Manage Tools Tab -->
            <div id="manage" class="tab-content">
                <h2>Manage Custom Tools</h2>
                <p>View, edit, and manage your existing custom tools.</p>

                <div id="toolsList" class="tool-list">
                    <!-- Tools will be loaded dynamically -->
                </div>
            </div>

            <!-- Export/Import Tab -->
            <div id="export" class="tab-content">
                <h2>Export & Import Tools</h2>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                    <div>
                        <h3>Export Tools</h3>
                        <p>Export your custom tools to share with others or backup.</p>
                        <button class="btn" onclick="exportTools()">Export All Tools</button>
                        <button class="btn btn-secondary" onclick="exportSelectedTools()">Export Selected</button>
                    </div>

                    <div>
                        <h3>Import Tools</h3>
                        <p>Import custom tools from exported files.</p>
                        <input type="file" id="importFile" accept=".json" style="margin-bottom: 10px;">
                        <button class="btn" onclick="importTools()">Import Tools</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let actionCounter = 0;
        let parameterCounters = {};

        function showTab(tabName) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });

            // Remove active class from all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });

            // Show selected tab content
            document.getElementById(tabName).classList.add('active');

            // Add active class to clicked tab
            event.target.classList.add('active');

            // Load data for specific tabs
            if (tabName === 'manage') {
                loadTools();
            }
        }

        function addAction() {
            actionCounter++;
            const actionId = `action_${actionCounter}`;
            parameterCounters[actionId] = 0;

            const actionHtml = `
                <div class="parameter-list" id="${actionId}">
                    <h4>Action ${actionCounter}</h4>
                    <div class="form-group">
                        <label>Action Name *</label>
                        <input type="text" name="${actionId}_name" required placeholder="process_data">
                    </div>
                    <div class="form-group">
                        <label>Description *</label>
                        <input type="text" name="${actionId}_description" required placeholder="Process data with custom logic">
                    </div>
                    <div class="form-group">
                        <label>Unity Command *</label>
                        <input type="text" name="${actionId}_command" required placeholder="ProcessData">
                    </div>
                    <div class="form-group">
                        <label>Timeout (seconds)</label>
                        <input type="number" name="${actionId}_timeout" value="30" min="1" max="300">
                    </div>

                    <h5>Parameters</h5>
                    <div id="${actionId}_parameters">
                        <!-- Parameters will be added here -->
                    </div>
                    <button type="button" class="btn btn-secondary" onclick="addParameter('${actionId}')">Add Parameter</button>
                    <button type="button" class="btn btn-danger" onclick="removeAction('${actionId}')">Remove Action</button>
                </div>
            `;

            document.getElementById('actionsList').insertAdjacentHTML('beforeend', actionHtml);
        }

        function removeAction(actionId) {
            document.getElementById(actionId).remove();
            delete parameterCounters[actionId];
        }

        function addParameter(actionId) {
            parameterCounters[actionId]++;
            const paramId = `${actionId}_param_${parameterCounters[actionId]}`;

            const paramHtml = `
                <div class="parameter-item" id="${paramId}">
                    <input type="text" name="${paramId}_name" placeholder="Parameter name" style="flex: 1;">
                    <select name="${paramId}_type" style="flex: 1;">
                        <option value="string">String</option>
                        <option value="integer">Integer</option>
                        <option value="float">Float</option>
                        <option value="boolean">Boolean</option>
                        <option value="array">Array</option>
                        <option value="object">Object</option>
                        <option value="file_path">File Path</option>
                        <option value="unity_object">Unity Object</option>
                        <option value="enum">Enum</option>
                    </select>
                    <input type="text" name="${paramId}_description" placeholder="Description" style="flex: 2;">
                    <label><input type="checkbox" name="${paramId}_required" checked> Required</label>
                    <button type="button" class="btn btn-danger" onclick="removeParameter('${paramId}')" style="padding: 5px 10px;">×</button>
                </div>
            `;

            document.getElementById(`${actionId}_parameters`).insertAdjacentHTML('beforeend', paramHtml);
        }

        function removeParameter(paramId) {
            document.getElementById(paramId).remove();
        }

        function useTemplate(templateName) {
            // This would populate the form with template data
            alert(`Using template: ${templateName}\\nThis would populate the form with template data.`);
            showTab('create');
        }

        function validateTool() {
            const formData = new FormData(document.getElementById('toolForm'));
            const toolData = formDataToToolData(formData);

            // This would send validation request to server
            alert('Tool validation would be performed here.\\nAll fields and actions would be validated.');
        }

        function formDataToToolData(formData) {
            // Convert form data to tool data structure
            const toolData = {
                name: formData.get('name'),
                description: formData.get('description'),
                category: formData.get('category'),
                author: formData.get('author') || 'Unknown',
                tags: formData.get('tags') ? formData.get('tags').split(',').map(t => t.trim()) : [],
                actions: []
            };

            // Extract actions and parameters
            // This would be implemented to parse the dynamic form data

            return toolData;
        }

        function loadTools() {
            // This would load tools from the server
            const toolsHtml = `
                <div class="tool-card">
                    <span class="status-indicator status-enabled"></span>
                    <h3>Sample Custom Tool</h3>
                    <p>This is a sample custom tool for demonstration purposes.</p>
                    <div class="actions">
                        <button class="btn btn-secondary">Edit</button>
                        <button class="btn btn-secondary">Duplicate</button>
                        <button class="btn btn-danger">Delete</button>
                    </div>
                </div>
            `;

            document.getElementById('toolsList').innerHTML = toolsHtml;
        }

        function exportTools() {
            alert('All tools would be exported as JSON file.');
        }

        function exportSelectedTools() {
            alert('Selected tools would be exported as JSON file.');
        }

        function importTools() {
            const fileInput = document.getElementById('importFile');
            if (fileInput.files.length === 0) {
                alert('Please select a file to import.');
                return;
            }

            alert('Tools would be imported from the selected file.');
        }

        // Initialize with one action
        addAction();

        // Form submission
        document.getElementById('toolForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const toolData = formDataToToolData(formData);

            alert('Tool would be created with the provided data.\\nThis would send a request to the server to create the custom tool.');
        });
    </script>
</body>
</html>
    '''

    # Save the HTML file
    web_interface_path = Path("UnityMcpServer/web_interface")
    web_interface_path.mkdir(parents=True, exist_ok=True)

    with open(web_interface_path / "custom_tool_creator.html", 'w', encoding='utf-8') as f:
        f.write(html_content)

    return str(web_interface_path / "custom_tool_creator.html")
