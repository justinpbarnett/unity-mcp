"""
Advanced logging system with filtering, export, and debugging capabilities.
Extends the enhanced logging system with additional features for development and production.
"""

import json
import csv
import time
import os
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import gzip
import threading
from collections import defaultdict, deque

from enhanced_logging import enhanced_logger, LogContext


class LogLevel(Enum):
    """Extended log levels for advanced filtering."""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """Log categories for better organization."""
    SYSTEM = "system"
    UNITY_COMMUNICATION = "unity_communication"
    TOOL_EXECUTION = "tool_execution"
    ERROR_RECOVERY = "error_recovery"
    PERFORMANCE = "performance"
    USER_ACTION = "user_action"
    SECURITY = "security"
    DEBUG = "debug"


@dataclass
class LogFilter:
    """Configuration for log filtering."""
    levels: List[LogLevel] = None
    categories: List[LogCategory] = None
    tools: List[str] = None
    time_range: tuple = None  # (start_time, end_time)
    search_text: str = None
    user_id: str = None
    session_id: str = None
    include_performance: bool = True
    include_errors_only: bool = False
    max_entries: int = 1000


@dataclass
class LogEntry:
    """Structured log entry for advanced logging."""
    timestamp: float
    level: LogLevel
    category: LogCategory
    message: str
    tool_name: str = None
    operation: str = None
    user_id: str = None
    session_id: str = None
    request_id: str = None
    duration: float = None
    success: bool = None
    error_type: str = None
    recovery_applied: bool = False
    performance_metrics: Dict[str, Any] = None
    additional_data: Dict[str, Any] = None


