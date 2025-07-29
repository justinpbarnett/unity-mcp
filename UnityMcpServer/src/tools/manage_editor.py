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

def register_manage_editor_tools(mcp: FastMCP):
    """Register all editor management tools with the MCP server."""

    @mcp.tool()
    def manage_editor(
        ctx: Context,
        action: str,
        wait_for_completion: bool = None,
        # --- Parameters for specific actions ---
        tool_name: str = None,
        tag_name: str = None,
        layer_name: str = None,
    ) -> Dict[str, Any]:
        """Controls and queries the Unity editor's state and settings.

        Args:
            action: Operation (e.g., 'play', 'pause', 'get_state', 'set_active_tool', 'add_tag').
            wait_for_completion: Optional. If True, waits for certain actions.
            Action-specific arguments (e.g., tool_name, tag_name, layer_name).

        Returns:
            Dictionary with operation results ('success', 'message', 'data').
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Create log context
        log_context = LogContext(
            operation=f"manage_editor.{action}",
            tool_name="manage_editor",
            request_id=request_id
        )

        try:
            # Log tool call
            enhanced_logger.log_tool_call(
                "manage_editor",
                action,
                {
                    "wait_for_completion": wait_for_completion,
                    "tool_name": tool_name,
                    "tag_name": tag_name,
                    "layer_name": layer_name
                },
                request_id
            )

            # Validate input parameters
            parameters = {
                "action": action,
                "wait_for_completion": wait_for_completion,
                "tool_name": tool_name,
                "tag_name": tag_name,
                "layer_name": layer_name
            }

            validate_tool_parameters("manage_editor", parameters)

            # Execute the operation with timeout
            result = _execute_editor_operation(
                action, wait_for_completion, tool_name, tag_name, layer_name, log_context
            )

            # Log successful result
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_editor", action, True,
                result_summary=f"Editor {action} completed",
                request_id=request_id,
                duration=duration
            )

            return result

        except ValidationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_editor", action, False,
                error_message=f"Validation error: {e.message}",
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except UnityOperationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_editor", action, False,
                error_message=e.message,
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except Exception as e:
            duration = time.time() - start_time
            enhanced_logger.error(
                f"Unexpected error in manage_editor.{action}",
                context=log_context,
                exception=e,
                parameters=parameters
            )
            enhanced_logger.log_tool_result(
                "manage_editor", action, False,
                error_message=f"Internal error: {str(e)}",
                request_id=request_id,
                duration=duration
            )

            # Create generic error response for unexpected errors
            from exceptions import UnityMcpError, ErrorCategory, ErrorSeverity
            error = UnityMcpError(
                f"Unexpected error in editor management: {str(e)}",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH,
                context={"original_error": str(e), "action": action}
            )
            return create_error_response(error)


@with_timeout(OperationType.EDITOR_OPERATION, "editor_operation")
def _execute_editor_operation(
    action: str,
    wait_for_completion: Optional[bool],
    tool_name: Optional[str],
    tag_name: Optional[str],
    layer_name: Optional[str],
    log_context: LogContext
) -> Dict[str, Any]:
    """Execute editor operation with proper error handling and logging."""

    enhanced_logger.info(
        f"Executing editor operation: {action}",
        context=log_context,
        wait_for_completion=wait_for_completion,
        tool_name=tool_name,
        tag_name=tag_name,
        layer_name=layer_name
    )

    try:
        # Prepare parameters, removing None values
        params = {
            "action": action,
            "waitForCompletion": wait_for_completion,
            "toolName": tool_name,
            "tagName": tag_name,
            "layerName": layer_name
        }
        params = {k: v for k, v in params.items() if v is not None}

        # Validate action-specific requirements
        _validate_editor_action(action, params, log_context)

        # Get connection and send command
        connection = get_enhanced_unity_connection()

        enhanced_logger.info(
            "Sending editor command to Unity",
            context=log_context,
            command_params=list(params.keys())
        )

        response = connection.send_command("manage_editor", params)

        # Process response
        if response.get("success"):
            result_data = response.get("data", {})

            enhanced_logger.info(
                f"Editor operation '{action}' completed successfully",
                context=log_context,
                response_message=response.get("message", ""),
                result_keys=list(result_data.keys()) if result_data else []
            )

            return {
                "success": True,
                "message": response.get("message", "Editor operation completed successfully."),
                "data": result_data
            }
        else:
            error_message = response.get("error", "Unknown Unity error occurred during editor management.")
            enhanced_logger.error(
                f"Unity editor operation failed: {error_message}",
                context=log_context,
                unity_error=error_message
            )

            raise UnityOperationError(
                error_message,
                operation=f"manage_editor.{action}",
                unity_error=error_message,
                context={"action": action, "params": params}
            )

    except Exception as e:
        if isinstance(e, (UnityOperationError, ValidationError)):
            raise  # Re-raise our custom exceptions

        # Wrap unexpected exceptions
        enhanced_logger.error(
            f"Unexpected error during editor operation",
            context=log_context,
            exception=e,
            action=action
        )

        raise UnityOperationError(
            f"Editor operation failed: {str(e)}",
            operation=f"manage_editor.{action}",
            context={"original_error": str(e), "action": action}
        )


def _validate_editor_action(action: str, params: Dict[str, Any], log_context: LogContext) -> None:
    """Validate action-specific requirements for editor operations."""

    # Action-specific validation
    if action == "set_active_tool" and not params.get("toolName"):
        raise ValidationError(
            "tool_name is required for set_active_tool action",
            parameter="tool_name",
            context={"action": action}
        )

    if action == "add_tag" and not params.get("tagName"):
        raise ValidationError(
            "tag_name is required for add_tag action",
            parameter="tag_name",
            context={"action": action}
        )

    if action == "remove_tag" and not params.get("tagName"):
        raise ValidationError(
            "tag_name is required for remove_tag action",
            parameter="tag_name",
            context={"action": action}
        )

    if action == "add_layer" and not params.get("layerName"):
        raise ValidationError(
            "layer_name is required for add_layer action",
            parameter="layer_name",
            context={"action": action}
        )

    if action == "remove_layer" and not params.get("layerName"):
        raise ValidationError(
            "layer_name is required for remove_layer action",
            parameter="layer_name",
            context={"action": action}
        )

    # Log validation success
    enhanced_logger.info(
        f"Editor action validation passed for '{action}'",
        context=log_context,
        validated_params=list(params.keys())
    )