"""
Configuration settings for the Unity MCP Server.
This file contains all configurable parameters for the server.
"""

import argparse
from dataclasses import dataclass

@dataclass
class ServerConfig:
    """Main configuration class for the MCP server."""
    
    # Network settings
    unity_host: str = "localhost"
    unity_port: int = 6400
    mcp_port: int = 6500
    
    # Connection settings
    connection_timeout: float = 86400.0  # 24 hours timeout
    buffer_size: int = 16 * 1024 * 1024  # 16MB buffer
    
    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Server settings
    max_retries: int = 3
    retry_delay: float = 1.0

# Parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='Unity MCP Server')
    parser.add_argument('--unity-host', dest='unity_host', type=str, default="localhost",
                        help='Host address of Unity Editor (default: localhost)')
    parser.add_argument('--unity-port', dest='unity_port', type=int, default=6400,
                        help='Port number of Unity Editor (default: 6400)')
    parser.add_argument('--log-level', dest='log_level', type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help='Logging level (default: INFO)')
    return parser.parse_args()

# Create a global config instance with default values
config = ServerConfig()

# This will be called from server.py to update the config with command line arguments
def load_config_from_args():
    args = parse_args()
    config.unity_host = args.unity_host
    config.unity_port = args.unity_port
    config.log_level = args.log_level 