class AdvancedLogManager:
    """Advanced logging manager with filtering, export, and analysis capabilities."""
    
    def __init__(self, max_memory_entries: int = 10000):
        self.max_memory_entries = max_memory_entries
        self.memory_logs: deque = deque(maxlen=max_memory_entries)
        self.log_statistics = defaultdict(int)
        self.performance_metrics = defaultdict(list)
        self.error_patterns = defaultdict(int)
        self.lock = threading.Lock()
        
        # Export settings
        self.export_directory = "logs/exports"
        os.makedirs(self.export_directory, exist_ok=True)
        
        # Real-time monitoring
        self.real_time_filters: List[LogFilter] = []
        self.real_time_callbacks: List[callable] = []
    
    def log_advanced(self, level: LogLevel, category: LogCategory, message: str,
                    tool_name: str = None, operation: str = None,
                    user_id: str = None, session_id: str = None,
                    request_id: str = None, duration: float = None,
                    success: bool = None, error_type: str = None,
                    recovery_applied: bool = False,
                    performance_metrics: Dict[str, Any] = None,
                    **additional_data) -> None:
        """Log an entry with advanced metadata."""
        
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            category=category,
            message=message,
            tool_name=tool_name,
            operation=operation,
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            duration=duration,
            success=success,
            error_type=error_type,
            recovery_applied=recovery_applied,
            performance_metrics=performance_metrics,
            additional_data=additional_data if additional_data else None
        )
        
        with self.lock:
            # Add to memory storage
            self.memory_logs.append(entry)
            
            # Update statistics
            self.log_statistics[f"level_{level.value}"] += 1
            self.log_statistics[f"category_{category.value}"] += 1
            if tool_name:
                self.log_statistics[f"tool_{tool_name}"] += 1
            if error_type:
                self.error_patterns[error_type] += 1
            if duration is not None and operation:
                self.performance_metrics[operation].append(duration)
        
        # Also log to the enhanced logger
        log_context = LogContext(
            operation=operation,
            tool_name=tool_name,
            user_id=user_id,
            session_id=session_id,
            request_id=request_id
        )
        
        # Map to enhanced logger levels
        if level == LogLevel.TRACE or level == LogLevel.DEBUG:
            enhanced_logger.debug(message, context=log_context, **additional_data)
        elif level == LogLevel.INFO:
            enhanced_logger.info(message, context=log_context, **additional_data)
        elif level == LogLevel.WARNING:
            enhanced_logger.warning(message, context=log_context, **additional_data)
        elif level == LogLevel.ERROR:
            enhanced_logger.error(message, context=log_context, **additional_data)
        elif level == LogLevel.CRITICAL:
            enhanced_logger.critical(message, context=log_context, **additional_data)
        
        # Check real-time filters and trigger callbacks
        self._check_real_time_filters(entry)
    
    def filter_logs(self, log_filter: LogFilter) -> List[LogEntry]:
        """Filter logs based on the provided criteria."""
        
        with self.lock:
            filtered_logs = list(self.memory_logs)
        
        # Apply level filter
        if log_filter.levels:
            filtered_logs = [log for log in filtered_logs if log.level in log_filter.levels]
        
        # Apply category filter
        if log_filter.categories:
            filtered_logs = [log for log in filtered_logs if log.category in log_filter.categories]
        
        # Apply tool filter
        if log_filter.tools:
            filtered_logs = [log for log in filtered_logs if log.tool_name in log_filter.tools]
        
        # Apply time range filter
        if log_filter.time_range:
            start_time, end_time = log_filter.time_range
            filtered_logs = [log for log in filtered_logs 
                           if start_time <= log.timestamp <= end_time]
        
        # Apply search text filter
        if log_filter.search_text:
            search_lower = log_filter.search_text.lower()
            filtered_logs = [log for log in filtered_logs 
                           if search_lower in log.message.lower() or
                           (log.tool_name and search_lower in log.tool_name.lower()) or
                           (log.operation and search_lower in log.operation.lower())]
        
        # Apply user filter
        if log_filter.user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == log_filter.user_id]
        
        # Apply session filter
        if log_filter.session_id:
            filtered_logs = [log for log in filtered_logs if log.session_id == log_filter.session_id]
        
        # Apply errors only filter
        if log_filter.include_errors_only:
            filtered_logs = [log for log in filtered_logs 
                           if log.level in [LogLevel.ERROR, LogLevel.CRITICAL] or log.success is False]
        
        # Apply performance filter
        if not log_filter.include_performance:
            filtered_logs = [log for log in filtered_logs if log.category != LogCategory.PERFORMANCE]
        
        # Limit results
        if log_filter.max_entries and len(filtered_logs) > log_filter.max_entries:
            # Keep most recent entries
            filtered_logs = filtered_logs[-log_filter.max_entries:]
        
        return filtered_logs
    
    def export_logs(self, log_filter: LogFilter, format: str = "json", 
                   filename: str = None, compress: bool = False) -> str:
        """Export filtered logs to various formats."""
        
        filtered_logs = self.filter_logs(log_filter)
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"unity_mcp_logs_{timestamp}.{format}"
        
        filepath = os.path.join(self.export_directory, filename)
        
        if format.lower() == "json":
            self._export_json(filtered_logs, filepath, compress)
        elif format.lower() == "csv":
            self._export_csv(filtered_logs, filepath, compress)
        elif format.lower() == "txt":
            self._export_text(filtered_logs, filepath, compress)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        return filepath
    
    def _export_json(self, logs: List[LogEntry], filepath: str, compress: bool):
        """Export logs as JSON."""
        
        log_data = []
        for log in logs:
            log_dict = asdict(log)
            # Convert enum values to strings
            log_dict["level"] = log.level.value
            log_dict["category"] = log.category.value
            # Convert timestamp to readable format
            log_dict["timestamp_readable"] = datetime.fromtimestamp(log.timestamp).isoformat()
            log_data.append(log_dict)
        
        export_data = {
            "export_info": {
                "timestamp": datetime.now().isoformat(),
                "total_entries": len(log_data),
                "format": "json"
            },
            "logs": log_data
        }
        
        if compress:
            with gzip.open(f"{filepath}.gz", "wt", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str)
            filepath = f"{filepath}.gz"
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str)
    
    def _export_csv(self, logs: List[LogEntry], filepath: str, compress: bool):
        """Export logs as CSV."""
        
        if not logs:
            return
        
        fieldnames = [
            "timestamp", "timestamp_readable", "level", "category", "message",
            "tool_name", "operation", "user_id", "session_id", "request_id",
            "duration", "success", "error_type", "recovery_applied"
        ]
        
        def write_csv(file_handle):
            writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
            writer.writeheader()
            
            for log in logs:
                row = {
                    "timestamp": log.timestamp,
                    "timestamp_readable": datetime.fromtimestamp(log.timestamp).isoformat(),
                    "level": log.level.value,
                    "category": log.category.value,
                    "message": log.message,
                    "tool_name": log.tool_name or "",
                    "operation": log.operation or "",
                    "user_id": log.user_id or "",
                    "session_id": log.session_id or "",
                    "request_id": log.request_id or "",
                    "duration": log.duration or "",
                    "success": log.success if log.success is not None else "",
                    "error_type": log.error_type or "",
                    "recovery_applied": log.recovery_applied
                }
                writer.writerow(row)
        
        if compress:
            with gzip.open(f"{filepath}.gz", "wt", encoding="utf-8", newline="") as f:
                write_csv(f)
            filepath = f"{filepath}.gz"
        else:
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                write_csv(f)
    
    def _export_text(self, logs: List[LogEntry], filepath: str, compress: bool):
        """Export logs as human-readable text."""
        
        def write_text(file_handle):
            file_handle.write(f"Unity MCP Server Log Export\n")
            file_handle.write(f"Generated: {datetime.now().isoformat()}\n")
            file_handle.write(f"Total Entries: {len(logs)}\n")
            file_handle.write("=" * 80 + "\n\n")
            
            for log in logs:
                timestamp_readable = datetime.fromtimestamp(log.timestamp).strftime("%Y-%m-%d %H:%M:%S")
                file_handle.write(f"[{timestamp_readable}] {log.level.value} - {log.category.value}\n")
                file_handle.write(f"Message: {log.message}\n")
                
                if log.tool_name:
                    file_handle.write(f"Tool: {log.tool_name}\n")
                if log.operation:
                    file_handle.write(f"Operation: {log.operation}\n")
                if log.duration is not None:
                    file_handle.write(f"Duration: {log.duration:.3f}s\n")
                if log.success is not None:
                    file_handle.write(f"Success: {log.success}\n")
                if log.error_type:
                    file_handle.write(f"Error Type: {log.error_type}\n")
                if log.recovery_applied:
                    file_handle.write(f"Recovery Applied: Yes\n")
                
                file_handle.write("-" * 40 + "\n")
        
        if compress:
            with gzip.open(f"{filepath}.gz", "wt", encoding="utf-8") as f:
                write_text(f)
            filepath = f"{filepath}.gz"
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                write_text(f)
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get comprehensive log statistics."""
        
        with self.lock:
            stats = dict(self.log_statistics)
            error_patterns = dict(self.error_patterns)
            
            # Calculate performance statistics
            perf_stats = {}
            for operation, durations in self.performance_metrics.items():
                if durations:
                    perf_stats[operation] = {
                        "count": len(durations),
                        "avg_duration": sum(durations) / len(durations),
                        "min_duration": min(durations),
                        "max_duration": max(durations)
                    }
        
        return {
            "total_entries": len(self.memory_logs),
            "statistics": stats,
            "error_patterns": error_patterns,
            "performance_statistics": perf_stats,
            "memory_usage": {
                "current_entries": len(self.memory_logs),
                "max_entries": self.max_memory_entries,
                "usage_percentage": (len(self.memory_logs) / self.max_memory_entries) * 100
            }
        }
    
    def add_real_time_filter(self, log_filter: LogFilter, callback: callable):
        """Add a real-time filter with callback for monitoring."""
        
        self.real_time_filters.append(log_filter)
        self.real_time_callbacks.append(callback)
    
    def _check_real_time_filters(self, entry: LogEntry):
        """Check if entry matches any real-time filters and trigger callbacks."""
        
        for i, log_filter in enumerate(self.real_time_filters):
            if self._matches_filter(entry, log_filter):
                try:
                    self.real_time_callbacks[i](entry)
                except Exception as e:
                    # Don't let callback errors break logging
                    enhanced_logger.error(f"Real-time callback error: {e}")
    
    def _matches_filter(self, entry: LogEntry, log_filter: LogFilter) -> bool:
        """Check if a log entry matches the given filter."""
        
        if log_filter.levels and entry.level not in log_filter.levels:
            return False
        
        if log_filter.categories and entry.category not in log_filter.categories:
            return False
        
        if log_filter.tools and entry.tool_name not in log_filter.tools:
            return False
        
        if log_filter.user_id and entry.user_id != log_filter.user_id:
            return False
        
        if log_filter.session_id and entry.session_id != log_filter.session_id:
            return False
        
        if log_filter.include_errors_only:
            if entry.level not in [LogLevel.ERROR, LogLevel.CRITICAL] and entry.success is not False:
                return False
        
        if log_filter.search_text:
            search_lower = log_filter.search_text.lower()
            if not (search_lower in entry.message.lower() or
                   (entry.tool_name and search_lower in entry.tool_name.lower()) or
                   (entry.operation and search_lower in entry.operation.lower())):
                return False
        
        return True
    
    def clear_logs(self, older_than_hours: int = None):
        """Clear logs from memory, optionally keeping recent entries."""
        
        with self.lock:
            if older_than_hours:
                cutoff_time = time.time() - (older_than_hours * 3600)
                # Keep logs newer than cutoff
                self.memory_logs = deque(
                    [log for log in self.memory_logs if log.timestamp > cutoff_time],
                    maxlen=self.max_memory_entries
                )
            else:
                self.memory_logs.clear()
            
            # Reset statistics
            self.log_statistics.clear()
            self.error_patterns.clear()
            self.performance_metrics.clear()


# Global advanced log manager instance
advanced_log_manager = AdvancedLogManager()
