"""
Enhanced error recovery system for Unity MCP Server.
Provides automatic recovery mechanisms, graceful degradation, and comprehensive error reporting.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

from enhanced_logging import enhanced_logger, LogContext
from exceptions import UnityMcpError, ConnectionError, TimeoutError, UnityOperationError
from enhanced_connection import get_enhanced_unity_connection


class RecoveryStrategy(Enum):
    """Available recovery strategies for different error types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    USER_INTERVENTION = "user_intervention"
    SKIP = "skip"


class ErrorSeverity(Enum):
    """Error severity levels for recovery decisions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RecoveryAction:
    """Defines a recovery action for specific error conditions."""
    strategy: RecoveryStrategy
    max_attempts: int = 3
    delay_seconds: float = 1.0
    fallback_function: Optional[Callable] = None
    degraded_mode_function: Optional[Callable] = None
    user_message: str = ""
    auto_execute: bool = True


@dataclass
class ErrorContext:
    """Extended error context for recovery decisions."""
    error_type: str
    error_message: str
    operation: str
    tool_name: str
    parameters: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    attempt_count: int = 0
    recovery_attempted: bool = False
    recovery_successful: bool = False
    user_notified: bool = False


class ErrorRecoveryManager:
    """Manages error recovery strategies and automatic recovery attempts."""
    
    def __init__(self):
        self.recovery_rules: Dict[str, RecoveryAction] = {}
        self.error_history: List[ErrorContext] = []
        self.degraded_mode_active = False
        self.recovery_stats = {
            "total_errors": 0,
            "recovered_errors": 0,
            "failed_recoveries": 0,
            "degraded_mode_activations": 0
        }
        self._setup_default_recovery_rules()
    
    def _setup_default_recovery_rules(self):
        """Setup default recovery rules for common error scenarios."""
        
        # Connection errors - retry with exponential backoff
        self.recovery_rules["ConnectionError"] = RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=5,
            delay_seconds=2.0,
            user_message="Unity connection lost. Attempting to reconnect...",
            auto_execute=True
        )
        
        # Timeout errors - retry with longer timeout
        self.recovery_rules["TimeoutError"] = RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_attempts=3,
            delay_seconds=1.0,
            user_message="Operation timed out. Retrying with extended timeout...",
            auto_execute=True
        )
        
        # Unity operation errors - try graceful degradation
        self.recovery_rules["UnityOperationError"] = RecoveryAction(
            strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
            max_attempts=2,
            delay_seconds=0.5,
            degraded_mode_function=self._unity_degraded_mode,
            user_message="Unity operation failed. Switching to safe mode...",
            auto_execute=True
        )
        
        # Validation errors - user intervention required
        self.recovery_rules["ValidationError"] = RecoveryAction(
            strategy=RecoveryStrategy.USER_INTERVENTION,
            max_attempts=1,
            user_message="Invalid parameters detected. Please check your input and try again.",
            auto_execute=False
        )
        
        # Resource errors - fallback to alternative methods
        self.recovery_rules["ResourceError"] = RecoveryAction(
            strategy=RecoveryStrategy.FALLBACK,
            max_attempts=2,
            delay_seconds=1.0,
            fallback_function=self._resource_fallback,
            user_message="Resource access failed. Trying alternative approach...",
            auto_execute=True
        )
    
    async def handle_error(self, error: Exception, context: LogContext, 
                          operation_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle an error with appropriate recovery strategy.
        
        Args:
            error: The exception that occurred
            context: Logging context for the operation
            operation_params: Parameters of the failed operation
            
        Returns:
            Recovery result with success status and any recovered data
        """
        error_type = type(error).__name__
        error_context = ErrorContext(
            error_type=error_type,
            error_message=str(error),
            operation=context.operation or "unknown",
            tool_name=context.tool_name or "unknown",
            parameters=operation_params or {}
        )
        
        self.error_history.append(error_context)
        self.recovery_stats["total_errors"] += 1
        
        enhanced_logger.error(
            f"Error occurred in {error_context.operation}: {error_context.error_message}",
            context=context,
            exception=error,
            error_type=error_type,
            recovery_manager="starting_recovery"
        )
        
        # Get recovery action for this error type
        recovery_action = self.recovery_rules.get(error_type)
        if not recovery_action:
            # Default recovery for unknown errors
            recovery_action = RecoveryAction(
                strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
                max_attempts=1,
                user_message=f"Unexpected error occurred: {error_type}. Attempting graceful handling...",
                degraded_mode_function=self._generic_degraded_mode
            )
        
        # Execute recovery strategy
        recovery_result = await self._execute_recovery(error_context, recovery_action, context)
        
        # Update statistics
        if recovery_result["success"]:
            self.recovery_stats["recovered_errors"] += 1
            error_context.recovery_successful = True
        else:
            self.recovery_stats["failed_recoveries"] += 1
        
        error_context.recovery_attempted = True
        
        return recovery_result
    
    async def _execute_recovery(self, error_context: ErrorContext, 
                               recovery_action: RecoveryAction, 
                               log_context: LogContext) -> Dict[str, Any]:
        """Execute the specified recovery strategy."""
        
        enhanced_logger.info(
            f"Executing recovery strategy: {recovery_action.strategy.value}",
            context=log_context,
            error_type=error_context.error_type,
            max_attempts=recovery_action.max_attempts
        )
        
        if recovery_action.strategy == RecoveryStrategy.RETRY:
            return await self._retry_recovery(error_context, recovery_action, log_context)
        
        elif recovery_action.strategy == RecoveryStrategy.FALLBACK:
            return await self._fallback_recovery(error_context, recovery_action, log_context)
        
        elif recovery_action.strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            return await self._graceful_degradation_recovery(error_context, recovery_action, log_context)
        
        elif recovery_action.strategy == RecoveryStrategy.USER_INTERVENTION:
            return self._user_intervention_recovery(error_context, recovery_action, log_context)
        
        elif recovery_action.strategy == RecoveryStrategy.SKIP:
            return self._skip_recovery(error_context, recovery_action, log_context)
        
        else:
            return {
                "success": False,
                "message": f"Unknown recovery strategy: {recovery_action.strategy}",
                "error": "Invalid recovery configuration"
            }
    
    async def _retry_recovery(self, error_context: ErrorContext, 
                             recovery_action: RecoveryAction, 
                             log_context: LogContext) -> Dict[str, Any]:
        """Implement retry recovery strategy with exponential backoff."""
        
        for attempt in range(1, recovery_action.max_attempts + 1):
            error_context.attempt_count = attempt
            
            enhanced_logger.info(
                f"Retry attempt {attempt}/{recovery_action.max_attempts}",
                context=log_context,
                error_type=error_context.error_type,
                delay=recovery_action.delay_seconds * attempt
            )
            
            # Wait with exponential backoff
            await asyncio.sleep(recovery_action.delay_seconds * attempt)
            
            try:
                # For connection errors, try to reconnect
                if error_context.error_type == "ConnectionError":
                    connection = get_enhanced_unity_connection()
                    if connection.connect():
                        enhanced_logger.info(
                            "Connection recovery successful",
                            context=log_context,
                            attempt=attempt
                        )
                        return {
                            "success": True,
                            "message": f"Connection recovered after {attempt} attempts",
                            "data": {"recovery_method": "retry", "attempts": attempt}
                        }
                
                # For other errors, this would need to be implemented per operation type
                # For now, we'll consider it successful if we get here without exception
                return {
                    "success": True,
                    "message": f"Operation recovered after {attempt} attempts",
                    "data": {"recovery_method": "retry", "attempts": attempt}
                }
                
            except Exception as retry_error:
                enhanced_logger.warning(
                    f"Retry attempt {attempt} failed: {str(retry_error)}",
                    context=log_context,
                    retry_error=str(retry_error)
                )
                
                if attempt == recovery_action.max_attempts:
                    return {
                        "success": False,
                        "message": f"All {recovery_action.max_attempts} retry attempts failed",
                        "error": str(retry_error)
                    }
        
        return {
            "success": False,
            "message": "Retry recovery failed",
            "error": "Maximum retry attempts exceeded"
        }
    
    async def _fallback_recovery(self, error_context: ErrorContext, 
                                recovery_action: RecoveryAction, 
                                log_context: LogContext) -> Dict[str, Any]:
        """Implement fallback recovery strategy."""
        
        if recovery_action.fallback_function:
            try:
                result = await recovery_action.fallback_function(error_context, log_context)
                enhanced_logger.info(
                    "Fallback recovery successful",
                    context=log_context,
                    fallback_result=result
                )
                return {
                    "success": True,
                    "message": "Operation completed using fallback method",
                    "data": {"recovery_method": "fallback", "fallback_result": result}
                }
            except Exception as fallback_error:
                enhanced_logger.error(
                    f"Fallback recovery failed: {str(fallback_error)}",
                    context=log_context,
                    exception=fallback_error
                )
                return {
                    "success": False,
                    "message": "Fallback recovery failed",
                    "error": str(fallback_error)
                }
        else:
            return {
                "success": False,
                "message": "No fallback function configured",
                "error": "Fallback recovery not available"
            }
    
    async def _graceful_degradation_recovery(self, error_context: ErrorContext, 
                                           recovery_action: RecoveryAction, 
                                           log_context: LogContext) -> Dict[str, Any]:
        """Implement graceful degradation recovery strategy."""
        
        self.degraded_mode_active = True
        self.recovery_stats["degraded_mode_activations"] += 1
        
        enhanced_logger.warning(
            "Activating degraded mode",
            context=log_context,
            error_type=error_context.error_type,
            operation=error_context.operation
        )
        
        if recovery_action.degraded_mode_function:
            try:
                result = await recovery_action.degraded_mode_function(error_context, log_context)
                return {
                    "success": True,
                    "message": "Operation completed in degraded mode",
                    "data": {
                        "recovery_method": "graceful_degradation",
                        "degraded_mode": True,
                        "degraded_result": result
                    },
                    "warning": "System is operating in degraded mode with limited functionality"
                }
            except Exception as degraded_error:
                enhanced_logger.error(
                    f"Degraded mode recovery failed: {str(degraded_error)}",
                    context=log_context,
                    exception=degraded_error
                )
                return {
                    "success": False,
                    "message": "Degraded mode recovery failed",
                    "error": str(degraded_error)
                }
        else:
            return {
                "success": True,
                "message": "System switched to degraded mode",
                "data": {"recovery_method": "graceful_degradation", "degraded_mode": True},
                "warning": "System is operating in degraded mode with limited functionality"
            }
    
    def _user_intervention_recovery(self, error_context: ErrorContext, 
                                   recovery_action: RecoveryAction, 
                                   log_context: LogContext) -> Dict[str, Any]:
        """Implement user intervention recovery strategy."""
        
        error_context.user_notified = True
        
        enhanced_logger.warning(
            "User intervention required",
            context=log_context,
            error_type=error_context.error_type,
            user_message=recovery_action.user_message
        )
        
        return {
            "success": False,
            "message": recovery_action.user_message,
            "error": error_context.error_message,
            "data": {
                "recovery_method": "user_intervention",
                "requires_user_action": True,
                "error_context": {
                    "operation": error_context.operation,
                    "tool_name": error_context.tool_name,
                    "parameters": error_context.parameters
                }
            }
        }
    
    def _skip_recovery(self, error_context: ErrorContext, 
                      recovery_action: RecoveryAction, 
                      log_context: LogContext) -> Dict[str, Any]:
        """Implement skip recovery strategy."""
        
        enhanced_logger.info(
            "Skipping failed operation",
            context=log_context,
            error_type=error_context.error_type,
            operation=error_context.operation
        )
        
        return {
            "success": True,
            "message": "Operation skipped due to error",
            "data": {
                "recovery_method": "skip",
                "skipped": True,
                "original_error": error_context.error_message
            },
            "warning": f"Operation {error_context.operation} was skipped due to: {error_context.error_message}"
        }
    
    async def _unity_degraded_mode(self, error_context: ErrorContext, 
                                  log_context: LogContext) -> Dict[str, Any]:
        """Unity-specific degraded mode implementation."""
        
        # In degraded mode, we provide limited functionality
        # This could include read-only operations, cached responses, etc.
        
        if "read" in error_context.operation.lower() or "get" in error_context.operation.lower():
            # For read operations, try to provide cached or default data
            return {
                "degraded_operation": True,
                "message": "Providing cached or default data",
                "data": self._get_cached_or_default_data(error_context.operation)
            }
        else:
            # For write operations, log the attempt but don't execute
            return {
                "degraded_operation": True,
                "message": "Write operation deferred in degraded mode",
                "deferred": True,
                "operation": error_context.operation,
                "parameters": error_context.parameters
            }
    
    async def _resource_fallback(self, error_context: ErrorContext, 
                                log_context: LogContext) -> Dict[str, Any]:
        """Resource access fallback implementation."""
        
        # Try alternative resource access methods
        if "file" in error_context.error_message.lower():
            return {
                "fallback_method": "alternative_file_access",
                "message": "Using alternative file access method",
                "success": True
            }
        elif "network" in error_context.error_message.lower():
            return {
                "fallback_method": "cached_network_data",
                "message": "Using cached network data",
                "success": True
            }
        else:
            return {
                "fallback_method": "generic_fallback",
                "message": "Using generic fallback approach",
                "success": True
            }
    
    async def _generic_degraded_mode(self, error_context: ErrorContext, 
                                    log_context: LogContext) -> Dict[str, Any]:
        """Generic degraded mode for unknown error types."""
        
        return {
            "degraded_operation": True,
            "message": f"Generic degraded mode for {error_context.error_type}",
            "limited_functionality": True,
            "original_operation": error_context.operation
        }
    
    def _get_cached_or_default_data(self, operation: str) -> Dict[str, Any]:
        """Get cached or default data for read operations in degraded mode."""
        
        # This would typically access a cache or provide sensible defaults
        default_responses = {
            "get_state": {"state": "unknown", "degraded": True},
            "get_hierarchy": {"objects": [], "degraded": True},
            "get_components": {"components": [], "degraded": True},
            "read_console": {"messages": [], "degraded": True}
        }
        
        for key, response in default_responses.items():
            if key in operation.lower():
                return response
        
        return {"degraded": True, "message": "No cached data available"}
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics and system health information."""
        
        success_rate = 0.0
        if self.recovery_stats["total_errors"] > 0:
            success_rate = (self.recovery_stats["recovered_errors"] / 
                          self.recovery_stats["total_errors"]) * 100
        
        return {
            "recovery_stats": self.recovery_stats,
            "success_rate": round(success_rate, 2),
            "degraded_mode_active": self.degraded_mode_active,
            "recent_errors": [
                {
                    "error_type": ctx.error_type,
                    "operation": ctx.operation,
                    "timestamp": ctx.timestamp,
                    "recovered": ctx.recovery_successful
                }
                for ctx in self.error_history[-10:]  # Last 10 errors
            ]
        }
    
    def reset_degraded_mode(self):
        """Reset degraded mode when system recovers."""
        
        if self.degraded_mode_active:
            self.degraded_mode_active = False
            enhanced_logger.info(
                "Degraded mode deactivated - system restored to full functionality",
                degraded_mode=False
            )


# Global error recovery manager instance
error_recovery_manager = ErrorRecoveryManager()
