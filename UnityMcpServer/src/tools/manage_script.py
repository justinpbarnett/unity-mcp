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
from error_recovery import error_recovery_manager

def register_manage_script_tools(mcp: FastMCP):
    """Register all script management tools with the MCP server."""

    @mcp.tool()
    def manage_script(
        ctx: Context,
        action: str,
        name: str,
        path: str,
        contents: str,
        script_type: str,
        namespace: str
    ) -> Dict[str, Any]:
        """Manages C# scripts in Unity (create, read, update, delete).
        Make reference variables public for easier access in the Unity Editor.

        Args:
            action: Operation ('create', 'read', 'update', 'delete').
            name: Script name (no .cs extension).
            path: Asset path (default: "Assets/").
            contents: C# code for 'create'/'update'.
            script_type: Type hint (e.g., 'MonoBehaviour').
            namespace: Script namespace.

        Returns:
            Dictionary with results ('success', 'message', 'data').
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Create log context
        log_context = LogContext(
            operation=f"manage_script.{action}",
            tool_name="manage_script",
            request_id=request_id
        )

        try:
            # Log tool call
            enhanced_logger.log_tool_call(
                "manage_script",
                action,
                {
                    "name": name,
                    "path": path,
                    "script_type": script_type,
                    "namespace": namespace,
                    "has_contents": contents is not None
                },
                request_id
            )

            # Validate input parameters
            parameters = {
                "action": action,
                "name": name,
                "path": path,
                "contents": contents,
                "script_type": script_type,
                "namespace": namespace
            }

            validate_tool_parameters("manage_script", parameters)

            # Execute the operation with timeout
            result = _execute_script_operation(
                action, name, path, contents, script_type, namespace, log_context
            )

            # Log successful result
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_script", action, True,
                result_summary=f"Script '{name}' {action} completed",
                request_id=request_id,
                duration=duration
            )

            return result

        except ValidationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_script", action, False,
                error_message=f"Validation error: {e.message}",
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except (UnityOperationError, ResourceError) as e:
            duration = time.time() - start_time

            # Attempt error recovery
            recovery_result = await error_recovery_manager.handle_error(
                e, log_context, {"action": action, "name": name, "path": path}
            )

            if recovery_result["success"]:
                enhanced_logger.log_tool_result(
                    "manage_script", action, True,
                    result_summary=f"Script '{name}' {action} completed after recovery",
                    request_id=request_id,
                    duration=duration,
                    recovery_used=True
                )
                return {
                    "success": True,
                    "message": recovery_result["message"],
                    "data": recovery_result.get("data", {}),
                    "recovery_info": {
                        "recovery_applied": True,
                        "original_error": e.message,
                        "recovery_method": recovery_result.get("data", {}).get("recovery_method", "unknown")
                    }
                }
            else:
                enhanced_logger.log_tool_result(
                    "manage_script", action, False,
                    error_message=f"Error and recovery failed: {e.message}",
                    request_id=request_id,
                    duration=duration,
                    recovery_attempted=True,
                    recovery_failed=True
                )

                # Return enhanced error response with recovery information
                error_response = create_error_response(e)
                error_response["recovery_info"] = {
                    "recovery_attempted": True,
                    "recovery_successful": False,
                    "recovery_message": recovery_result.get("message", "Recovery failed")
                }
                return error_response

        except Exception as e:
            duration = time.time() - start_time
            enhanced_logger.error(
                f"Unexpected error in manage_script.{action}",
                context=log_context,
                exception=e,
                parameters=parameters
            )
            enhanced_logger.log_tool_result(
                "manage_script", action, False,
                error_message=f"Internal error: {str(e)}",
                request_id=request_id,
                duration=duration
            )

            # Create generic error response for unexpected errors
            from exceptions import UnityMcpError, ErrorCategory, ErrorSeverity
            error = UnityMcpError(
                f"Unexpected error in script management: {str(e)}",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH,
                context={"original_error": str(e), "action": action, "name": name}
            )
            return create_error_response(error)


@with_timeout(OperationType.SCRIPT_OPERATION, "script_operation")
def _execute_script_operation(
    action: str,
    name: str,
    path: str,
    contents: Optional[str],
    script_type: str,
    namespace: str,
    log_context: LogContext
) -> Dict[str, Any]:
    """Execute script operation with proper error handling and logging."""

    enhanced_logger.info(
        f"Executing script operation: {action}",
        context=log_context,
        script_name=name,
        script_path=path,
        script_type=script_type
    )

    try:
        # Prepare parameters for Unity
        params = {
            "action": action,
            "name": name,
            "path": path,
            "namespace": namespace,
            "scriptType": script_type
        }

        # Handle contents encoding for safe transmission
        if contents is not None:
            if action in ['create', 'update']:
                # Validate contents for basic syntax issues
                _validate_script_contents(contents, script_type, log_context)

                # Encode content for safer transmission
                try:
                    encoded_contents = base64.b64encode(contents.encode('utf-8')).decode('utf-8')
                    params["encodedContents"] = encoded_contents
                    params["contentsEncoded"] = True

                    enhanced_logger.info(
                        "Script contents encoded for transmission",
                        context=log_context,
                        content_size=len(contents),
                        encoded_size=len(encoded_contents)
                    )
                except Exception as e:
                    raise ResourceError(
                        f"Failed to encode script contents: {str(e)}",
                        resource_type="script_content",
                        context={"encoding_error": str(e)}
                    )
            else:
                params["contents"] = contents

        # Remove None values to avoid sending null
        params = {k: v for k, v in params.items() if v is not None}

        # Get connection and send command
        connection = get_enhanced_unity_connection()

        enhanced_logger.info(
            "Sending script command to Unity",
            context=log_context,
            command_params=list(params.keys())
        )

        response = connection.send_command("manage_script", params)

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
                        "Script contents decoded from response",
                        context=log_context,
                        decoded_size=len(decoded_contents)
                    )
                except Exception as e:
                    enhanced_logger.warning(
                        "Failed to decode script contents from response",
                        context=log_context,
                        error=str(e)
                    )

            enhanced_logger.info(
                f"Script operation '{action}' completed successfully",
                context=log_context,
                response_message=response.get("message", "")
            )

            return {
                "success": True,
                "message": response.get("message", "Script operation completed successfully."),
                "data": result_data
            }
        else:
            error_message = response.get("error", "Unknown Unity error occurred.")
            enhanced_logger.error(
                f"Unity script operation failed: {error_message}",
                context=log_context,
                unity_error=error_message
            )

            raise UnityOperationError(
                error_message,
                operation=f"manage_script.{action}",
                unity_error=error_message,
                context={"script_name": name, "script_path": path}
            )

    except Exception as e:
        if isinstance(e, (UnityOperationError, ResourceError, ValidationError)):
            raise  # Re-raise our custom exceptions

        # Wrap unexpected exceptions
        enhanced_logger.error(
            f"Unexpected error during script operation",
            context=log_context,
            exception=e,
            script_name=name,
            action=action
        )

        raise UnityOperationError(
            f"Script operation failed: {str(e)}",
            operation=f"manage_script.{action}",
            context={"original_error": str(e), "script_name": name}
        )


def _validate_script_contents(contents: str, script_type: str, log_context: LogContext) -> None:
    """Validate script contents for basic issues."""
    if not contents or not contents.strip():
        raise ValidationError(
            "Script contents cannot be empty",
            parameter="contents",
            value="<empty>"
        )

    # Basic syntax validation
    if script_type == "MonoBehaviour":
        if "class" not in contents:
            enhanced_logger.warning(
                "MonoBehaviour script missing class declaration",
                context=log_context
            )

        if ": MonoBehaviour" not in contents and "MonoBehaviour" in script_type:
            enhanced_logger.warning(
                "MonoBehaviour script should inherit from MonoBehaviour",
                context=log_context
            )

    # Check for common issues
    if len(contents) > 1024 * 1024:  # 1MB limit
        raise ValidationError(
            "Script contents too large (max 1MB)",
            parameter="contents",
            context={"size": len(contents), "max_size": 1024 * 1024}
        )

    enhanced_logger.info(
        "Script contents validation passed",
        context=log_context,
        content_size=len(contents),
        script_type=script_type
    )