from mcp.server.fastmcp import FastMCP, Context, Image
import logging
import time
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, List
from config import config
from tools import register_all_tools

# Import enhanced infrastructure
from enhanced_connection import get_enhanced_unity_connection, EnhancedUnityConnection
from enhanced_logging import enhanced_logger, LogContext
from timeout_manager import timeout_manager
from exceptions import ConnectionError as UnityConnectionError

# Configure basic logging (enhanced logging is configured separately)
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format=config.log_format
)
logger = logging.getLogger("unity-mcp-server")

# Global connection state
_enhanced_unity_connection: EnhancedUnityConnection = None

@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Handle server startup and shutdown with enhanced error handling."""
    global _enhanced_unity_connection

    startup_context = LogContext(operation="server_startup")
    enhanced_logger.info("Unity MCP Server starting up", context=startup_context)

    try:
        # Initialize enhanced connection
        _enhanced_unity_connection = get_enhanced_unity_connection()

        # Attempt initial connection
        try:
            if _enhanced_unity_connection.connect():
                enhanced_logger.info(
                    "Successfully connected to Unity on startup",
                    context=startup_context,
                    connection_metrics=_enhanced_unity_connection.get_metrics()
                )
            else:
                enhanced_logger.warning(
                    "Could not connect to Unity on startup - will retry on first request",
                    context=startup_context
                )
        except UnityConnectionError as e:
            enhanced_logger.warning(
                f"Unity connection failed on startup: {e.message}",
                context=startup_context,
                exception=e
            )
        except Exception as e:
            enhanced_logger.error(
                f"Unexpected error during Unity connection: {str(e)}",
                context=startup_context,
                exception=e
            )

        try:
            # Yield the connection object for tools to access
            yield {"bridge": _enhanced_unity_connection}
        finally:
            # Cleanup on shutdown
            shutdown_context = LogContext(operation="server_shutdown")
            enhanced_logger.info("Unity MCP Server shutting down", context=shutdown_context)

            if _enhanced_unity_connection:
                try:
                    # Log final metrics
                    final_metrics = _enhanced_unity_connection.get_metrics()
                    enhanced_logger.info(
                        "Final connection metrics",
                        context=shutdown_context,
                        metrics=final_metrics
                    )

                    # Disconnect gracefully
                    _enhanced_unity_connection.disconnect()
                    enhanced_logger.info("Unity connection closed", context=shutdown_context)
                except Exception as e:
                    enhanced_logger.error(
                        "Error during connection cleanup",
                        context=shutdown_context,
                        exception=e
                    )
                finally:
                    _enhanced_unity_connection = None

            # Cancel any long-running operations
            cancelled_count = timeout_manager.cancel_long_running_operations()
            if cancelled_count > 0:
                enhanced_logger.info(
                    f"Cancelled {cancelled_count} long-running operations during shutdown",
                    context=shutdown_context
                )

            enhanced_logger.info("Unity MCP Server shut down complete", context=shutdown_context)

    except Exception as e:
        enhanced_logger.critical(
            f"Critical error during server lifecycle: {str(e)}",
            context=startup_context,
            exception=e
        )
        raise

# Initialize MCP server
mcp = FastMCP(
    "unity-mcp-server",
    description="Unity Editor integration via Model Context Protocol",
    lifespan=server_lifespan
)

# Register all tools
register_all_tools(mcp)

# Health check tool for monitoring
@mcp.tool()
def health_check(ctx: Context) -> Dict[str, Any]:
    """Check the health status of the Unity MCP Server and Unity connection."""
    try:
        health_context = LogContext(operation="health_check")
        enhanced_logger.info("Health check requested", context=health_context)

        # Get connection metrics
        connection = get_enhanced_unity_connection()
        metrics = connection.get_metrics()

        # Test connection with ping
        connection_healthy = False
        ping_error = None
        try:
            ping_result = connection.ping()
            connection_healthy = True
            enhanced_logger.info("Health check ping successful", context=health_context)
        except Exception as e:
            ping_error = str(e)
            enhanced_logger.warning(
                f"Health check ping failed: {ping_error}",
                context=health_context,
                exception=e
            )

        # Get timeout manager status
        active_operations = timeout_manager.get_active_operations()

        health_status = {
            "status": "healthy" if connection_healthy else "degraded",
            "timestamp": time.time(),
            "connection": {
                "healthy": connection_healthy,
                "error": ping_error,
                "metrics": metrics
            },
            "operations": {
                "active_count": len(active_operations),
                "active_operations": active_operations
            },
            "server": {
                "version": "2.0.0",
                "config": {
                    "host": config.unity_host,
                    "port": config.unity_port,
                    "timeouts_enabled": True,
                    "validation_enabled": config.enable_strict_validation,
                    "health_checks_enabled": config.enable_health_checks
                }
            }
        }

        return {
            "success": True,
            "message": f"Health check completed - status: {health_status['status']}",
            "data": health_status
        }

    except Exception as e:
        enhanced_logger.error(
            "Health check failed with unexpected error",
            context=LogContext(operation="health_check"),
            exception=e
        )
        return {
            "success": False,
            "error": f"Health check failed: {str(e)}",
            "data": {
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
        }

# Asset Creation Strategy

@mcp.prompt()
def asset_creation_strategy() -> str:
    """Guide for discovering and using Unity MCP tools effectively."""
    return (
        "Available Unity MCP Server Tools:\\n\\n"
        "- `manage_editor`: Controls editor state and queries info.\\n"
        "- `execute_menu_item`: Executes Unity Editor menu items by path.\\n"
        "- `read_console`: Reads or clears Unity console messages, with filtering options.\\n"
        "- `manage_scene`: Manages scenes.\\n"
        "- `manage_gameobject`: Manages GameObjects in the scene.\\n"
        "- `manage_script`: Manages C# script files.\\n"
        "- `manage_asset`: Manages prefabs and assets.\\n"
        "- `manage_shader`: Manages shaders.\\n"
        "- `health_check`: Check server and Unity connection health.\\n\\n"
        "Enhanced Features:\\n"
        "- Robust error handling with detailed error messages\\n"
        "- Operation timeouts to prevent infinite waiting\\n"
        "- Input validation for all parameters\\n"
        "- Comprehensive logging for debugging\\n"
        "- Connection health monitoring and auto-recovery\\n\\n"
        "Tips:\\n"
        "- Create prefabs for reusable GameObjects.\\n"
        "- Always include a camera and main light in your scenes.\\n"
        "- Use health_check tool to monitor connection status.\\n"
    )

# Run the server
if __name__ == "__main__":
    mcp.run(transport='stdio')
