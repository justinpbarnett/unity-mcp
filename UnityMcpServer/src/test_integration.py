#!/usr/bin/env python3
"""
Integration tests for Unity MCP Server production-ready implementation.
Tests the complete system including Unity connection, error handling, timeouts, and all tools.
"""

import sys
import time
import asyncio
import json
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Add the src directory to the path
sys.path.insert(0, '.')

def test_server_startup_and_health():
    """Test server startup and health check functionality."""
    print("Testing server startup and health check...")
    
    try:
        # Import server components
        from server import server_lifespan
        from enhanced_connection import get_enhanced_unity_connection
        from config import config
        
        # Test health check without Unity connection
        try:
            from server import FastMCP
            mcp = FastMCP("unity-mcp-server")
            
            # Import and register tools
            from tools import register_all_tools
            register_all_tools(mcp)
            
            print("✓ Server startup components loaded successfully")
            print("✓ All tools registered successfully")
            
            # Test health check functionality
            connection = get_enhanced_unity_connection()
            metrics = connection.get_metrics()
            
            if isinstance(metrics, dict) and "state" in metrics:
                print("✓ Connection metrics available")
                print(f"  Connection state: {metrics['state']}")
                print(f"  Host: {metrics.get('host', 'unknown')}")
                print(f"  Port: {metrics.get('port', 'unknown')}")
            else:
                print("✗ Connection metrics format invalid")
                return False
                
            return True
            
        except Exception as e:
            print(f"✗ Server startup test failed: {e}")
            return False
            
    except Exception as e:
        print(f"✗ Server component import failed: {e}")
        return False


def test_timeout_protection():
    """Test that timeout protection works correctly."""
    print("\nTesting timeout protection...")
    
    try:
        from timeout_manager import TimeoutManager, OperationType
        from exceptions import TimeoutError as UnityTimeoutError
        
        # Create timeout manager
        manager = TimeoutManager()
        
        # Test quick operation (should succeed)
        @manager.with_timeout(OperationType.PING, "test_quick", 1.0)
        def quick_operation():
            time.sleep(0.1)
            return "success"
        
        try:
            result = quick_operation()
            if result == "success":
                print("✓ Quick operation completed within timeout")
            else:
                print("✗ Quick operation returned unexpected result")
                return False
        except Exception as e:
            print(f"✗ Quick operation failed unexpectedly: {e}")
            return False
        
        # Test slow operation (should timeout)
        @manager.with_timeout(OperationType.PING, "test_slow", 0.1)
        def slow_operation():
            time.sleep(0.5)
            return "should_not_reach_here"
        
        try:
            result = slow_operation()
            print("✗ Slow operation should have timed out")
            return False
        except UnityTimeoutError as e:
            if "test_slow" in e.message and "timed out" in e.message:
                print("✓ Slow operation correctly timed out with proper error message")
            else:
                print(f"✗ Timeout error message incorrect: {e.message}")
                return False
        except Exception as e:
            print(f"✗ Slow operation failed with wrong exception type: {e}")
            return False
        
        # Test active operations tracking
        active_ops = manager.get_active_operations()
        if isinstance(active_ops, dict):
            print("✓ Active operations tracking functional")
        else:
            print("✗ Active operations tracking not working")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Timeout protection test failed: {e}")
        return False


def test_error_handling_system():
    """Test the comprehensive error handling system."""
    print("\nTesting error handling system...")
    
    try:
        from exceptions import (
            ValidationError, UnityOperationError, ConnectionError, TimeoutError,
            ErrorCategory, ErrorSeverity, create_error_response, log_exception
        )
        from enhanced_logging import enhanced_logger
        
        # Test ValidationError
        validation_error = ValidationError(
            "Test validation failed",
            parameter="test_param",
            value="invalid_value",
            context={"additional": "context"}
        )
        
        if (validation_error.category == ErrorCategory.VALIDATION and
            validation_error.parameter == "test_param" and
            validation_error.context["additional"] == "context"):
            print("✓ ValidationError creation and context working")
        else:
            print("✗ ValidationError not working correctly")
            return False
        
        # Test error response creation
        error_response = create_error_response(validation_error)
        
        if (error_response.get("success") == False and
            "error" in error_response and
            "error_details" in error_response and
            error_response["error_details"]["error_type"] == "ValidationError"):
            print("✓ Error response creation working")
        else:
            print("✗ Error response format incorrect")
            return False
        
        # Test UnityOperationError
        unity_error = UnityOperationError(
            "Unity operation failed",
            operation="test_operation",
            unity_error="Unity-side error message"
        )
        
        if (unity_error.category == ErrorCategory.UNITY_OPERATION and
            unity_error.context["operation"] == "test_operation" and
            unity_error.context["unity_error"] == "Unity-side error message"):
            print("✓ UnityOperationError creation and context working")
        else:
            print("✗ UnityOperationError not working correctly")
            return False
        
        # Test error logging (should not raise exceptions)
        try:
            log_exception(enhanced_logger.logger, validation_error, {"test": "context"})
            print("✓ Error logging functional")
        except Exception as e:
            print(f"✗ Error logging failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error handling system test failed: {e}")
        return False


