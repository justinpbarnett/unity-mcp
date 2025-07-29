"""
Timeout management system for Unity MCP Server operations.
Provides configurable timeouts for different operation types and
ensures no operation can hang indefinitely.
"""

import asyncio
import functools
import logging
import time
from typing import Dict, Any, Callable, Optional, TypeVar, Awaitable
from dataclasses import dataclass
from enum import Enum

from exceptions import TimeoutError as UnityTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class OperationType(Enum):
    """Types of operations with different timeout requirements."""
    CONNECTION = "connection"
    PING = "ping"
    SCRIPT_OPERATION = "script_operation"
    SCENE_OPERATION = "scene_operation"
    GAMEOBJECT_OPERATION = "gameobject_operation"
    ASSET_OPERATION = "asset_operation"
    EDITOR_OPERATION = "editor_operation"
    CONSOLE_OPERATION = "console_operation"
    MENU_OPERATION = "menu_operation"
    SHADER_OPERATION = "shader_operation"
    LONG_RUNNING = "long_running"


@dataclass
class TimeoutConfig:
    """Configuration for operation timeouts."""
    # Default timeouts in seconds for different operation types
    connection_timeout: float = 10.0
    ping_timeout: float = 5.0
    script_operation_timeout: float = 30.0
    scene_operation_timeout: float = 60.0
    gameobject_operation_timeout: float = 30.0
    asset_operation_timeout: float = 45.0
    editor_operation_timeout: float = 20.0
    console_operation_timeout: float = 10.0
    menu_operation_timeout: float = 15.0
    shader_operation_timeout: float = 30.0
    long_running_timeout: float = 300.0  # 5 minutes
    
    # Global maximum timeout (safety net)
    max_timeout: float = 600.0  # 10 minutes
    
    def get_timeout(self, operation_type: OperationType) -> float:
        """Get timeout for a specific operation type."""
        timeout_map = {
            OperationType.CONNECTION: self.connection_timeout,
            OperationType.PING: self.ping_timeout,
            OperationType.SCRIPT_OPERATION: self.script_operation_timeout,
            OperationType.SCENE_OPERATION: self.scene_operation_timeout,
            OperationType.GAMEOBJECT_OPERATION: self.gameobject_operation_timeout,
            OperationType.ASSET_OPERATION: self.asset_operation_timeout,
            OperationType.EDITOR_OPERATION: self.editor_operation_timeout,
            OperationType.CONSOLE_OPERATION: self.console_operation_timeout,
            OperationType.MENU_OPERATION: self.menu_operation_timeout,
            OperationType.SHADER_OPERATION: self.shader_operation_timeout,
            OperationType.LONG_RUNNING: self.long_running_timeout,
        }
        
        timeout = timeout_map.get(operation_type, self.script_operation_timeout)
        return min(timeout, self.max_timeout)


class TimeoutManager:
    """Manages timeouts for Unity MCP operations."""
    
    def __init__(self, config: TimeoutConfig = None):
        self.config = config or TimeoutConfig()
        self._active_operations: Dict[str, float] = {}
    
    def with_timeout(
        self,
        operation_type: OperationType,
        operation_name: str = None,
        timeout_override: float = None
    ):
        """Decorator to add timeout protection to functions."""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            if asyncio.iscoroutinefunction(func):
                return self._async_timeout_wrapper(func, operation_type, operation_name, timeout_override)
            else:
                return self._sync_timeout_wrapper(func, operation_type, operation_name, timeout_override)
        return decorator
    
    def _async_timeout_wrapper(
        self,
        func: Callable[..., Awaitable[T]],
        operation_type: OperationType,
        operation_name: str = None,
        timeout_override: float = None
    ) -> Callable[..., Awaitable[T]]:
        """Async timeout wrapper."""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            timeout = timeout_override or self.config.get_timeout(operation_type)
            op_name = operation_name or func.__name__
            
            start_time = time.time()
            operation_id = f"{op_name}_{start_time}"
            
            try:
                self._active_operations[operation_id] = start_time
                logger.debug(f"Starting operation '{op_name}' with timeout {timeout}s")
                
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
                
                elapsed = time.time() - start_time
                logger.debug(f"Operation '{op_name}' completed in {elapsed:.2f}s")
                
                return result
                
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                logger.error(f"Operation '{op_name}' timed out after {elapsed:.2f}s (limit: {timeout}s)")
                raise UnityTimeoutError(
                    f"Operation '{op_name}' timed out after {timeout} seconds",
                    timeout_seconds=timeout,
                    operation=op_name,
                    context={"elapsed_time": elapsed, "args_count": len(args), "kwargs_keys": list(kwargs.keys())}
                )
            finally:
                self._active_operations.pop(operation_id, None)
        
        return wrapper
    
    def _sync_timeout_wrapper(
        self,
        func: Callable[..., T],
        operation_type: OperationType,
        operation_name: str = None,
        timeout_override: float = None
    ) -> Callable[..., T]:
        """Sync timeout wrapper using asyncio for timeout management."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            timeout = timeout_override or self.config.get_timeout(operation_type)
            op_name = operation_name or func.__name__
            
            async def run_with_timeout():
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
            
            try:
                return asyncio.run(asyncio.wait_for(run_with_timeout(), timeout=timeout))
            except asyncio.TimeoutError:
                logger.error(f"Sync operation '{op_name}' timed out after {timeout}s")
                raise UnityTimeoutError(
                    f"Operation '{op_name}' timed out after {timeout} seconds",
                    timeout_seconds=timeout,
                    operation=op_name,
                    context={"args_count": len(args), "kwargs_keys": list(kwargs.keys())}
                )
        
        return wrapper
    
    def get_active_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active operations."""
        current_time = time.time()
        return {
            op_id: {
                "start_time": start_time,
                "elapsed_time": current_time - start_time,
                "operation_name": op_id.split('_')[0]
            }
            for op_id, start_time in self._active_operations.items()
        }
    
    def cancel_long_running_operations(self, max_age_seconds: float = 300.0):
        """Cancel operations that have been running too long."""
        current_time = time.time()
        to_cancel = [
            op_id for op_id, start_time in self._active_operations.items()
            if current_time - start_time > max_age_seconds
        ]
        
        for op_id in to_cancel:
            logger.warning(f"Cancelling long-running operation: {op_id}")
            self._active_operations.pop(op_id, None)
        
        return len(to_cancel)


# Global timeout manager instance
timeout_manager = TimeoutManager()


def with_timeout(
    operation_type: OperationType,
    operation_name: str = None,
    timeout_override: float = None
):
    """Convenience decorator for adding timeout protection."""
    return timeout_manager.with_timeout(operation_type, operation_name, timeout_override)
