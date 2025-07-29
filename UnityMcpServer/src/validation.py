"""
Input validation framework for Unity MCP Server.
Provides comprehensive validation for all tool parameters
to catch errors early and provide clear feedback.
"""

import re
from typing import Any, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass
from enum import Enum
import os.path

from exceptions import ValidationError


class ValidationType(Enum):
    """Types of validation rules."""
    REQUIRED = "required"
    TYPE = "type"
    RANGE = "range"
    LENGTH = "length"
    PATTERN = "pattern"
    CHOICES = "choices"
    PATH = "path"
    CUSTOM = "custom"


@dataclass
class ValidationRule:
    """A single validation rule."""
    rule_type: ValidationType
    value: Any = None
    message: str = None
    
    def __post_init__(self):
        if not self.message:
            self.message = self._generate_default_message()
    
    def _generate_default_message(self) -> str:
        """Generate default error message for the rule."""
        try:
            if self.rule_type == ValidationType.REQUIRED:
                return "This parameter is required"
            elif self.rule_type == ValidationType.TYPE:
                return f"Must be of type {self.value.__name__ if isinstance(self.value, type) else self.value}"
            elif self.rule_type == ValidationType.RANGE and self.value and len(self.value) >= 2:
                return f"Must be between {self.value[0]} and {self.value[1]}"
            elif self.rule_type == ValidationType.LENGTH and self.value and len(self.value) >= 2:
                return f"Length must be between {self.value[0]} and {self.value[1]}"
            elif self.rule_type == ValidationType.PATTERN:
                return f"Must match pattern: {self.value}"
            elif self.rule_type == ValidationType.CHOICES and self.value:
                return f"Must be one of: {', '.join(map(str, self.value))}"
            elif self.rule_type == ValidationType.PATH:
                return "Must be a valid path"
            elif self.rule_type == ValidationType.CUSTOM:
                return "Custom validation failed"
            else:
                return "Validation failed"
        except Exception:
            return "Validation failed"


class ParameterValidator:
    """Validates individual parameters."""
    
    def __init__(self, parameter_name: str, rules: List[ValidationRule]):
        self.parameter_name = parameter_name
        self.rules = rules
    
    def validate(self, value: Any) -> None:
        """Validate a parameter value against all rules."""
        for rule in self.rules:
            try:
                self._validate_rule(value, rule)
            except ValidationError as e:
                # Re-raise with parameter context
                raise ValidationError(
                    f"Parameter '{self.parameter_name}': {e.message}",
                    parameter=self.parameter_name,
                    value=value,
                    context=e.context
                )
    
    def _validate_rule(self, value: Any, rule: ValidationRule) -> None:
        """Validate a single rule."""
        if rule.rule_type == ValidationType.REQUIRED:
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValidationError(rule.message)
        
        # Skip other validations if value is None (unless required)
        if value is None:
            return
        
        if rule.rule_type == ValidationType.TYPE:
            expected_type = rule.value
            if not isinstance(value, expected_type):
                raise ValidationError(
                    rule.message,
                    context={"expected_type": expected_type.__name__, "actual_type": type(value).__name__}
                )
        
        elif rule.rule_type == ValidationType.RANGE:
            min_val, max_val = rule.value
            if not (min_val <= value <= max_val):
                raise ValidationError(
                    rule.message,
                    context={"min_value": min_val, "max_value": max_val, "actual_value": value}
                )
        
        elif rule.rule_type == ValidationType.LENGTH:
            min_len, max_len = rule.value
            length = len(value) if hasattr(value, '__len__') else 0
            if not (min_len <= length <= max_len):
                raise ValidationError(
                    rule.message,
                    context={"min_length": min_len, "max_length": max_len, "actual_length": length}
                )
        
        elif rule.rule_type == ValidationType.PATTERN:
            pattern = rule.value
            if isinstance(value, str) and not re.match(pattern, value):
                raise ValidationError(
                    rule.message,
                    context={"pattern": pattern, "value": value}
                )
        
        elif rule.rule_type == ValidationType.CHOICES:
            choices = rule.value
            if choices is None:
                raise ValidationError("Choices validation rule has no valid choices defined")
            if value not in choices:
                raise ValidationError(
                    rule.message,
                    context={"valid_choices": choices, "actual_value": value}
                )
        
        elif rule.rule_type == ValidationType.PATH:
            if isinstance(value, str):
                # Basic path validation - check for invalid characters
                invalid_chars = '<>:"|?*' if os.name == 'nt' else '\0'
                if any(char in value for char in invalid_chars):
                    raise ValidationError(
                        rule.message,
                        context={"invalid_characters": invalid_chars, "path": value}
                    )
        
        elif rule.rule_type == ValidationType.CUSTOM:
            validator_func = rule.value
            if callable(validator_func):
                try:
                    if not validator_func(value):
                        raise ValidationError(rule.message)
                except Exception as e:
                    raise ValidationError(
                        f"Custom validation failed: {str(e)}",
                        context={"custom_error": str(e)}
                    )