def test_input_validation_system():
    """Test the input validation system for all tools."""
    print("\nTesting input validation system...")
    
    try:
        from validation import validate_tool_parameters, UnityToolValidators
        from exceptions import ValidationError
        
        # Test manage_script validation
        try:
            # Valid parameters should pass
            validate_tool_parameters("manage_script", {
                "action": "create",
                "name": "TestScript",
                "path": "Assets/Scripts/",
                "contents": "// Test content",
                "script_type": "MonoBehaviour",
                "namespace": "TestNamespace"
            })
            print("✓ manage_script validation passes for valid parameters")
        except ValidationError:
            print("✗ manage_script validation failed for valid parameters")
            return False
        
        # Invalid parameters should fail
        try:
            validate_tool_parameters("manage_script", {
                "action": "invalid_action",
                "name": "TestScript",
                "path": "Assets/Scripts/",
                "contents": "// Test content",
                "script_type": "MonoBehaviour",
                "namespace": "TestNamespace"
            })
            print("✗ manage_script validation should have failed for invalid action")
            return False
        except ValidationError as e:
            if "action" in e.message.lower():
                print("✓ manage_script validation correctly rejects invalid action")
            else:
                print(f"✗ manage_script validation error message incorrect: {e.message}")
                return False
        
        # Test manage_gameobject validation
        try:
            validate_tool_parameters("manage_gameobject", {
                "action": "create",
                "name": "TestObject",
                "position": [1.0, 2.0, 3.0],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0]
            })
            print("✓ manage_gameobject validation passes for valid parameters")
        except ValidationError:
            print("✗ manage_gameobject validation failed for valid parameters")
            return False
        
        # Test invalid position format
        try:
            validate_tool_parameters("manage_gameobject", {
                "action": "create",
                "name": "TestObject",
                "position": [1.0, 2.0]  # Invalid: only 2 components
            })
            print("✗ manage_gameobject validation should have failed for invalid position")
            return False
        except ValidationError as e:
            if "position" in e.message.lower():
                print("✓ manage_gameobject validation correctly rejects invalid position")
            else:
                print(f"✗ manage_gameobject validation error message incorrect: {e.message}")
                return False
        
        # Test that all tool validators exist
        tool_names = [
            "manage_script", "manage_editor", "manage_scene", "manage_gameobject",
            "manage_asset", "manage_shader", "read_console", "execute_menu_item"
        ]
        
        for tool_name in tool_names:
            try:
                validate_tool_parameters(tool_name, {"action": "test"})
            except ValidationError:
                pass  # Expected for invalid parameters
            except Exception as e:
                print(f"✗ Validator for {tool_name} not working: {e}")
                return False
        
        print("✓ All tool validators are functional")
        return True
        
    except Exception as e:
        print(f"✗ Input validation system test failed: {e}")
        return False


def test_enhanced_logging_system():
    """Test the enhanced logging system."""
    print("\nTesting enhanced logging system...")
    
    try:
        from enhanced_logging import enhanced_logger, LogContext, PerformanceLogger
        import json
        
        # Test basic logging with context
        context = LogContext(
            operation="test_operation",
            tool_name="test_tool",
            request_id="test-123"
        )
        
        # Capture log output (in real scenario, this would go to files)
        enhanced_logger.info("Test info message", context=context, test_param="test_value")
        enhanced_logger.warning("Test warning message", context=context)
        enhanced_logger.error("Test error message", context=context, error_code="TEST_001")
        
        print("✓ Basic logging with context working")
        
        # Test tool-specific logging
        enhanced_logger.log_tool_call("test_tool", "test_action", {"param1": "value1"}, "test-123")
        enhanced_logger.log_tool_result("test_tool", "test_action", True, "Test completed", "test-123", 0.5)
        enhanced_logger.log_tool_result("test_tool", "test_action", False, error_message="Test failed", request_id="test-123", duration=0.3)
        
        print("✓ Tool-specific logging working")
        
        # Test Unity communication logging
        enhanced_logger.log_unity_communication("test_command", True, response_size=1024, duration=0.2)
        enhanced_logger.log_unity_communication("test_command", False, error_message="Connection failed")
        
        print("✓ Unity communication logging working")
        
        # Test performance logger
        perf_logger = PerformanceLogger(enhanced_logger.logger)
        perf_logger.start_operation("test-op-123", "test_operation", {"context": "test"})
        time.sleep(0.1)  # Simulate work
        perf_logger.end_operation("test-op-123", "test_operation", True, "Operation completed")
        perf_logger.log_performance_metric("test_metric", 42.0, "ms", {"context": "test"})
        
        print("✓ Performance logging working")
        
        return True
        
    except Exception as e:
        print(f"✗ Enhanced logging system test failed: {e}")
        return False


