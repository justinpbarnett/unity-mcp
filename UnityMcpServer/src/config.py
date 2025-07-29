"""
Configuration settings for the Unity MCP Server.
This file contains all configurable parameters for the server.
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ServerConfig:
    """Main configuration class for the MCP server."""

    # Network settings
    unity_host: str = "localhost"
    unity_port: int = 6400
    mcp_port: int = 6500

    # Connection settings
    connection_timeout: float = 86400.0  # 24 hours timeout (legacy)
    buffer_size: int = 16 * 1024 * 1024  # 16MB buffer

    # Enhanced timeout settings (per operation type)
    operation_timeouts: Dict[str, float] = None

    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_exponential_backoff: bool = True
    retry_max_delay: float = 30.0

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_structured_logging: bool = True
    log_file_max_size: int = 10 * 1024 * 1024  # 10MB
    log_file_backup_count: int = 5

    # Error handling settings
    enable_detailed_errors: bool = True
    include_stack_traces: bool = True
    error_context_max_size: int = 1000  # Max characters for error context

    # Performance settings
    enable_performance_logging: bool = True
    slow_operation_threshold: float = 5.0  # Log operations slower than this

    # Health check settings
    enable_health_checks: bool = True
    health_check_interval: float = 30.0  # seconds

    # Validation settings
    enable_strict_validation: bool = True
    validate_unity_paths: bool = True

    def __post_init__(self):
        """Initialize default operation timeouts if not provided."""
        if self.operation_timeouts is None:
            self.operation_timeouts = {
                "connection": 10.0,
                "ping": 5.0,
                "script_operation": 30.0,
                "scene_operation": 60.0,
                "gameobject_operation": 30.0,
                "asset_operation": 45.0,
                "editor_operation": 20.0,
                "console_operation": 10.0,
                "menu_operation": 15.0,
                "shader_operation": 30.0,
                "long_running": 300.0,
                "max_timeout": 600.0
            }

# Create a global config instance
config = ServerConfig()