class ToolValidator:
    """Validates all parameters for a tool."""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.parameter_validators: Dict[str, ParameterValidator] = {}
    
    def add_parameter(self, name: str, rules: List[ValidationRule]) -> 'ToolValidator':
        """Add a parameter validator."""
        self.parameter_validators[name] = ParameterValidator(name, rules)
        return self
    
    def validate(self, parameters: Dict[str, Any]) -> None:
        """Validate all parameters for the tool."""
        errors = []
        
        for param_name, validator in self.parameter_validators.items():
            try:
                value = parameters.get(param_name)
                validator.validate(value)
            except ValidationError as e:
                errors.append(e)
        
        if errors:
            # Combine all validation errors
            error_messages = [e.message for e in errors]
            combined_message = f"Validation failed for tool '{self.tool_name}': " + "; ".join(error_messages)
            
            # Use the first error's context as base, add tool context
            context = errors[0].context.copy() if errors else {}
            context.update({
                "tool_name": self.tool_name,
                "total_errors": len(errors),
                "all_errors": [e.to_dict() for e in errors]
            })
            
            raise ValidationError(
                combined_message,
                context=context
            )


# Common validation rule factories
def required() -> ValidationRule:
    """Create a required validation rule."""
    return ValidationRule(ValidationType.REQUIRED)


def type_check(expected_type: Type) -> ValidationRule:
    """Create a type validation rule."""
    return ValidationRule(ValidationType.TYPE, expected_type)


def range_check(min_val: Union[int, float], max_val: Union[int, float]) -> ValidationRule:
    """Create a range validation rule."""
    return ValidationRule(ValidationType.RANGE, (min_val, max_val))


def length_check(min_len: int, max_len: int) -> ValidationRule:
    """Create a length validation rule."""
    return ValidationRule(ValidationType.LENGTH, (min_len, max_len))


def pattern_check(pattern: str) -> ValidationRule:
    """Create a pattern validation rule."""
    return ValidationRule(ValidationType.PATTERN, pattern)


def choices_check(choices: List[Any]) -> ValidationRule:
    """Create a choices validation rule."""
    return ValidationRule(ValidationType.CHOICES, choices)


def path_check() -> ValidationRule:
    """Create a path validation rule."""
    return ValidationRule(ValidationType.PATH)


def custom_check(validator_func: Callable[[Any], bool], message: str = None) -> ValidationRule:
    """Create a custom validation rule."""
    return ValidationRule(ValidationType.CUSTOM, validator_func, message)


# Pre-defined validators for common Unity MCP parameters
def create_action_validator(valid_actions: List[str]) -> List[ValidationRule]:
    """Create validator for action parameters."""
    return [
        required(),
        type_check(str),
        choices_check(valid_actions)
    ]


def create_path_validator(required_param: bool = True) -> List[ValidationRule]:
    """Create validator for path parameters."""
    rules = [type_check(str), path_check()]
    if required_param:
        rules.insert(0, required())
    return rules


def create_name_validator(required_param: bool = True) -> List[ValidationRule]:
    """Create validator for name parameters."""
    rules = [
        type_check(str),
        length_check(1, 255),
        pattern_check(r'^[a-zA-Z_][a-zA-Z0-9_]*$')  # Valid identifier pattern
    ]
    if required_param:
        rules.insert(0, required())
    return rules


def create_position_validator() -> List[ValidationRule]:
    """Create validator for position parameters (3D coordinates)."""
    def validate_position(value):
        return (isinstance(value, list) and
                len(value) == 3 and
                all(isinstance(x, (int, float)) for x in value))

    return [
        type_check(list),
        custom_check(validate_position, "Position must be a list of 3 numbers [x, y, z]")
    ]


