from mcp.server.fastmcp import FastMCP, Context
from typing import Dict, Any, Optional
import os
import base64
import time
import uuid

# Import enhanced infrastructure
from enhanced_connection import get_enhanced_unity_connection
from exceptions import ValidationError, UnityOperationError, ResourceError, create_error_response
from enhanced_logging import enhanced_logger, LogContext
from timeout_manager import with_timeout, OperationType
from validation import validate_tool_parameters
from config import config

def register_manage_shader_tools(mcp: FastMCP):
    """Register all shader script management tools with the MCP server."""

    @mcp.tool()
    def manage_shader(
        ctx: Context,
        action: str,
        name: str,
        path: str,
        contents: str,
    ) -> Dict[str, Any]:
        """Manages shader scripts in Unity (create, read, update, delete).

        Args:
            action: Operation ('create', 'read', 'update', 'delete').
            name: Shader name (no .shader extension).
            path: Asset path (default: "Assets/").
            contents: Shader code for 'create'/'update'.

        Returns:
            Dictionary with results ('success', 'message', 'data').
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Create log context
        log_context = LogContext(
            operation=f"manage_shader.{action}",
            tool_name="manage_shader",
            request_id=request_id
        )

        try:
            # Log tool call
            enhanced_logger.log_tool_call(
                "manage_shader",
                action,
                {
                    "name": name,
                    "path": path,
                    "has_contents": contents is not None
                },
                request_id
            )

            # Validate input parameters
            parameters = {
                "action": action,
                "name": name,
                "path": path,
                "contents": contents
            }

            validate_tool_parameters("manage_shader", parameters)

            # Execute the operation with timeout
            result = _execute_shader_operation(
                action, name, path, contents, log_context
            )

            # Log successful result
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_shader", action, True,
                result_summary=f"Shader '{name}' {action} completed",
                request_id=request_id,
                duration=duration
            )

            return result

        except ValidationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_shader", action, False,
                error_message=f"Validation error: {e.message}",
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except (UnityOperationError, ResourceError) as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_shader", action, False,
                error_message=e.message,
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except Exception as e:
            duration = time.time() - start_time
            enhanced_logger.error(
                f"Unexpected error in manage_shader.{action}",
                context=log_context,
                exception=e,
                parameters=parameters
            )
            enhanced_logger.log_tool_result(
                "manage_shader", action, False,
                error_message=f"Internal error: {str(e)}",
                request_id=request_id,
                duration=duration
            )

            # Create generic error response for unexpected errors
            from exceptions import UnityMcpError, ErrorCategory, ErrorSeverity
            error = UnityMcpError(
                f"Unexpected error in shader management: {str(e)}",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH,
                context={"original_error": str(e), "action": action, "shader_name": name}
            )
            return create_error_response(error)


@with_timeout(OperationType.SHADER_OPERATION, "shader_operation")
def _execute_shader_operation(
    action: str,
    name: str,
    path: str,
    contents: Optional[str],
    log_context: LogContext
) -> Dict[str, Any]:
    """Execute shader operation with proper error handling and logging."""

    enhanced_logger.info(
        f"Executing shader operation: {action}",
        context=log_context,
        shader_name=name,
        shader_path=path
    )

    try:
        # Prepare parameters for Unity
        params = {
            "action": action,
            "name": name,
            "path": path,
        }

        # Handle contents encoding for safe transmission
        if contents is not None:
            if action in ['create', 'update']:
                # Validate contents for basic syntax issues
                _validate_shader_contents(contents, log_context)

                # Encode content for safer transmission
                try:
                    encoded_contents = base64.b64encode(contents.encode('utf-8')).decode('utf-8')
                    params["encodedContents"] = encoded_contents
                    params["contentsEncoded"] = True

                    enhanced_logger.info(
                        "Shader contents encoded for transmission",
                        context=log_context,
                        content_size=len(contents),
                        encoded_size=len(encoded_contents)
                    )
                except Exception as e:
                    raise ResourceError(
                        f"Failed to encode shader contents: {str(e)}",
                        resource_type="shader_content",
                        context={"encoding_error": str(e)}
                    )
            else:
                params["contents"] = contents

        # Remove None values to avoid sending null
        params = {k: v for k, v in params.items() if v is not None}

        # Get connection and send command
        connection = get_enhanced_unity_connection()

        enhanced_logger.info(
            "Sending shader command to Unity",
            context=log_context,
            command_params=list(params.keys())
        )

        response = connection.send_command("manage_shader", params)

        # Process response from Unity
        if response.get("success"):
            result_data = response.get("data", {})

            # Decode base64 encoded content if present
            if result_data.get("contentsEncoded"):
                try:
                    decoded_contents = base64.b64decode(result_data["encodedContents"]).decode('utf-8')
                    result_data["contents"] = decoded_contents
                    # Clean up encoded fields
                    result_data.pop("encodedContents", None)
                    result_data.pop("contentsEncoded", None)

                    enhanced_logger.info(
                        "Shader contents decoded from response",
                        context=log_context,
                        decoded_size=len(decoded_contents)
                    )
                except Exception as e:
                    enhanced_logger.warning(
                        "Failed to decode shader contents from response",
                        context=log_context,
                        error=str(e)
                    )

            enhanced_logger.info(
                f"Shader operation '{action}' completed successfully",
                context=log_context,
                response_message=response.get("message", "")
            )

            return {
                "success": True,
                "message": response.get("message", "Shader operation completed successfully."),
                "data": result_data
            }
        else:
            error_message = response.get("error", "Unknown Unity error occurred.")
            enhanced_logger.error(
                f"Unity shader operation failed: {error_message}",
                context=log_context,
                unity_error=error_message
            )

            raise UnityOperationError(
                error_message,
                operation=f"manage_shader.{action}",
                unity_error=error_message,
                context={"shader_name": name, "shader_path": path}
            )

    except Exception as e:
        if isinstance(e, (UnityOperationError, ResourceError, ValidationError)):
            raise  # Re-raise our custom exceptions

        # Wrap unexpected exceptions
        enhanced_logger.error(
            f"Unexpected error during shader operation",
            context=log_context,
            exception=e,
            shader_name=name,
            action=action
        )

        raise UnityOperationError(
            f"Shader operation failed: {str(e)}",
            operation=f"manage_shader.{action}",
            context={"original_error": str(e), "shader_name": name}
        )


def _validate_shader_contents(contents: str, log_context: LogContext) -> None:
    """Validate shader contents for basic issues."""
    if not contents or not contents.strip():
        raise ValidationError(
            "Shader contents cannot be empty",
            parameter="contents",
            value="<empty>"
        )

    # Basic shader syntax validation
    if "Shader" not in contents:
        enhanced_logger.warning(
            "Shader contents missing 'Shader' declaration",
            context=log_context
        )

    # Check for common shader structure
    if "Properties" not in contents and "SubShader" not in contents:
        enhanced_logger.warning(
            "Shader contents may be missing Properties or SubShader blocks",
            context=log_context
        )

    # Check for size limits
    if len(contents) > 1024 * 1024:  # 1MB limit
        raise ValidationError(
            "Shader contents too large (max 1MB)",
            parameter="contents",
            context={"size": len(contents), "max_size": 1024 * 1024}
        )

    enhanced_logger.info(
        "Shader contents validation passed",
        context=log_context,
        content_size=len(contents)
    )