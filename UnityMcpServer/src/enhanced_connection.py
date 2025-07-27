"""
Enhanced Unity connection management with health monitoring,
retry logic, and robust error handling.
"""

import socket
import json
import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import threading
from contextlib import contextmanager

from config import config
from exceptions import ConnectionError, TimeoutError, UnityOperationError
from enhanced_logging import enhanced_logger, LogContext
from timeout_manager import with_timeout, OperationType


class ConnectionState(Enum):
    """Connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionMetrics:
    """Metrics for connection monitoring."""
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_commands: int = 0
    successful_commands: int = 0
    failed_commands: int = 0
    average_response_time: float = 0.0
    last_successful_ping: Optional[float] = None
    connection_uptime: float = 0.0
    reconnection_attempts: int = 0


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = field(default_factory=lambda: config.max_retries)
    base_delay: float = field(default_factory=lambda: config.retry_delay)
    max_delay: float = field(default_factory=lambda: config.retry_max_delay)
    exponential_backoff: bool = field(default_factory=lambda: config.retry_exponential_backoff)
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        if not self.exponential_backoff:
            return self.base_delay
        
        delay = self.base_delay * (2 ** (attempt - 1))
        return min(delay, self.max_delay)


class EnhancedUnityConnection:
    """Enhanced Unity connection with robust error handling and monitoring."""
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or config.unity_host
        self.port = port or config.unity_port
        self.sock: Optional[socket.socket] = None
        self.state = ConnectionState.DISCONNECTED
        self.metrics = ConnectionMetrics()
        self.retry_config = RetryConfig()
        self._lock = threading.RLock()
        self._connection_start_time: Optional[float] = None
        self._health_check_task: Optional[asyncio.Task] = None
        
    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self.state == ConnectionState.CONNECTED and self.sock is not None
    
    @with_timeout(OperationType.CONNECTION, "connect")
    def connect(self) -> bool:
        """Establish connection to Unity with retry logic."""
        with self._lock:
            if self.is_connected:
                return True
            
            self.state = ConnectionState.CONNECTING
            self.metrics.total_connections += 1
            
            for attempt in range(1, self.retry_config.max_attempts + 1):
                try:
                    enhanced_logger.info(
                        f"Attempting to connect to Unity (attempt {attempt}/{self.retry_config.max_attempts})",
                        context=LogContext(operation="connect"),
                        host=self.host,
                        port=self.port,
                        attempt=attempt
                    )
                    
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sock.settimeout(config.operation_timeouts.get("connection", 10.0))
                    self.sock.connect((self.host, self.port))
                    
                    # Verify connection with ping
                    if self._verify_connection():
                        self.state = ConnectionState.CONNECTED
                        self.metrics.successful_connections += 1
                        self._connection_start_time = time.time()
                        
                        enhanced_logger.info(
                            "Successfully connected to Unity",
                            context=LogContext(operation="connect"),
                            host=self.host,
                            port=self.port,
                            attempts_used=attempt
                        )
                        
                        # Start health monitoring if enabled
                        if config.enable_health_checks:
                            self._start_health_monitoring()
                        
                        return True
                    else:
                        self._cleanup_socket()
                        raise ConnectionError("Connection verification failed")
                        
                except Exception as e:
                    self._cleanup_socket()
                    
                    if attempt == self.retry_config.max_attempts:
                        self.state = ConnectionState.FAILED
                        self.metrics.failed_connections += 1
                        
                        enhanced_logger.error(
                            f"Failed to connect to Unity after {attempt} attempts",
                            context=LogContext(operation="connect"),
                            exception=e,
                            host=self.host,
                            port=self.port,
                            total_attempts=attempt
                        )
                        
                        raise ConnectionError(
                            f"Could not connect to Unity at {self.host}:{self.port} after {attempt} attempts",
                            host=self.host,
                            port=self.port,
                            context={"last_error": str(e), "attempts": attempt}
                        )
                    
                    # Wait before retry
                    delay = self.retry_config.get_delay(attempt)
                    enhanced_logger.warning(
                        f"Connection attempt {attempt} failed, retrying in {delay}s",
                        context=LogContext(operation="connect"),
                        error=str(e),
                        retry_delay=delay
                    )
                    time.sleep(delay)
            
            return False
    
    def _verify_connection(self) -> bool:
        """Verify connection is working with a ping."""
        try:
            result = self._send_raw_command("ping")
            return result.get("message") == "pong"
        except Exception:
            return False
    
    def disconnect(self):
        """Disconnect from Unity with cleanup."""
        with self._lock:
            if self._health_check_task:
                self._health_check_task.cancel()
                self._health_check_task = None
            
            self._cleanup_socket()
            
            if self._connection_start_time:
                self.metrics.connection_uptime += time.time() - self._connection_start_time
                self._connection_start_time = None
            
            self.state = ConnectionState.DISCONNECTED
            
            enhanced_logger.info(
                "Disconnected from Unity",
                context=LogContext(operation="disconnect")
            )
    
    def _cleanup_socket(self):
        """Clean up socket resources."""
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                enhanced_logger.warning(
                    "Error closing socket",
                    context=LogContext(operation="cleanup"),
                    error=str(e)
                )
            finally:
                self.sock = None
    
    @with_timeout(OperationType.PING, "ping")
    def ping(self) -> Dict[str, Any]:
        """Ping Unity to check connection health."""
        try:
            result = self._send_raw_command("ping")
            self.metrics.last_successful_ping = time.time()
            return result
        except Exception as e:
            enhanced_logger.error(
                "Ping failed",
                context=LogContext(operation="ping"),
                exception=e
            )
            raise
    
    def send_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send command to Unity with automatic reconnection."""
        if not self.is_connected:
            enhanced_logger.info("Connection lost, attempting to reconnect")
            if not self.connect():
                raise ConnectionError("Could not establish connection to Unity")
        
        return self._send_command_with_retry(command_type, params)
    
    def _send_command_with_retry(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send command with retry logic."""
        self.metrics.total_commands += 1
        
        for attempt in range(1, self.retry_config.max_attempts + 1):
            try:
                start_time = time.time()
                result = self._send_raw_command(command_type, params)
                duration = time.time() - start_time
                
                # Update metrics
                self.metrics.successful_commands += 1
                self._update_average_response_time(duration)
                
                enhanced_logger.log_unity_communication(
                    command_type, True, 
                    response_size=len(json.dumps(result)) if result else 0,
                    duration=duration
                )
                
                return result
                
            except Exception as e:
                if attempt == self.retry_config.max_attempts:
                    self.metrics.failed_commands += 1
                    enhanced_logger.log_unity_communication(
                        command_type, False, error_message=str(e)
                    )
                    raise
                
                # Try to reconnect if connection error
                if isinstance(e, (ConnectionError, socket.error)):
                    enhanced_logger.warning(f"Connection error on attempt {attempt}, reconnecting")
                    self.disconnect()
                    if not self.connect():
                        continue
                
                delay = self.retry_config.get_delay(attempt)
                time.sleep(delay)
        
        raise UnityOperationError(f"Command '{command_type}' failed after all retry attempts")
    
    def _send_raw_command(self, command_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send raw command to Unity (internal method)."""
        if not self.sock:
            raise ConnectionError("No active connection to Unity")
        
        # Handle ping specially
        if command_type == "ping":
            self.sock.sendall(b"ping")
            response_data = self._receive_full_response()
            response = json.loads(response_data.decode('utf-8'))
            
            if response.get("status") != "success":
                raise ConnectionError("Ping response was not successful")
            
            return response.get("result", {})
        
        # Regular command
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        command_json = json.dumps(command, ensure_ascii=False)
        self.sock.sendall(command_json.encode('utf-8'))
        
        response_data = self._receive_full_response()
        try:
            response = json.loads(response_data.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise UnityOperationError(f"Invalid JSON response from Unity: {str(e)}")
        
        if response.get("status") == "error":
            error_message = response.get("error", "Unknown Unity error")
            raise UnityOperationError(error_message, operation=command_type, unity_error=error_message)
        
        return response.get("result", {})
    
    def _receive_full_response(self) -> bytes:
        """Receive complete response from Unity."""
        chunks = []
        timeout = config.operation_timeouts.get("connection", 10.0)
        self.sock.settimeout(timeout)
        
        try:
            while True:
                chunk = self.sock.recv(config.buffer_size)
                if not chunk:
                    if not chunks:
                        raise ConnectionError("Connection closed before receiving data")
                    break
                chunks.append(chunk)
                
                # Check if we have complete JSON
                data = b''.join(chunks)
                try:
                    decoded_data = data.decode('utf-8')
                    json.loads(decoded_data)  # Validate JSON
                    return data
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue  # Need more data
                    
        except socket.timeout:
            raise TimeoutError(f"Timeout waiting for Unity response", timeout_seconds=timeout)
    
    def _update_average_response_time(self, duration: float):
        """Update average response time metric."""
        if self.metrics.successful_commands == 1:
            self.metrics.average_response_time = duration
        else:
            # Exponential moving average
            alpha = 0.1
            self.metrics.average_response_time = (
                alpha * duration + (1 - alpha) * self.metrics.average_response_time
            )
    
    def _start_health_monitoring(self):
        """Start background health monitoring."""
        async def health_check_loop():
            while self.is_connected:
                try:
                    await asyncio.sleep(config.health_check_interval)
                    if self.is_connected:
                        self.ping()
                except Exception as e:
                    enhanced_logger.warning(
                        "Health check failed",
                        context=LogContext(operation="health_check"),
                        exception=e
                    )
        
        if asyncio.get_event_loop().is_running():
            self._health_check_task = asyncio.create_task(health_check_loop())
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection metrics."""
        metrics_dict = {
            "state": self.state.value,
            "host": self.host,
            "port": self.port,
            "is_connected": self.is_connected,
            **self.metrics.__dict__
        }
        
        if self._connection_start_time:
            metrics_dict["current_session_duration"] = time.time() - self._connection_start_time
        
        return metrics_dict


# Global enhanced connection instance
_enhanced_connection: Optional[EnhancedUnityConnection] = None


def get_enhanced_unity_connection() -> EnhancedUnityConnection:
    """Get or create the global enhanced Unity connection."""
    global _enhanced_connection
    
    if _enhanced_connection is None:
        _enhanced_connection = EnhancedUnityConnection()
    
    return _enhanced_connection
