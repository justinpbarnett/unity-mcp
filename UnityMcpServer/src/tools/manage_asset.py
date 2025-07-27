"""
Defines the manage_asset tool for interacting with Unity assets.
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
from error_recovery import error_recovery_manager
from advanced_logging import advanced_log_manager, LogLevel, LogCategory

def register_manage_asset_tools(mcp: FastMCP):
    """Registers the manage_asset tool with the MCP server."""

    @mcp.tool()
    async def manage_asset(
        ctx: Context,
        action: str,
        path: str,
        asset_type: str = None,
        properties: Dict[str, Any] = None,
        destination: str = None,
        generate_preview: bool = False,
        search_pattern: str = None,
        filter_type: str = None,
        filter_date_after: str = None,
        page_size: int = None,
        page_number: int = None
    ) -> Dict[str, Any]:
        """Performs asset operations (import, create, modify, delete, etc.) in Unity.

        Args:
            ctx: The MCP context.
            action: Operation to perform (e.g., 'import', 'create', 'modify', 'delete', 'duplicate', 'move', 'rename', 'search', 'get_info', 'create_folder', 'get_components').
            path: Asset path (e.g., "Materials/MyMaterial.mat") or search scope.
            asset_type: Asset type (e.g., 'Material', 'Folder') - required for 'create'.
            properties: Dictionary of properties for 'create'/'modify'.
            destination: Target path for 'duplicate'/'move'.
            search_pattern: Search pattern (e.g., '*.prefab').
            filter_*: Filters for search (type, date).
            page_*: Pagination for search.

        Returns:
            A dictionary with operation results ('success', 'data', 'error').
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Create log context
        log_context = LogContext(
            operation=f"manage_asset.{action}",
            tool_name="manage_asset",
            request_id=request_id
        )

        try:
            # Log tool call
            enhanced_logger.log_tool_call(
                "manage_asset",
                action,
                {
                    "path": path,
                    "asset_type": asset_type,
                    "has_properties": properties is not None,
                    "destination": destination,
                    "generate_preview": generate_preview
                },
                request_id
            )

            # Ensure properties is a dict if None
            if properties is None:
                properties = {}

            # Validate input parameters
            parameters = {
                "action": action,
                "path": path,
                "asset_type": asset_type,
                "properties": properties,
                "destination": destination,
                "generate_preview": generate_preview,
                "search_pattern": search_pattern,
                "filter_type": filter_type,
                "filter_date_after": filter_date_after,
                "page_size": page_size,
                "page_number": page_number
            }

            validate_tool_parameters("manage_asset", parameters)

            # Execute the operation with timeout
            result = await _execute_asset_operation(
                action, path, asset_type, properties, destination, generate_preview,
                search_pattern, filter_type, filter_date_after, page_size, page_number,
                log_context
            )

            # Log successful result
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_asset", action, True,
                result_summary=f"Asset {action} completed for '{path}'",
                request_id=request_id,
                duration=duration
            )

            return result

        except ValidationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_asset", action, False,
                error_message=f"Validation error: {e.message}",
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except UnityOperationError as e:
            duration = time.time() - start_time
            enhanced_logger.log_tool_result(
                "manage_asset", action, False,
                error_message=e.message,
                request_id=request_id,
                duration=duration
            )
            return create_error_response(e)

        except Exception as e:
            duration = time.time() - start_time
            enhanced_logger.error(
                f"Unexpected error in manage_asset.{action}",
                context=log_context,
                exception=e,
                parameters={k: v for k, v in parameters.items() if k != 'properties'}  # Exclude complex objects
            )
            enhanced_logger.log_tool_result(
                "manage_asset", action, False,
                error_message=f"Internal error: {str(e)}",
                request_id=request_id,
                duration=duration
            )

            # Create generic error response for unexpected errors
            from exceptions import UnityMcpError, ErrorCategory, ErrorSeverity
            error = UnityMcpError(
                f"Unexpected error in asset management: {str(e)}",
                category=ErrorCategory.INTERNAL,
                severity=ErrorSeverity.HIGH,
                context={"original_error": str(e), "action": action, "asset_path": path}
            )
            return create_error_response(error)