# Tool-specific validator factories
class UnityToolValidators:
    """Pre-configured validators for Unity MCP tools."""

    @staticmethod
    def create_manage_script_validator() -> ToolValidator:
        """Create validator for manage_script tool."""
        validator = ToolValidator("manage_script")

        validator.add_parameter("action", create_action_validator([
            "create", "read", "update", "delete"
        ]))
        validator.add_parameter("name", create_name_validator(required_param=True))
        validator.add_parameter("path", create_path_validator(required_param=True))
        validator.add_parameter("script_type", [
            type_check(str),
            choices_check(["MonoBehaviour", "ScriptableObject", "Editor", "Custom"])
        ])
        validator.add_parameter("namespace", [
            type_check(str),
            pattern_check(r'^[a-zA-Z_][a-zA-Z0-9_.]*$')
        ])

        return validator

    @staticmethod
    def create_manage_editor_validator() -> ToolValidator:
        """Create validator for manage_editor tool."""
        validator = ToolValidator("manage_editor")

        validator.add_parameter("action", create_action_validator([
            "play", "pause", "stop", "get_state", "get_windows", "get_active_tool",
            "get_selection", "set_active_tool", "add_tag", "remove_tag", "get_tags",
            "add_layer", "remove_layer", "get_layers"
        ]))
        validator.add_parameter("tool_name", [type_check(str), length_check(1, 100)])
        validator.add_parameter("tag_name", [type_check(str), length_check(1, 50)])
        validator.add_parameter("layer_name", [type_check(str), length_check(1, 50)])

        return validator

    @staticmethod
    def create_manage_scene_validator() -> ToolValidator:
        """Create validator for manage_scene tool."""
        validator = ToolValidator("manage_scene")

        validator.add_parameter("action", create_action_validator([
            "load", "save", "create", "get_hierarchy", "get_active", "set_active"
        ]))
        validator.add_parameter("name", create_name_validator(required_param=True))
        validator.add_parameter("path", create_path_validator(required_param=True))
        validator.add_parameter("build_index", [
            type_check(int),
            range_check(0, 1000)
        ])

        return validator

    @staticmethod
    def create_manage_gameobject_validator() -> ToolValidator:
        """Create validator for manage_gameobject tool."""
        validator = ToolValidator("manage_gameobject")

        validator.add_parameter("action", create_action_validator([
            "create", "modify", "delete", "find", "add_component", "remove_component",
            "set_component_property", "get_components"
        ]))
        validator.add_parameter("target", [type_check(str), length_check(1, 255)])
        validator.add_parameter("search_method", [
            type_check(str),
            choices_check(["by_name", "by_id", "by_path", "by_tag"])
        ])
        validator.add_parameter("name", create_name_validator(required_param=False))
        validator.add_parameter("tag", [type_check(str), length_check(1, 50)])
        validator.add_parameter("position", create_position_validator())
        validator.add_parameter("rotation", create_position_validator())  # Also 3D vector
        validator.add_parameter("scale", create_position_validator())     # Also 3D vector

        return validator

    @staticmethod
    def create_manage_asset_validator() -> ToolValidator:
        """Create validator for manage_asset tool."""
        validator = ToolValidator("manage_asset")

        validator.add_parameter("action", create_action_validator([
            "import", "create", "modify", "delete", "duplicate", "move", "rename",
            "search", "get_info", "create_folder", "get_components"
        ]))
        validator.add_parameter("path", create_path_validator(required_param=True))
        validator.add_parameter("asset_type", [
            type_check(str),
            choices_check(["Material", "Texture", "Prefab", "Script", "Shader", "Folder"])
        ])
        validator.add_parameter("destination", create_path_validator(required_param=False))
        validator.add_parameter("search_pattern", [
            type_check(str),
            pattern_check(r'^[*?a-zA-Z0-9_.\-/\\]+$')  # Basic glob pattern
        ])

        return validator

    @staticmethod
    def create_read_console_validator() -> ToolValidator:
        """Create validator for read_console tool."""
        validator = ToolValidator("read_console")

        validator.add_parameter("action", create_action_validator(["get", "clear"]))
        validator.add_parameter("types", [
            type_check(list),
            custom_check(
                lambda x: all(t in ["error", "warning", "log", "all"] for t in x),
                "Types must be a list containing only: error, warning, log, all"
            )
        ])
        validator.add_parameter("count", [type_check(int), range_check(1, 10000)])
        validator.add_parameter("format", [
            type_check(str),
            choices_check(["plain", "detailed", "json"])
        ])

        return validator

    @staticmethod
    def create_execute_menu_item_validator() -> ToolValidator:
        """Create validator for execute_menu_item tool."""
        validator = ToolValidator("execute_menu_item")

        validator.add_parameter("menu_path", [
            required(),
            type_check(str),
            length_check(1, 500),
            pattern_check(r'^[a-zA-Z0-9_\-/\s]+$')  # Menu path pattern
        ])
        validator.add_parameter("action", create_action_validator(["execute", "get_available_menus"]))

        return validator

    @staticmethod
    def create_manage_shader_validator() -> ToolValidator:
        """Create validator for manage_shader tool."""
        validator = ToolValidator("manage_shader")

        validator.add_parameter("action", create_action_validator([
            "create", "read", "update", "delete"
        ]))
        validator.add_parameter("name", create_name_validator(required_param=True))
        validator.add_parameter("path", create_path_validator(required_param=True))

        return validator


# Global validator registry
_validator_registry: Dict[str, ToolValidator] = {}


def get_tool_validator(tool_name: str) -> Optional[ToolValidator]:
    """Get validator for a specific tool."""
    if tool_name not in _validator_registry:
        # Create validator on first access
        validator_factory = getattr(UnityToolValidators, f"create_{tool_name}_validator", None)
        if validator_factory:
            _validator_registry[tool_name] = validator_factory()
        else:
            return None

    return _validator_registry[tool_name]


def validate_tool_parameters(tool_name: str, parameters: Dict[str, Any]) -> None:
    """Validate parameters for a specific tool."""
    # Import config here to avoid circular imports
    try:
        from config import config
        if not config.enable_strict_validation:
            return
    except ImportError:
        # If config is not available, skip validation
        return

    validator = get_tool_validator(tool_name)
    if validator:
        validator.validate(parameters)
