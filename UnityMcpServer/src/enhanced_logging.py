"""
Enhanced logging framework for Unity MCP Server.
Provides structured logging with context, performance metrics,
and error tracking for production environments.
"""

import logging
import logging.handlers
import json
import time
import traceback
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import sys

from config import config


@dataclass
class LogContext:
    """Context information for log entries."""
    operation: Optional[str] = None
    tool_name: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    unity_connection_id: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    additional_data: Optional[Dict[str, Any]] = None


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add custom fields from extra
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class PerformanceLogger:
    """Logger for tracking operation performance."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._operation_starts: Dict[str, float] = {}
    
    def start_operation(self, operation_id: str, operation_name: str, context: Dict[str, Any] = None):
        """Start tracking an operation."""
        start_time = time.time()
        self._operation_starts[operation_id] = start_time
        
        self.logger.info(
            f"Starting operation: {operation_name}",
            extra={
                "operation_id": operation_id,
                "operation_name": operation_name,
                "operation_phase": "start",
                "context": context or {}
            }
        )
    
    def end_operation(self, operation_id: str, operation_name: str, success: bool = True, 
                     result_summary: str = None, context: Dict[str, Any] = None):
        """End tracking an operation."""
        end_time = time.time()
        start_time = self._operation_starts.pop(operation_id, end_time)
        duration = end_time - start_time
        
        log_level = logging.INFO if success else logging.ERROR
        status = "completed" if success else "failed"
        
        self.logger.log(
            log_level,
            f"Operation {status}: {operation_name} (duration: {duration:.3f}s)",
            extra={
                "operation_id": operation_id,
                "operation_name": operation_name,
                "operation_phase": "end",
                "operation_success": success,
                "operation_duration": duration,
                "result_summary": result_summary,
                "context": context or {}
            }
        )
    
    def log_performance_metric(self, metric_name: str, value: float, unit: str = None, 
                              context: Dict[str, Any] = None):
        """Log a performance metric."""
        self.logger.info(
            f"Performance metric: {metric_name} = {value}{unit or ''}",
            extra={
                "metric_name": metric_name,
                "metric_value": value,
                "metric_unit": unit,
                "metric_type": "performance",
                "context": context or {}
            }
        )


class UnityMcpLogger:
    """Enhanced logger for Unity MCP Server."""
    
    def __init__(self, name: str = "unity-mcp-server"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.performance_logger = PerformanceLogger(self.logger)
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set level
        level = getattr(logging, config.log_level.upper(), logging.INFO)
        self.logger.setLevel(level)
        
        # Console handler with structured formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler for persistent logging
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "unity_mcp_server.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(file_handler)
        
        # Error file handler for errors only
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "unity_mcp_errors.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(error_handler)
    
    def log_with_context(self, level: int, message: str, context: LogContext = None, **kwargs):
        """Log a message with structured context."""
        extra = {}
        if context:
            extra.update(asdict(context))
        extra.update(kwargs)
        
        self.logger.log(level, message, extra=extra)
    
    def info(self, message: str, context: LogContext = None, **kwargs):
        """Log info message with context."""
        self.log_with_context(logging.INFO, message, context, **kwargs)
    
    def warning(self, message: str, context: LogContext = None, **kwargs):
        """Log warning message with context."""
        self.log_with_context(logging.WARNING, message, context, **kwargs)
    
    def error(self, message: str, context: LogContext = None, exception: Exception = None, **kwargs):
        """Log error message with context and exception info."""
        if exception:
            # Avoid overwriting existing exc_info
            if "exc_info" not in kwargs:
                kwargs["exc_info"] = (type(exception), exception, exception.__traceback__)
        self.log_with_context(logging.ERROR, message, context, **kwargs)
    
    def critical(self, message: str, context: LogContext = None, exception: Exception = None, **kwargs):
        """Log critical message with context and exception info."""
        if exception:
            # Avoid overwriting existing exc_info
            if "exc_info" not in kwargs:
                kwargs["exc_info"] = (type(exception), exception, exception.__traceback__)
        self.log_with_context(logging.CRITICAL, message, context, **kwargs)
    
    def log_tool_call(self, tool_name: str, action: str, parameters: Dict[str, Any], 
                     request_id: str = None):
        """Log a tool call with parameters."""
        self.info(
            f"Tool call: {tool_name}.{action}",
            context=LogContext(
                operation=f"{tool_name}.{action}",
                tool_name=tool_name,
                request_id=request_id
            ),
            tool_action=action,
            tool_parameters=parameters
        )
    
    def log_tool_result(self, tool_name: str, action: str, success: bool, 
                       result_summary: str = None, error_message: str = None,
                       request_id: str = None, duration: float = None):
        """Log a tool result."""
        level = logging.INFO if success else logging.ERROR
        status = "success" if success else "error"
        message = f"Tool {status}: {tool_name}.{action}"
        
        if duration:
            message += f" (duration: {duration:.3f}s)"
        
        extra = {
            "tool_name": tool_name,
            "tool_action": action,
            "tool_success": success,
            "tool_duration": duration,
            "result_summary": result_summary,
            "error_message": error_message
        }
        
        self.log_with_context(
            level, 
            message,
            context=LogContext(
                operation=f"{tool_name}.{action}",
                tool_name=tool_name,
                request_id=request_id
            ),
            **extra
        )
    
    def log_unity_communication(self, command_type: str, success: bool, 
                               response_size: int = None, duration: float = None,
                               error_message: str = None):
        """Log Unity communication events."""
        level = logging.DEBUG if success else logging.ERROR
        status = "success" if success else "error"
        message = f"Unity communication {status}: {command_type}"
        
        extra = {
            "unity_command": command_type,
            "unity_success": success,
            "unity_response_size": response_size,
            "unity_duration": duration,
            "unity_error": error_message
        }
        
        self.logger.log(level, message, extra=extra)


# Global logger instance
enhanced_logger = UnityMcpLogger()
