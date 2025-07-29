from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Any, Optional
import time
import uuid

# Import enhanced infrastructure
from enhanced_connection import get_enhanced_unity_connection
from exceptions import ValidationError, UnityOperationError, create_error_response
from enhanced_logging import enhanced_logger, LogContext
from timeout_manager import with_timeout, OperationType
from validation import validate_tool_parameters
from config import config

def register_manage_scene_tools(mcp: FastMCP):
    """Register all scene management tools with the MCP server."""

    @mcp.tool()
    def manage_scene(
        ctx: Context,
        action: str,
        name: str,
        path: str,
        build_index: int,
    ) -> Dict[str, Any]:
        """Manages Unity scenes (load, save, create, get hierarchy, etc.).

        Args:
            action: Operation (e.g., 'load', 'save', 'create', 'get_hierarchy').
            name: Scene name (no extension) for create/load/save.
            path: Asset path for scene operations (default: "Assets/").
            build_index: Build index for load/build settings actions.

        Returns:
            Dictionary with results ('success', 'message', 'data').
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Create log context
        log_context = LogContext(
            operation=f"manage_scene.{action}",
            tool_name="manage_scene",
            request_id=request_id
        )

        try:
            # Log tool call
            enhanced_logger.log_tool_call(
                "manage_scene",
                action,
                {
                    "name": name,
                    "path": path,
                    "build_index": build_index
                },
                request_id
            )

            # Validate input parameters
            parameters = {
                "action": action,
                "name": name,
                "path": path,
                "build_index": build_index
            }

            validate_tool_parameters("manage_scene", parameters)

            # Execute the operation with timeout
            result = _execute_scene_operation(
                action, name, path, build_index, log_context
            )

            # Log successful result
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_scene", action, True,
                result_summary=f"Scene '{name}' {action} completed",
                request_id=request_id,
                duration=duration
            )

            return result

        except ValidationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_scene", action, False,
                error_message=f"Validation error: {e.message}",
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except UnityOperationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_scene", action, False,
                error_message=e.message,
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except Exception as e:
            duration = time.time() - start_time
            enhanced_logger.error(
                f"Unexpected error in manage_scene.{action}",
                context=log_context,
                exception=e,
                parameters=parameters
            )
            enhanced_logger.log_tool_result(
                "manage_scene", action, False,
                error_message=f"Internal error: {str(e)}",
                request_id=request_id,
                duration=duration
            )

            # Create generic error response for unexpected errors
            from exceptions import UnityMcpError, ErrorCategory, ErrorSeverity
            error = UnityMcpError(
                f"Unexpected error in scene management: {str(e)}",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH,
                context={"original_error": str(e), "action": action, "scene_name": name}
            )
            return create_error_response(error)


@with_timeout(OperationType.SCENE_OPERATION, "scene_operation")
def _execute_scene_operation(
    action: str,
    name: str,
    path: str,
    build_index: int,
    log_context: LogContext
) -> Dict[str, Any]:
    """Execute scene operation with proper error handling and logging."""

    enhanced_logger.info(
        f"Executing scene operation: {action}",
        context=log_context,
        scene_name=name,
        scene_path=path,
        build_index=build_index
    )

    try:
        # Prepare parameters for Unity
        params = {
            "action": action,
            "name": name,
            "path": path,
            "buildIndex": build_index
        }

        # Remove None values to avoid sending null
        params = {k: v for k, v in params.items() if v is not None}

        # Validate action-specific requirements
        _validate_scene_action(action, params, log_context)

        # Get connection and send command
        connection = get_enhanced_unity_connection()

        enhanced_logger.info(
            "Sending scene command to Unity",
            context=log_context,
            command_params=list(params.keys())
        )

        response = connection.send_command("manage_scene", params)

        # Process response from Unity
        if response.get("success"):
            result_data = response.get("data", {})

            enhanced_logger.info(
                f"Scene operation '{action}' completed successfully",
                context=log_context,
                response_message=response.get("message", ""),
                result_keys=list(result_data.keys()) if result_data else []
            )

            return {
                "success": True,
                "message": response.get("message", "Scene operation completed successfully."),
                "data": result_data
            }
        else:
            error_message = response.get("error", "Unknown Unity error occurred during scene management.")
            enhanced_logger.error(
                f"Unity scene operation failed: {error_message}",
                context=log_context,
                unity_error=error_message
            )

            raise UnityOperationError(
                error_message,
                operation=f"manage_scene.{action}",
                unity_error=error_message,
                context={"scene_name": name, "scene_path": path, "build_index": build_index}
            )

    except Exception as e:
        if isinstance(e, (UnityOperationError, ValidationError)):
            raise  # Re-raise our custom exceptions

        # Wrap unexpected exceptions
        enhanced_logger.error(
            f"Unexpected error during scene operation",
            context=log_context,
            exception=e,
            scene_name=name,
            action=action
        )

        raise UnityOperationError(
            f"Scene operation failed: {str(e)}",
            operation=f"manage_scene.{action}",
            context={"original_error": str(e), "scene_name": name}
        )


def _validate_scene_action(action: str, params: Dict[str, Any], log_context: LogContext) -> None:
    """Validate action-specific requirements for scene operations."""

    # Action-specific validation
    if action in ["load", "save", "create"] and not params.get("name"):
        raise ValidationError(
            f"Scene name is required for {action} action",
            parameter="name",
            context={"action": action}
        )

    if action in ["create", "save"] and not params.get("path"):
        raise ValidationError(
            f"Scene path is required for {action} action",
            parameter="path",
            context={"action": action}
        )

    if action == "load" and params.get("buildIndex") is not None:
        build_index = params.get("buildIndex")
        if not isinstance(build_index, int) or build_index < 0:
            raise ValidationError(
                "Build index must be a non-negative integer",
                parameter="build_index",
                value=build_index,
                context={"action": action}
            )

    # Validate scene name format
    scene_name = params.get("name")
    if scene_name and not isinstance(scene_name, str):
        raise ValidationError(
            "Scene name must be a string",
            parameter="name",
            value=scene_name
        )

    if scene_name and len(scene_name.strip()) == 0:
        raise ValidationError(
            "Scene name cannot be empty",
            parameter="name",
            value=scene_name
        )

    # Validate path format
    scene_path = params.get("path")
    if scene_path and not isinstance(scene_path, str):
        raise ValidationError(
            "Scene path must be a string",
            parameter="path",
            value=scene_path
        )

    # Log validation success
    enhanced_logger.info(
        f"Scene action validation passed for '{action}'",
        context=log_context,
        validated_params=list(params.keys())
    )