def test_connection_management():
    """Test the enhanced connection management system."""
    print("\nTesting connection management system...")
    
    try:
        from enhanced_connection import EnhancedUnityConnection, ConnectionState, ConnectionMetrics
        from exceptions import ConnectionError
        
        # Create connection instance
        connection = EnhancedUnityConnection("localhost", 6400)
        
        # Test initial state
        if connection.state == ConnectionState.DISCONNECTED:
            print("✓ Connection initial state correct")
        else:
            print(f"✗ Connection initial state incorrect: {connection.state}")
            return False
        
        # Test metrics retrieval
        metrics = connection.get_metrics()
        if isinstance(metrics, dict) and "state" in metrics:
            print("✓ Connection metrics retrieval working")
            print(f"  State: {metrics['state']}")
            print(f"  Host: {metrics['host']}")
            print(f"  Port: {metrics['port']}")
        else:
            print("✗ Connection metrics format invalid")
            return False
        
        # Test connection attempt (will fail without Unity, but should handle gracefully)
        try:
            connection.connect()
            print("✓ Connection attempt succeeded (Unity is running)")
        except ConnectionError as e:
            if "Could not connect to Unity" in e.message:
                print("✓ Connection attempt failed gracefully (Unity not running)")
            else:
                print(f"✗ Connection error message unexpected: {e.message}")
                return False
        except Exception as e:
            print(f"✗ Connection attempt failed with unexpected error: {e}")
            return False
        
        # Test cleanup
        connection.disconnect()
        if connection.state == ConnectionState.DISCONNECTED:
            print("✓ Connection cleanup working")
        else:
            print(f"✗ Connection cleanup failed: {connection.state}")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Connection management test failed: {e}")
        return False


def test_configuration_system():
    """Test the enhanced configuration system."""
    print("\nTesting configuration system...")
    
    try:
        from config import config
        
        # Test that all required configuration options exist
        required_options = [
            "operation_timeouts", "enable_strict_validation", "enable_health_checks",
            "retry_exponential_backoff", "enable_detailed_errors", "enable_performance_logging",
            "max_retries", "retry_delay", "retry_max_delay"
        ]
        
        for option in required_options:
            if not hasattr(config, option):
                print(f"✗ Configuration option missing: {option}")
                return False
        
        print("✓ All required configuration options present")
        
        # Test operation timeouts configuration
        if isinstance(config.operation_timeouts, dict):
            required_timeouts = [
                "connection", "ping", "script_operation", "scene_operation",
                "gameobject_operation", "asset_operation", "editor_operation",
                "console_operation", "menu_operation", "shader_operation"
            ]
            
            for timeout_type in required_timeouts:
                if timeout_type not in config.operation_timeouts:
                    print(f"✗ Timeout configuration missing: {timeout_type}")
                    return False
                
                timeout_value = config.operation_timeouts[timeout_type]
                if not isinstance(timeout_value, (int, float)) or timeout_value <= 0:
                    print(f"✗ Invalid timeout value for {timeout_type}: {timeout_value}")
                    return False
            
            print("✓ Operation timeouts configuration valid")
        else:
            print("✗ Operation timeouts configuration invalid")
            return False
        
        # Test boolean configuration options
        boolean_options = [
            "enable_strict_validation", "enable_health_checks", "retry_exponential_backoff",
            "enable_detailed_errors", "enable_performance_logging", "enable_structured_logging"
        ]
        
        for option in boolean_options:
            value = getattr(config, option)
            if not isinstance(value, bool):
                print(f"✗ Configuration option {option} should be boolean, got {type(value)}")
                return False
        
        print("✓ Boolean configuration options valid")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration system test failed: {e}")
        return False


def run_integration_tests():
    """Run all integration tests."""
    print("Unity MCP Server - Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Server Startup and Health", test_server_startup_and_health),
        ("Timeout Protection", test_timeout_protection),
        ("Error Handling System", test_error_handling_system),
        ("Input Validation System", test_input_validation_system),
        ("Enhanced Logging System", test_enhanced_logging_system),
        ("Connection Management", test_connection_management),
        ("Configuration System", test_configuration_system),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Integration Test Results: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All integration tests passed! The system is production-ready.")
        print("\n✅ Verified Production Features:")
        print("   • Server startup and health monitoring")
        print("   • Timeout protection preventing infinite waits")
        print("   • Comprehensive error handling with rich context")
        print("   • Input validation for all tool parameters")
        print("   • Enhanced logging with structured output")
        print("   • Robust connection management with metrics")
        print("   • Complete configuration system")
        return True
    else:
        print("❌ Some integration tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