@with_timeout(OperationType.ASSET_OPERATION, "asset_operation")
async def _execute_asset_operation(
    action: str,
    path: str,
    asset_type: Optional[str],
    properties: Dict[str, Any],
    destination: Optional[str],
    generate_preview: bool,
    search_pattern: Optional[str],
    filter_type: Optional[str],
    filter_date_after: Optional[str],
    page_size: Optional[int],
    page_number: Optional[int],
    log_context: LogContext
) -> Dict[str, Any]:
    """Execute asset operation with proper error handling and logging."""

    enhanced_logger.info(
        f"Executing asset operation: {action}",
        context=log_context,
        asset_path=path,
        asset_type=asset_type,
        destination=destination,
        generate_preview=generate_preview
    )

    try:
        # Prepare parameters for Unity
        params_dict = {
            "action": action.lower(),
            "path": path,
            "assetType": asset_type,
            "properties": properties,
            "destination": destination,
            "generatePreview": generate_preview,
            "searchPattern": search_pattern,
            "filterType": filter_type,
            "filterDateAfter": filter_date_after,
            "pageSize": page_size,
            "pageNumber": page_number
        }

        # Remove None values to avoid sending unnecessary nulls
        params_dict = {k: v for k, v in params_dict.items() if v is not None}

        # Validate action-specific requirements
        _validate_asset_action(action, params_dict, log_context)

        # Get connection and send command
        connection = get_enhanced_unity_connection()

        enhanced_logger.info(
            "Sending asset command to Unity",
            context=log_context,
            command_params=list(params_dict.keys()),
            param_count=len(params_dict)
        )

        # Use asyncio to run the synchronous operation in a thread pool
        import asyncio
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,  # Use default executor
            connection.send_command,
            "manage_asset",
            params_dict
        )

        # Process response from Unity
        if response.get("success"):
            result_data = response.get("data", {})

            enhanced_logger.info(
                f"Asset operation '{action}' completed successfully",
                context=log_context,
                response_message=response.get("message", ""),
                result_keys=list(result_data.keys()) if result_data else []
            )

            return {
                "success": True,
                "message": response.get("message", "Asset operation completed successfully."),
                "data": result_data
            }
        else:
            error_message = response.get("error", "Unknown Unity error occurred during asset management.")
            enhanced_logger.error(
                f"Unity asset operation failed: {error_message}",
                context=log_context,
                unity_error=error_message
            )

            raise UnityOperationError(
                error_message,
                operation=f"manage_asset.{action}",
                unity_error=error_message,
                context={"asset_path": path, "action": action, "asset_type": asset_type}
            )

    except Exception as e:
        if isinstance(e, (UnityOperationError, ValidationError)):
            raise  # Re-raise our custom exceptions

        # Wrap unexpected exceptions
        enhanced_logger.error(
            f"Unexpected error during asset operation",
            context=log_context,
            exception=e,
            asset_path=path,
            action=action
        )

        raise UnityOperationError(
            f"Asset operation failed: {str(e)}",
            operation=f"manage_asset.{action}",
            context={"original_error": str(e), "asset_path": path}
        )


def _validate_asset_action(action: str, params: Dict[str, Any], log_context: LogContext) -> None:
    """Validate action-specific requirements for asset operations."""

    # Action-specific validation
    if action == "create" and not params.get("assetType"):
        raise ValidationError(
            "Asset type is required for create action",
            parameter="asset_type",
            context={"action": action}
        )

    if action in ["duplicate", "move"] and not params.get("destination"):
        raise ValidationError(
            f"Destination path is required for {action} action",
            parameter="destination",
            context={"action": action}
        )

    if action == "search":
        if not params.get("searchPattern") and not params.get("filterType"):
            raise ValidationError(
                "Either search pattern or filter type is required for search action",
                parameter="search_pattern",
                context={"action": action}
            )

    # Validate pagination parameters
    if params.get("pageSize") is not None:
        page_size = params.get("pageSize")
        if not isinstance(page_size, int) or page_size <= 0:
            raise ValidationError(
                "Page size must be a positive integer",
                parameter="page_size",
                value=page_size
            )

    if params.get("pageNumber") is not None:
        page_number = params.get("pageNumber")
        if not isinstance(page_number, int) or page_number < 0:
            raise ValidationError(
                "Page number must be a non-negative integer",
                parameter="page_number",
                value=page_number
            )

    # Validate path format
    asset_path = params.get("path")
    if asset_path and not isinstance(asset_path, str):
        raise ValidationError(
            "Asset path must be a string",
            parameter="path",
            value=asset_path
        )

    if asset_path and len(asset_path.strip()) == 0:
        raise ValidationError(
            "Asset path cannot be empty",
            parameter="path",
            value=asset_path
        )

    # Log validation success
    enhanced_logger.info(
        f"Asset action validation passed for '{action}'",
        context=log_context,
        validated_params=list(params.keys())
    )