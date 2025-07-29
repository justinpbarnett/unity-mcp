"""
Remote connection support for Unity MCP Server.
Enables seamless remote connection between Unity host and MCP server with security and discovery.
"""

import socket
import json
import time
import threading
import hashlib
import secrets
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import ssl
from urllib.parse import urlparse

from enhanced_logging import enhanced_logger, LogContext
from exceptions import ConnectionError, ValidationError
from config import config


class ConnectionType(Enum):
    """Types of remote connections supported."""
    LOCAL = "local"
    NETWORK = "network"
    SECURE = "secure"
    CLOUD = "cloud"


class AuthenticationMethod(Enum):
    """Authentication methods for remote connections."""
    NONE = "none"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    API_KEY = "api_key"


@dataclass
class RemoteHost:
    """Information about a remote Unity host."""
    host: str
    port: int
    name: str = "Unknown Unity Host"
    connection_type: ConnectionType = ConnectionType.NETWORK
    auth_method: AuthenticationMethod = AuthenticationMethod.NONE
    auth_token: str = None
    last_seen: float = 0
    is_verified: bool = False
    capabilities: List[str] = None
    unity_version: str = None
    project_name: str = None


@dataclass
class ConnectionConfig:
    """Configuration for remote connections."""
    enable_discovery: bool = True
    discovery_port: int = 6401
    discovery_interval: int = 30
    connection_timeout: int = 10
    enable_ssl: bool = False
    ssl_cert_file: str = None
    ssl_key_file: str = None
    require_authentication: bool = False
    allowed_hosts: List[str] = None
    max_connections: int = 10


