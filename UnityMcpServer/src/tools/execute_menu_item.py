"""
Defines the execute_menu_item tool for running Unity Editor menu commands.
"""
from typing import Dict, Any, Optional
import time
import uuid

from mcp.server.fastmcp import FastMCP, Context

# Import enhanced infrastructure
from enhanced_connection import get_enhanced_unity_connection
from exceptions import ValidationError, UnityOperationError, create_error_response
from enhanced_logging import enhanced_logger, LogContext
from timeout_manager import with_timeout, OperationType
from validation import validate_tool_parameters
from config import config

def register_execute_menu_item_tools(mcp: FastMCP):
    """Registers the execute_menu_item tool with the MCP server."""

    @mcp.tool()
    async def execute_menu_item(
        ctx: Context,
        menu_path: str,
        action: str = 'execute',
        parameters: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Executes a Unity Editor menu item via its path (e.g., "File/Save Project").

        Args:
            ctx: The MCP context.
            menu_path: The full path of the menu item to execute.
            action: The operation to perform (default: 'execute').
            parameters: Optional parameters for the menu item (rarely used).

        Returns:
            A dictionary indicating success or failure, with optional message/error.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Set default action
        action = action.lower() if action else 'execute'

        # Create log context
        log_context = LogContext(
            operation=f"execute_menu_item.{action}",
            tool_name="execute_menu_item",
            request_id=request_id
        )

        try:
            # Log tool call
            enhanced_logger.log_tool_call(
                "execute_menu_item",
                action,
                {
                    "menu_path": menu_path,
                    "has_parameters": parameters is not None
                },
                request_id
            )

            # Validate input parameters
            parameters_dict = {
                "menu_path": menu_path,
                "action": action,
                "parameters": parameters
            }

            validate_tool_parameters("execute_menu_item", parameters_dict)

            # Execute the operation with timeout
            result = await _execute_menu_item_operation(
                menu_path, action, parameters, log_context
            )

            # Log successful result
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "execute_menu_item", action, True,
                result_summary=f"Menu item '{menu_path}' executed",
                request_id=request_id,
                duration=duration
            )

            return result

        except ValidationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "execute_menu_item", action, False,
                error_message=f"Validation error: {e.message}",
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except UnityOperationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "execute_menu_item", action, False,
                error_message=e.message,
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except Exception as e:
            duration = time.time() - start_time
            enhanced_logger.error(
                f"Unexpected error in execute_menu_item.{action}",
                context=log_context,
                exception=e,
                parameters=parameters_dict
            )
            enhanced_logger.log_tool_result(
                "execute_menu_item", action, False,
                error_message=f"Internal error: {str(e)}",
                request_id=request_id,
                duration=duration
            )

            # Create generic error response for unexpected errors
            from exceptions import UnityMcpError, ErrorCategory, ErrorSeverity
            error = UnityMcpError(
                f"Unexpected error in menu item execution: {str(e)}",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH,
                context={"original_error": str(e), "action": action, "menu_path": menu_path}
            )
            return create_error_response(error)


@with_timeout(OperationType.MENU_OPERATION, "menu_operation")
async def _execute_menu_item_operation(
    menu_path: str,
    action: str,
    parameters: Optional[Dict[str, Any]],
    log_context: LogContext
) -> Dict[str, Any]:
    """Execute menu item operation with proper error handling and logging."""

    enhanced_logger.info(
        f"Executing menu item operation: {action}",
        context=log_context,
        menu_path=menu_path,
        has_parameters=parameters is not None
    )

    try:
        # Prepare parameters for the C# handler
        params_dict = {
            "action": action,
            "menuPath": menu_path,
            "parameters": parameters if parameters else {},
        }

        # Remove None values
        params_dict = {k: v for k, v in params_dict.items() if v is not None}

        if "parameters" not in params_dict:
            params_dict["parameters"] = {}  # Ensure parameters dict exists

        # Validate action-specific requirements
        _validate_menu_item_action(action, params_dict, log_context)

        # Get connection and send command
        connection = get_enhanced_unity_connection()

        enhanced_logger.info(
            "Sending menu item command to Unity",
            context=log_context,
            command_params=list(params_dict.keys())
        )

        # Use asyncio to run the synchronous operation in a thread pool
        import asyncio
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,  # Use default executor
            connection.send_command,
            "execute_menu_item",
            params_dict
        )

        # Process response from Unity
        if response.get("success"):
            result_data = response.get("data", {})

            enhanced_logger.info(
                f"Menu item operation '{action}' completed successfully",
                context=log_context,
                response_message=response.get("message", ""),
                result_keys=list(result_data.keys()) if result_data else []
            )

            return {
                "success": True,
                "message": response.get("message", "Menu item executed successfully."),
                "data": result_data
            }
        else:
            error_message = response.get("error", "Unknown Unity error occurred during menu item execution.")
            enhanced_logger.error(
                f"Unity menu item operation failed: {error_message}",
                context=log_context,
                unity_error=error_message
            )

            raise UnityOperationError(
                error_message,
                operation=f"execute_menu_item.{action}",
                unity_error=error_message,
                context={"menu_path": menu_path, "action": action}
            )

    except Exception as e:
        if isinstance(e, (UnityOperationError, ValidationError)):
            raise  # Re-raise our custom exceptions

        # Wrap unexpected exceptions
        enhanced_logger.error(
            f"Unexpected error during menu item operation",
            context=log_context,
            exception=e,
            menu_path=menu_path,
            action=action
        )

        raise UnityOperationError(
            f"Menu item operation failed: {str(e)}",
            operation=f"execute_menu_item.{action}",
            context={"original_error": str(e), "menu_path": menu_path}
        )


def _validate_menu_item_action(action: str, params: Dict[str, Any], log_context: LogContext) -> None:
    """Validate action-specific requirements for menu item operations."""

    # Validate action
    valid_actions = ["execute", "get_available_menus"]
    if action not in valid_actions:
        raise ValidationError(
            f"Invalid action '{action}'. Valid actions are: {', '.join(valid_actions)}",
            parameter="action",
            value=action
        )

    # Validate menu path
    menu_path = params.get("menuPath")
    if not menu_path or not isinstance(menu_path, str):
        raise ValidationError(
            "Menu path is required and must be a non-empty string",
            parameter="menu_path",
            value=menu_path
        )

    if len(menu_path.strip()) == 0:
        raise ValidationError(
            "Menu path cannot be empty",
            parameter="menu_path",
            value=menu_path
        )

    # Basic menu path format validation
    if action == "execute":
        if "/" not in menu_path:
            enhanced_logger.warning(
                "Menu path may be invalid - typically contains '/' separators",
                context=log_context,
                menu_path=menu_path
            )

        # Check for common invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in menu_path for char in invalid_chars):
            raise ValidationError(
                f"Menu path contains invalid characters: {invalid_chars}",
                parameter="menu_path",
                value=menu_path
            )

    # Validate parameters if provided
    parameters = params.get("parameters")
    if parameters and not isinstance(parameters, dict):
        raise ValidationError(
            "Parameters must be a dictionary",
            parameter="parameters",
            value=type(parameters).__name__
        )

    # Log validation success
    enhanced_logger.info(
        f"Menu item action validation passed for '{action}'",
        context=log_context,
        validated_params=list(params.keys())
    )