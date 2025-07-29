"""
Custom exception hierarchy for Unity MCP Server.
Provides specific exception types for different error scenarios to enable
better error handling, logging, and user feedback.
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors for better classification."""
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    UNITY_OPERATION = "unity_operation"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    INTERNAL = "internal"


class UnityMcpError(Exception):
    """Base exception class for Unity MCP Server errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.error_code = error_code or self._generate_error_code()
        self.context = context or {}
        self.cause = cause
        
    def _generate_error_code(self) -> str:
        """Generate a unique error code based on category and class name."""
        class_name = self.__class__.__name__
        return f"{self.category.value.upper()}_{class_name.upper()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "error_code": self.error_code,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None
        }


class ConnectionError(UnityMcpError):
    """Raised when Unity connection fails or is lost."""
    
    def __init__(self, message: str, host: str = None, port: int = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONNECTION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        if host:
            self.context["host"] = host
        if port:
            self.context["port"] = port


class TimeoutError(UnityMcpError):
    """Raised when operations exceed their timeout limits."""
    
    def __init__(self, message: str, timeout_seconds: float = None, operation: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        if timeout_seconds:
            self.context["timeout_seconds"] = timeout_seconds
        if operation:
            self.context["operation"] = operation


class ValidationError(UnityMcpError):
    """Raised when input validation fails."""

    def __init__(self, message: str, parameter: str = None, value: Any = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        self.parameter = parameter  # Store as direct attribute for backward compatibility
        if parameter:
            self.context["parameter"] = parameter
        if value is not None:
            self.context["value"] = str(value)


class UnityOperationError(UnityMcpError):
    """Raised when Unity operations fail."""
    
    def __init__(self, message: str, operation: str = None, unity_error: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.UNITY_OPERATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        if operation:
            self.context["operation"] = operation
        if unity_error:
            self.context["unity_error"] = unity_error


class ResourceError(UnityMcpError):
    """Raised when resource operations fail (file I/O, memory, etc.)."""
    
    def __init__(self, message: str, resource_type: str = None, resource_path: str = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )
        if resource_type:
            self.context["resource_type"] = resource_type
        if resource_path:
            self.context["resource_path"] = resource_path


class ConfigurationError(UnityMcpError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: str = None, config_value: Any = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )
        if config_key:
            self.context["config_key"] = config_key
        if config_value is not None:
            self.context["config_value"] = str(config_value)


def log_exception(logger: logging.Logger, exception: UnityMcpError, extra_context: Dict[str, Any] = None):
    """Log an exception with full context information."""
    context = {**exception.context}
    if extra_context:
        context.update(extra_context)
    
    log_level = {
        ErrorSeverity.LOW: logging.INFO,
        ErrorSeverity.MEDIUM: logging.WARNING,
        ErrorSeverity.HIGH: logging.ERROR,
        ErrorSeverity.CRITICAL: logging.CRITICAL
    }.get(exception.severity, logging.ERROR)
    
    logger.log(
        log_level,
        f"[{exception.error_code}] {exception.message}",
        extra={
            "error_category": exception.category.value,
            "error_severity": exception.severity.value,
            "error_code": exception.error_code,
            "error_context": context,
            "error_cause": str(exception.cause) if exception.cause else None
        }
    )


def create_error_response(exception: UnityMcpError) -> Dict[str, Any]:
    """Create a standardized error response from an exception."""
    return {
        "success": False,
        "error": exception.message,
        "error_details": exception.to_dict()
    }
