"""
Configuration settings for the Unity MCP Server.
This file contains all configurable parameters for the server.
"""

import platform
import os
import logging
from dataclasses import dataclass

def get_host_ip() -> str:
    """
    Dynamically get host IP address, following TypeScript logic
    In WSL environment, read nameserver IP from /etc/resolv.conf
    """
    # If not Linux platform, return localhost directly
    if platform.system() != 'Linux':
        return 'localhost'
    
    resolv_conf_path = '/etc/resolv.conf'
    
    try:
        with open(resolv_conf_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        lines = file_content.split('\n')
        
        # Find the line starting with "nameserver"
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith('nameserver'):
                parts = stripped_line.split()
                if len(parts) >= 2:
                    ip_address = parts[1]
                    return ip_address
        
        return 'localhost'
    
    except Exception as error:
        logging.error(f"Error reading or parsing {resolv_conf_path}: {error}")
        return 'localhost'

@dataclass
class ServerConfig:
    """Main configuration class for the MCP server."""
    
    # Network settings
    unity_host: str = None  # Will be set dynamically
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

# Create a global config instance
config = ServerConfig()
# Set the unity_host dynamically
config.unity_host = get_host_ip() 