class RemoteConnectionManager:
    """Manages remote connections to Unity hosts with discovery and security."""
    
    def __init__(self, connection_config: ConnectionConfig = None):
        self.config = connection_config or ConnectionConfig()
        self.discovered_hosts: Dict[str, RemoteHost] = {}
        self.active_connections: Dict[str, socket.socket] = {}
        self.connection_stats = {
            "total_discoveries": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "authentication_failures": 0
        }
        
        self.discovery_thread = None
        self.discovery_running = False
        self.lock = threading.Lock()
        
        # Security
        self.api_keys: Dict[str, str] = {}  # host -> api_key
        self.connection_tokens: Dict[str, str] = {}  # connection_id -> token
        
        if self.config.enable_discovery:
            self.start_discovery()
    
    def start_discovery(self):
        """Start the host discovery service."""
        
        if self.discovery_running:
            return
        
        self.discovery_running = True
        self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.discovery_thread.start()
        
        enhanced_logger.info(
            "Remote host discovery started",
            discovery_port=self.config.discovery_port,
            discovery_interval=self.config.discovery_interval
        )
    
    def stop_discovery(self):
        """Stop the host discovery service."""
        
        self.discovery_running = False
        if self.discovery_thread:
            self.discovery_thread.join(timeout=5)
        
        enhanced_logger.info("Remote host discovery stopped")
    
    def _discovery_loop(self):
        """Main discovery loop that broadcasts and listens for Unity hosts."""
        
        # Create UDP socket for discovery
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        discovery_socket.settimeout(1.0)
        
        try:
            # Bind to discovery port
            discovery_socket.bind(('', self.config.discovery_port))
            enhanced_logger.info(f"Discovery service listening on port {self.config.discovery_port}")
            
            while self.discovery_running:
                try:
                    # Send discovery broadcast
                    self._send_discovery_broadcast(discovery_socket)
                    
                    # Listen for responses
                    start_time = time.time()
                    while time.time() - start_time < self.config.discovery_interval:
                        try:
                            data, addr = discovery_socket.recvfrom(1024)
                            self._handle_discovery_response(data, addr)
                        except socket.timeout:
                            continue
                        except Exception as e:
                            enhanced_logger.warning(f"Discovery receive error: {e}")
                
                except Exception as e:
                    enhanced_logger.error(f"Discovery loop error: {e}")
                    time.sleep(5)  # Wait before retrying
        
        finally:
            discovery_socket.close()
    
    def _send_discovery_broadcast(self, sock: socket.socket):
        """Send discovery broadcast to find Unity hosts."""
        
        discovery_message = {
            "type": "mcp_discovery",
            "version": "2.0.0",
            "timestamp": time.time(),
            "server_info": {
                "name": "Unity MCP Server",
                "capabilities": ["script_management", "scene_management", "asset_management"],
                "auth_methods": [method.value for method in AuthenticationMethod],
                "secure_connection": self.config.enable_ssl
            }
        }
        
        try:
            message_data = json.dumps(discovery_message).encode('utf-8')
            sock.sendto(message_data, ('<broadcast>', self.config.discovery_port))
            
            enhanced_logger.debug("Discovery broadcast sent")
            
        except Exception as e:
            enhanced_logger.warning(f"Failed to send discovery broadcast: {e}")
    
    def _handle_discovery_response(self, data: bytes, addr: Tuple[str, int]):
        """Handle discovery response from Unity host."""
        
        try:
            response = json.loads(data.decode('utf-8'))
            
            if response.get("type") != "unity_host_response":
                return
            
            host_info = response.get("host_info", {})
            host_id = f"{addr[0]}:{host_info.get('port', 6400)}"
            
            # Create or update host information
            remote_host = RemoteHost(
                host=addr[0],
                port=host_info.get('port', 6400),
                name=host_info.get('name', 'Unity Host'),
                connection_type=ConnectionType.NETWORK,
                auth_method=AuthenticationMethod(host_info.get('auth_method', 'none')),
                last_seen=time.time(),
                capabilities=host_info.get('capabilities', []),
                unity_version=host_info.get('unity_version'),
                project_name=host_info.get('project_name')
            )
            
            with self.lock:
                self.discovered_hosts[host_id] = remote_host
                self.connection_stats["total_discoveries"] += 1
            
            enhanced_logger.info(
                f"Discovered Unity host: {remote_host.name} at {host_id}",
                host_info=host_info,
                capabilities=remote_host.capabilities
            )
            
        except Exception as e:
            enhanced_logger.warning(f"Failed to parse discovery response: {e}")
    
    def get_discovered_hosts(self, include_stale: bool = False) -> List[RemoteHost]:
        """Get list of discovered Unity hosts."""
        
        current_time = time.time()
        stale_threshold = 120  # 2 minutes
        
        with self.lock:
            hosts = []
            for host in self.discovered_hosts.values():
                if include_stale or (current_time - host.last_seen) < stale_threshold:
                    hosts.append(host)
            
            return hosts
    
    def connect_to_host(self, host: str, port: int, auth_token: str = None) -> str:
        """Connect to a specific Unity host."""
        
        host_id = f"{host}:{port}"
        
        # Check if host is allowed
        if self.config.allowed_hosts and host not in self.config.allowed_hosts:
            raise ConnectionError(f"Host {host} is not in allowed hosts list")
        
        # Check connection limit
        if len(self.active_connections) >= self.config.max_connections:
            raise ConnectionError("Maximum number of connections reached")
        
        try:
            # Create socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.connection_timeout)
            
            # Enable SSL if configured
            if self.config.enable_ssl:
                context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                if self.config.ssl_cert_file:
                    context.load_cert_chain(self.config.ssl_cert_file, self.config.ssl_key_file)
                sock = context.wrap_socket(sock, server_hostname=host)
            
            # Connect to host
            sock.connect((host, port))
            
            # Perform authentication if required
            if self.config.require_authentication:
                if not self._authenticate_connection(sock, host, auth_token):
                    sock.close()
                    self.connection_stats["authentication_failures"] += 1
                    raise ConnectionError("Authentication failed")
            
            # Generate connection ID
            connection_id = self._generate_connection_id(host, port)
            
            with self.lock:
                self.active_connections[connection_id] = sock
                self.connection_stats["successful_connections"] += 1
            
            enhanced_logger.info(
                f"Successfully connected to Unity host {host_id}",
                connection_id=connection_id,
                ssl_enabled=self.config.enable_ssl,
                authenticated=self.config.require_authentication
            )
            
            return connection_id
            
        except Exception as e:
            self.connection_stats["failed_connections"] += 1
            enhanced_logger.error(f"Failed to connect to Unity host {host_id}: {e}")
            raise ConnectionError(f"Could not connect to Unity host {host_id}: {str(e)}")
    
    def _authenticate_connection(self, sock: socket.socket, host: str, auth_token: str) -> bool:
        """Authenticate the connection with the Unity host."""
        
        try:
            # Send authentication request
            auth_request = {
                "type": "auth_request",
                "method": "token",
                "token": auth_token or self.api_keys.get(host),
                "timestamp": time.time()
            }
            
            auth_data = json.dumps(auth_request).encode('utf-8')
            sock.send(len(auth_data).to_bytes(4, 'big'))  # Send length first
            sock.send(auth_data)
            
            # Receive authentication response
            response_length = int.from_bytes(sock.recv(4), 'big')
            response_data = sock.recv(response_length)
            response = json.loads(response_data.decode('utf-8'))
            
            if response.get("status") == "authenticated":
                enhanced_logger.info(f"Authentication successful for host {host}")
                return True
            else:
                enhanced_logger.warning(f"Authentication failed for host {host}: {response.get('message')}")
                return False
                
        except Exception as e:
            enhanced_logger.error(f"Authentication error for host {host}: {e}")
            return False
    
    def _generate_connection_id(self, host: str, port: int) -> str:
        """Generate a unique connection ID."""
        
        timestamp = str(time.time())
        random_part = secrets.token_hex(8)
        connection_string = f"{host}:{port}:{timestamp}:{random_part}"
        
        return hashlib.sha256(connection_string.encode()).hexdigest()[:16]
    
    def send_command(self, connection_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send a command to a connected Unity host."""
        
        with self.lock:
            sock = self.active_connections.get(connection_id)
        
        if not sock:
            raise ConnectionError(f"No active connection with ID {connection_id}")
        
        try:
            # Prepare command
            command_data = json.dumps(command).encode('utf-8')
            
            # Send command length and data
            sock.send(len(command_data).to_bytes(4, 'big'))
            sock.send(command_data)
            
            # Receive response length and data
            response_length = int.from_bytes(sock.recv(4), 'big')
            response_data = sock.recv(response_length)
            response = json.loads(response_data.decode('utf-8'))
            
            enhanced_logger.debug(
                f"Command sent to connection {connection_id}",
                command_type=command.get('type'),
                response_status=response.get('success')
            )
            
            return response
            
        except Exception as e:
            enhanced_logger.error(f"Failed to send command to connection {connection_id}: {e}")
            # Remove failed connection
            self.disconnect_host(connection_id)
            raise ConnectionError(f"Command failed: {str(e)}")
    
    def disconnect_host(self, connection_id: str):
        """Disconnect from a Unity host."""
        
        with self.lock:
            sock = self.active_connections.pop(connection_id, None)
        
        if sock:
            try:
                sock.close()
                enhanced_logger.info(f"Disconnected from Unity host (connection {connection_id})")
            except Exception as e:
                enhanced_logger.warning(f"Error closing connection {connection_id}: {e}")
    
    def disconnect_all(self):
        """Disconnect from all Unity hosts."""
        
        with self.lock:
            connection_ids = list(self.active_connections.keys())
        
        for connection_id in connection_ids:
            self.disconnect_host(connection_id)
        
        enhanced_logger.info("Disconnected from all Unity hosts")
    
    def set_api_key(self, host: str, api_key: str):
        """Set API key for a specific host."""
        
        self.api_keys[host] = api_key
        enhanced_logger.info(f"API key set for host {host}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get status of all connections and discovery."""
        
        with self.lock:
            active_connections = len(self.active_connections)
            discovered_hosts = len(self.discovered_hosts)
        
        return {
            "discovery_running": self.discovery_running,
            "active_connections": active_connections,
            "discovered_hosts": discovered_hosts,
            "connection_stats": self.connection_stats,
            "configuration": {
                "enable_discovery": self.config.enable_discovery,
                "discovery_port": self.config.discovery_port,
                "enable_ssl": self.config.enable_ssl,
                "require_authentication": self.config.require_authentication,
                "max_connections": self.config.max_connections
            }
        }
    
    def cleanup(self):
        """Clean up resources."""
        
        self.stop_discovery()
        self.disconnect_all()
        
        enhanced_logger.info("Remote connection manager cleaned up")


# Global remote connection manager instance
remote_connection_manager = RemoteConnectionManager()
