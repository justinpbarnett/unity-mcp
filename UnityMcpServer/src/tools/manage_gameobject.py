from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Any, List, Optional
import time
import uuid

# Import enhanced infrastructure
from enhanced_connection import get_enhanced_unity_connection
from exceptions import ValidationError, UnityOperationError, create_error_response
from enhanced_logging import enhanced_logger, LogContext
from timeout_manager import with_timeout, OperationType
from validation import validate_tool_parameters
from config import config

def register_manage_gameobject_tools(mcp: FastMCP):
    """Register all GameObject management tools with the MCP server."""

    @mcp.tool()
    def manage_gameobject(
        ctx: Context,
        action: str,
        target: str = None,  # GameObject identifier by name or path
        search_method: str = None,
        # --- Combined Parameters for Create/Modify ---
        name: str = None,  # Used for both 'create' (new object name) and 'modify' (rename)
        tag: str = None,  # Used for both 'create' (initial tag) and 'modify' (change tag)
        parent: str = None,  # Used for both 'create' (initial parent) and 'modify' (change parent)
        position: List[float] = None,
        rotation: List[float] = None,
        scale: List[float] = None,
        components_to_add: List[str] = None,  # List of component names to add
        primitive_type: str = None,
        save_as_prefab: bool = False,
        prefab_path: str = None,
        prefab_folder: str = "Assets/Prefabs",
        # --- Parameters for 'modify' ---
        set_active: bool = None,
        layer: str = None,  # Layer name
        components_to_remove: List[str] = None,
        component_properties: Dict[str, Dict[str, Any]] = None,
        # --- Parameters for 'find' ---
        search_term: str = None,
        find_all: bool = False,
        search_in_children: bool = False,
        search_inactive: bool = False,
        # -- Component Management Arguments --
        component_name: str = None,
        includeNonPublicSerialized: bool = None, # Controls serialization of private [SerializeField] fields
    ) -> Dict[str, Any]:
        """Manages GameObjects: create, modify, delete, find, and component operations.

        Args:
            action: Operation (e.g., 'create', 'modify', 'find', 'add_component', 'remove_component', 'set_component_property', 'get_components').
            target: GameObject identifier (name or path string) for modify/delete/component actions.
            search_method: How to find objects ('by_name', 'by_id', 'by_path', etc.). Used with 'find' and some 'target' lookups.
            name: GameObject name - used for both 'create' (initial name) and 'modify' (rename).
            tag: Tag name - used for both 'create' (initial tag) and 'modify' (change tag).
            parent: Parent GameObject reference - used for both 'create' (initial parent) and 'modify' (change parent).
            layer: Layer name - used for both 'create' (initial layer) and 'modify' (change layer).
            component_properties: Dict mapping Component names to their properties to set.
            components_to_add: List of component names to add.
            includeNonPublicSerialized: If True, includes private fields marked [SerializeField] in component data.

        Returns:
            Dictionary with operation results ('success', 'message', 'data').
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Create log context
        log_context = LogContext(
            operation=f"manage_gameobject.{action}",
            tool_name="manage_gameobject",
            request_id=request_id
        )

        try:
            # Log tool call
            enhanced_logger.log_tool_call(
                "manage_gameobject",
                action,
                {
                    "target": target,
                    "search_method": search_method,
                    "name": name,
                    "tag": tag,
                    "has_position": position is not None,
                    "has_components_to_add": components_to_add is not None,
                    "save_as_prefab": save_as_prefab
                },
                request_id
            )

            # Validate input parameters
            parameters = {
                "action": action,
                "target": target,
                "search_method": search_method,
                "name": name,
                "tag": tag,
                "parent": parent,
                "position": position,
                "rotation": rotation,
                "scale": scale,
                "components_to_add": components_to_add,
                "primitive_type": primitive_type,
                "save_as_prefab": save_as_prefab,
                "prefab_path": prefab_path,
                "prefab_folder": prefab_folder,
                "set_active": set_active,
                "layer": layer,
                "components_to_remove": components_to_remove,
                "component_properties": component_properties,
                "search_term": search_term,
                "find_all": find_all,
                "search_in_children": search_in_children,
                "search_inactive": search_inactive,
                "component_name": component_name,
                "includeNonPublicSerialized": includeNonPublicSerialized
            }

            validate_tool_parameters("manage_gameobject", parameters)

            # Execute the operation with timeout
            result = _execute_gameobject_operation(
                action, target, search_method, name, tag, parent, position, rotation, scale,
                components_to_add, primitive_type, save_as_prefab, prefab_path, prefab_folder,
                set_active, layer, components_to_remove, component_properties, search_term,
                find_all, search_in_children, search_inactive, component_name,
                includeNonPublicSerialized, log_context
            )

            # Log successful result
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_gameobject", action, True,
                result_summary=f"GameObject {action} completed",
                request_id=request_id,
                duration=duration
            )

            return result

        except ValidationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_gameobject", action, False,
                error_message=f"Validation error: {e.message}",
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except UnityOperationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_gameobject", action, False,
                error_message=e.message,
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except Exception as e:
            duration = time.time() - start_time
            enhanced_logger.error(
                f"Unexpected error in manage_gameobject.{action}",
                context=log_context,
                exception=e,
                parameters={k: v for k, v in parameters.items() if k not in ['component_properties']}  # Exclude complex objects
            )
            enhanced_logger.log_tool_result(
                "manage_gameobject", action, False,
                error_message=f"Internal error: {str(e)}",
                request_id=request_id,
                duration=duration
            )

            # Create generic error response for unexpected errors
            from exceptions import UnityMcpError, ErrorCategory, ErrorSeverity
            error = UnityMcpError(
                f"Unexpected error in GameObject management: {str(e)}",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH,
                context={"original_error": str(e), "action": action, "target": target}
            )
            return create_error_response(error)


@with_timeout(OperationType.GAMEOBJECT_OPERATION, "gameobject_operation")
def _execute_gameobject_operation(
    action: str,
    target: Optional[str],
    search_method: Optional[str],
    name: Optional[str],
    tag: Optional[str],
    parent: Optional[str],
    position: Optional[List[float]],
    rotation: Optional[List[float]],
    scale: Optional[List[float]],
    components_to_add: Optional[List[str]],
    primitive_type: Optional[str],
    save_as_prefab: bool,
    prefab_path: Optional[str],
    prefab_folder: str,
    set_active: Optional[bool],
    layer: Optional[str],
    components_to_remove: Optional[List[str]],
    component_properties: Optional[Dict[str, Dict[str, Any]]],
    search_term: Optional[str],
    find_all: bool,
    search_in_children: bool,
    search_inactive: bool,
    component_name: Optional[str],
    includeNonPublicSerialized: Optional[bool],
    log_context: LogContext
) -> Dict[str, Any]:
    """Execute GameObject operation with proper error handling and logging."""

    enhanced_logger.info(
        f"Executing GameObject operation: {action}",
        context=log_context,
        target=target,
        search_method=search_method,
        gameobject_name=name,
        save_as_prefab=save_as_prefab
    )

    try:
        # Prepare parameters for Unity
        params = {
            "action": action,
            "target": target,
            "searchMethod": search_method,
            "name": name,
            "tag": tag,
            "parent": parent,
            "position": position,
            "rotation": rotation,
            "scale": scale,
            "componentsToAdd": components_to_add,
            "primitiveType": primitive_type,
            "saveAsPrefab": save_as_prefab,
            "prefabPath": prefab_path,
            "prefabFolder": prefab_folder,
            "setActive": set_active,
            "layer": layer,
            "componentsToRemove": components_to_remove,
            "componentProperties": component_properties,
            "searchTerm": search_term,
            "findAll": find_all,
            "searchInChildren": search_in_children,
            "searchInactive": search_inactive,
            "componentName": component_name,
            "includeNonPublicSerialized": includeNonPublicSerialized
        }

        # Remove None values to avoid sending null
        params = {k: v for k, v in params.items() if v is not None}

        # Handle prefab path logic with validation
        if action == "create" and params.get("saveAsPrefab"):
            params = _handle_prefab_path_logic(params, prefab_folder, log_context)

        # Validate action-specific requirements
        _validate_gameobject_action(action, params, log_context)

        # Get connection and send command
        connection = get_enhanced_unity_connection()

        enhanced_logger.info(
            "Sending GameObject command to Unity",
            context=log_context,
            command_params=list(params.keys()),
            param_count=len(params)
        )

        response = connection.send_command("manage_gameobject", params)

        # Process response from Unity
        if response.get("success"):
            result_data = response.get("data", {})

            enhanced_logger.info(
                f"GameObject operation '{action}' completed successfully",
                context=log_context,
                response_message=response.get("message", ""),
                result_keys=list(result_data.keys()) if result_data else []
            )

            return {
                "success": True,
                "message": response.get("message", "GameObject operation completed successfully."),
                "data": result_data
            }
        else:
            error_message = response.get("error", "Unknown Unity error occurred during GameObject management.")
            enhanced_logger.error(
                f"Unity GameObject operation failed: {error_message}",
                context=log_context,
                unity_error=error_message
            )

            raise UnityOperationError(
                error_message,
                operation=f"manage_gameobject.{action}",
                unity_error=error_message,
                context={"target": target, "action": action, "gameobject_name": name}
            )

    except Exception as e:
        if isinstance(e, (UnityOperationError, ValidationError)):
            raise  # Re-raise our custom exceptions

        # Wrap unexpected exceptions
        enhanced_logger.error(
            f"Unexpected error during GameObject operation",
            context=log_context,
            exception=e,
            target=target,
            action=action
        )

        raise UnityOperationError(
            f"GameObject operation failed: {str(e)}",
            operation=f"manage_gameobject.{action}",
            context={"original_error": str(e), "target": target}
        )


def _handle_prefab_path_logic(params: Dict[str, Any], prefab_folder: str, log_context: LogContext) -> Dict[str, Any]:
    """Handle prefab path logic with proper validation."""

    if "prefabPath" not in params:
        if "name" not in params or not params["name"]:
            raise ValidationError(
                "Cannot create default prefab path: 'name' parameter is missing",
                parameter="name",
                context={"action": "create", "save_as_prefab": True}
            )

        # Use the provided prefab_folder and the name to construct the path
        constructed_path = f"{prefab_folder}/{params['name']}.prefab"
        # Ensure clean path separators (Unity prefers '/')
        params["prefabPath"] = constructed_path.replace("\\", "/")

        enhanced_logger.info(
            f"Constructed prefab path: {params['prefabPath']}",
            context=log_context,
            prefab_folder=prefab_folder,
            gameobject_name=params['name']
        )
    else:
        # Validate provided prefab path
        prefab_path = params["prefabPath"]
        if not prefab_path.lower().endswith(".prefab"):
            raise ValidationError(
                f"Invalid prefab_path: '{prefab_path}' must end with .prefab",
                parameter="prefab_path",
                value=prefab_path
            )

    # Remove prefab_folder from params as C# side only needs the final prefabPath
    params.pop("prefabFolder", None)

    return params


def _validate_gameobject_action(action: str, params: Dict[str, Any], log_context: LogContext) -> None:
    """Validate action-specific requirements for GameObject operations."""

    # Action-specific validation
    if action in ["modify", "delete", "add_component", "remove_component", "set_component_property", "get_components"]:
        if not params.get("target"):
            raise ValidationError(
                f"Target GameObject is required for {action} action",
                parameter="target",
                context={"action": action}
            )

    if action == "create" and not params.get("name"):
        raise ValidationError(
            "GameObject name is required for create action",
            parameter="name",
            context={"action": action}
        )

    if action in ["add_component", "remove_component"] and not params.get("componentName"):
        raise ValidationError(
            f"Component name is required for {action} action",
            parameter="component_name",
            context={"action": action}
        )

    if action == "set_component_property":
        if not params.get("componentName"):
            raise ValidationError(
                "Component name is required for set_component_property action",
                parameter="component_name",
                context={"action": action}
            )
        if not params.get("componentProperties"):
            raise ValidationError(
                "Component properties are required for set_component_property action",
                parameter="component_properties",
                context={"action": action}
            )

    if action == "find" and not params.get("searchTerm"):
        raise ValidationError(
            "Search term is required for find action",
            parameter="search_term",
            context={"action": action}
        )

    # Validate position, rotation, scale if provided
    for vector_param in ["position", "rotation", "scale"]:
        if vector_param in params:
            vector_value = params[vector_param]
            if not isinstance(vector_value, list) or len(vector_value) != 3:
                raise ValidationError(
                    f"{vector_param.capitalize()} must be a list of 3 numbers [x, y, z]",
                    parameter=vector_param,
                    value=vector_value
                )
            if not all(isinstance(x, (int, float)) for x in vector_value):
                raise ValidationError(
                    f"{vector_param.capitalize()} values must be numbers",
                    parameter=vector_param,
                    value=vector_value
                )

    # Validate component lists
    for component_list_param in ["componentsToAdd", "componentsToRemove"]:
        if component_list_param in params:
            component_list = params[component_list_param]
            if not isinstance(component_list, list):
                raise ValidationError(
                    f"{component_list_param} must be a list of component names",
                    parameter=component_list_param.replace("componentsTo", "components_to_").lower(),
                    value=component_list
                )
            if not all(isinstance(comp, str) for comp in component_list):
                raise ValidationError(
                    f"All component names in {component_list_param} must be strings",
                    parameter=component_list_param.replace("componentsTo", "components_to_").lower(),
                    value=component_list
                )

    # Log validation success
    enhanced_logger.info(
        f"GameObject action validation passed for '{action}'",
        context=log_context,
        validated_params=list(params.keys())
    )