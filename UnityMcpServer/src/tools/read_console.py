"""
Defines the read_console tool for accessing Unity Editor console messages.
"""
from typing import List, Dict, Any, Optional
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

def register_read_console_tools(mcp: FastMCP):
    """Registers the read_console tool with the MCP server."""

    @mcp.tool()
    def read_console(
        ctx: Context,
        action: str = None,
        types: List[str] = None,
        count: int = None,
        filter_text: str = None,
        since_timestamp: str = None,
        format: str = None,
        include_stacktrace: bool = None
    ) -> Dict[str, Any]:
        """Gets messages from or clears the Unity Editor console.

        Args:
            ctx: The MCP context.
            action: Operation ('get' or 'clear').
            types: Message types to get ('error', 'warning', 'log', 'all').
            count: Max messages to return.
            filter_text: Text filter for messages.
            since_timestamp: Get messages after this timestamp (ISO 8601).
            format: Output format ('plain', 'detailed', 'json').
            include_stacktrace: Include stack traces in output.

        Returns:
            Dictionary with results. For 'get', includes 'data' (messages).
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Set defaults if values are None
        action = action if action is not None else 'get'
        types = types if types is not None else ['error', 'warning', 'log']
        format = format if format is not None else 'detailed'
        include_stacktrace = include_stacktrace if include_stacktrace is not None else True

        # Create log context
        log_context = LogContext(
            operation=f"read_console.{action}",
            tool_name="read_console",
            request_id=request_id
        )

        try:
            # Log tool call
            enhanced_logger.log_tool_call(
                "read_console",
                action,
                {
                    "types": types,
                    "count": count,
                    "filter_text": filter_text,
                    "format": format,
                    "include_stacktrace": include_stacktrace
                },
                request_id
            )

            # Validate input parameters
            parameters = {
                "action": action,
                "types": types,
                "count": count,
                "filter_text": filter_text,
                "since_timestamp": since_timestamp,
                "format": format,
                "include_stacktrace": include_stacktrace
            }

            validate_tool_parameters("read_console", parameters)

            # Execute the operation with timeout
            result = _execute_console_operation(
                action, types, count, filter_text, since_timestamp, format,
                include_stacktrace, log_context
            )

            # Log successful result
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "read_console", action, True,
                result_summary=f"Console {action} completed",
                request_id=request_id,
                duration=duration
            )

            return result

        except ValidationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "read_console", action, False,
                error_message=f"Validation error: {e.message}",
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except UnityOperationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "read_console", action, False,
                error_message=e.message,
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except Exception as e:
            duration = time.time() - start_time
            enhanced_logger.error(
                f"Unexpected error in read_console.{action}",
                context=log_context,
                exception=e,
                parameters=parameters
            )
            enhanced_logger.log_tool_result(
                "read_console", action, False,
                error_message=f"Internal error: {str(e)}",
                request_id=request_id,
                duration=duration
            )

            # Create generic error response for unexpected errors
            from exceptions import UnityMcpError, ErrorCategory, ErrorSeverity
            error = UnityMcpError(
                f"Unexpected error in console management: {str(e)}",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH,
                context={"original_error": str(e), "action": action}
            )
            return create_error_response(error)


@with_timeout(OperationType.CONSOLE_OPERATION, "console_operation")
def _execute_console_operation(
    action: str,
    types: List[str],
    count: Optional[int],
    filter_text: Optional[str],
    since_timestamp: Optional[str],
    format: str,
    include_stacktrace: bool,
    log_context: LogContext
) -> Dict[str, Any]:
    """Execute console operation with proper error handling and logging."""

    enhanced_logger.info(
        f"Executing console operation: {action}",
        context=log_context,
        message_types=types,
        count=count,
        format=format
    )

    try:
        # Normalize action if it's a string
        if isinstance(action, str):
            action = action.lower()

        # Prepare parameters for the C# handler
        params_dict = {
            "action": action,
            "types": types,
            "count": count,
            "filterText": filter_text,
            "sinceTimestamp": since_timestamp,
            "format": format.lower() if isinstance(format, str) else format,
            "includeStacktrace": include_stacktrace
        }

        # Remove None values unless it's 'count' (as None might mean 'all')
        params_dict = {k: v for k, v in params_dict.items() if v is not None or k == 'count'}

        # Add count back if it was None, explicitly sending null might be important for C# logic
        if 'count' not in params_dict:
             params_dict['count'] = None

        # Validate action-specific requirements
        _validate_console_action(action, params_dict, log_context)

        # Get connection and send command
        connection = get_enhanced_unity_connection()

        enhanced_logger.info(
            "Sending console command to Unity",
            context=log_context,
            command_params=list(params_dict.keys())
        )

        response = connection.send_command("read_console", params_dict)

        # Process response from Unity
        if response.get("success"):
            result_data = response.get("data", {})

            # Log message count if available
            if isinstance(result_data, dict) and "messages" in result_data:
                message_count = len(result_data["messages"]) if isinstance(result_data["messages"], list) else 0
                enhanced_logger.info(
                    f"Console operation '{action}' completed successfully",
                    context=log_context,
                    message_count=message_count,
                    response_message=response.get("message", "")
                )
            else:
                enhanced_logger.info(
                    f"Console operation '{action}' completed successfully",
                    context=log_context,
                    response_message=response.get("message", "")
                )

            return {
                "success": True,
                "message": response.get("message", "Console operation completed successfully."),
                "data": result_data
            }
        else:
            error_message = response.get("error", "Unknown Unity error occurred during console operation.")
            enhanced_logger.error(
                f"Unity console operation failed: {error_message}",
                context=log_context,
                unity_error=error_message
            )

            raise UnityOperationError(
                error_message,
                operation=f"read_console.{action}",
                unity_error=error_message,
                context={"action": action, "types": types}
            )

    except Exception as e:
        if isinstance(e, (UnityOperationError, ValidationError)):
            raise  # Re-raise our custom exceptions

        # Wrap unexpected exceptions
        enhanced_logger.error(
            f"Unexpected error during console operation",
            context=log_context,
            exception=e,
            action=action
        )

        raise UnityOperationError(
            f"Console operation failed: {str(e)}",
            operation=f"read_console.{action}",
            context={"original_error": str(e), "action": action}
        )


def _validate_console_action(action: str, params: Dict[str, Any], log_context: LogContext) -> None:
    """Validate action-specific requirements for console operations."""

    # Validate action
    valid_actions = ["get", "clear"]
    if action not in valid_actions:
        raise ValidationError(
            f"Invalid action '{action}'. Valid actions are: {', '.join(valid_actions)}",
            parameter="action",
            value=action
        )

    # Validate types
    types = params.get("types", [])
    if types:
        valid_types = ["error", "warning", "log", "all"]
        invalid_types = [t for t in types if t not in valid_types]
        if invalid_types:
            raise ValidationError(
                f"Invalid message types: {invalid_types}. Valid types are: {', '.join(valid_types)}",
                parameter="types",
                value=types
            )

    # Validate count
    count = params.get("count")
    if count is not None and (not isinstance(count, int) or count <= 0):
        raise ValidationError(
            "Count must be a positive integer",
            parameter="count",
            value=count
        )

    # Validate format
    format_value = params.get("format")
    if format_value:
        valid_formats = ["plain", "detailed", "json"]
        if format_value not in valid_formats:
            raise ValidationError(
                f"Invalid format '{format_value}'. Valid formats are: {', '.join(valid_formats)}",
                parameter="format",
                value=format_value
            )

    # Log validation success
    enhanced_logger.info(
        f"Console action validation passed for '{action}'",
        context=log_context,
        validated_params=list(params.keys())
    )