#!/usr/bin/env python3
"""
Test script to validate Unity MCP Server improvements.
Tests error handling, timeouts, validation, and connection management.
"""

import sys
import time
import json
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, '.')

def test_imports():
    """Test that all new modules can be imported."""
    print("Testing imports...")
    
    try:
        from exceptions import (
            UnityMcpError, ConnectionError, TimeoutError, ValidationError,
            UnityOperationError, ResourceError, ConfigurationError
        )
        print("✓ Exception classes imported successfully")
        
        from timeout_manager import TimeoutManager, OperationType, with_timeout
        print("✓ Timeout manager imported successfully")
        
        from enhanced_logging import enhanced_logger, LogContext
        print("✓ Enhanced logging imported successfully")
        
        from validation import (
            ToolValidator, ValidationRule, validate_tool_parameters,
            UnityToolValidators
        )
        print("✓ Validation framework imported successfully")
        
        from enhanced_connection import EnhancedUnityConnection, get_enhanced_unity_connection
        print("✓ Enhanced connection imported successfully")
        
        from config import config
        print("✓ Enhanced config imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_exception_hierarchy():
    """Test the custom exception hierarchy."""
    print("\nTesting exception hierarchy...")
    
    try:
        from exceptions import (
            UnityMcpError, ConnectionError, ValidationError, 
            ErrorCategory, ErrorSeverity, create_error_response
        )
        
        # Test base exception
        base_error = UnityMcpError(
            "Test error",
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.HIGH,
            context={"test": "data"}
        )
        
        assert base_error.message == "Test error"
        assert base_error.category == ErrorCategory.INTERNAL
        assert base_error.severity == ErrorSeverity.HIGH
        assert base_error.context["test"] == "data"
        print("✓ Base exception works correctly")
        
        # Test specific exception
        conn_error = ConnectionError(
            "Connection failed",
            host="localhost",
            port=6400
        )
        
        assert conn_error.category == ErrorCategory.CONNECTION
        assert conn_error.context["host"] == "localhost"
        assert conn_error.context["port"] == 6400
        print("✓ Connection exception works correctly")
        
        # Test error response creation
        response = create_error_response(conn_error)
        assert response["success"] == False
        assert "error" in response
        assert "error_details" in response
        print("✓ Error response creation works correctly")
        
        return True
        
    except Exception as e:
        print(f"✗ Exception hierarchy test failed: {e}")
        return False


def test_validation_framework():
    """Test the input validation framework."""
    print("\nTesting validation framework...")
    
    try:
        from validation import (
            ToolValidator, ValidationRule, ValidationType,
            required, type_check, choices_check,
            UnityToolValidators, validate_tool_parameters
        )
        from exceptions import ValidationError
        
        # Test basic validation rules
        validator = ToolValidator("test_tool")
        validator.add_parameter("action", [
            required(),
            type_check(str),
            choices_check(["create", "read", "update", "delete"])
        ])
        
        # Test valid parameters
        try:
            validator.validate({"action": "create"})
            print("✓ Valid parameters pass validation")
        except ValidationError:
            print("✗ Valid parameters failed validation")
            return False
        
        # Test invalid parameters
        try:
            validator.validate({"action": "invalid"})
            print("✗ Invalid parameters should fail validation")
            return False
        except ValidationError:
            print("✓ Invalid parameters correctly fail validation")
        
        # Test tool-specific validators
        try:
            script_validator = UnityToolValidators.create_manage_script_validator()
            assert script_validator is not None
            print("✓ Tool-specific validators created successfully")
        except Exception as e:
            print(f"✗ Tool-specific validator creation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Validation framework test failed: {e}")
        return False


def test_timeout_manager():
    """Test the timeout management system."""
    print("\nTesting timeout manager...")
    
    try:
        from timeout_manager import TimeoutManager, OperationType, with_timeout
        from exceptions import TimeoutError
        
        # Create timeout manager
        manager = TimeoutManager()
        
        # Test timeout decorator on a function that completes quickly
        @manager.with_timeout(OperationType.PING, "test_quick", 1.0)
        def quick_function():
            time.sleep(0.1)
            return "success"
        
        result = quick_function()
        assert result == "success"
        print("✓ Quick function completes within timeout")
        
        # Test timeout decorator on a function that times out
        @manager.with_timeout(OperationType.PING, "test_slow", 0.1)
        def slow_function():
            time.sleep(0.5)
            return "should not reach here"
        
        try:
            slow_function()
            print("✗ Slow function should have timed out")
            return False
        except TimeoutError as e:
            print("✓ Slow function correctly times out")
            assert "test_slow" in e.message
        
        return True
        
    except Exception as e:
        print(f"✗ Timeout manager test failed: {e}")
        return False


def test_enhanced_logging():
    """Test the enhanced logging system."""
    print("\nTesting enhanced logging...")
    
    try:
        from enhanced_logging import enhanced_logger, LogContext
        
        # Test basic logging
        context = LogContext(
            operation="test_operation",
            tool_name="test_tool",
            request_id="test-123"
        )
        
        enhanced_logger.info("Test info message", context=context)
        enhanced_logger.warning("Test warning message", context=context)
        
        # Test tool logging
        enhanced_logger.log_tool_call(
            "test_tool", 
            "test_action", 
            {"param1": "value1"},
            "test-123"
        )
        
        enhanced_logger.log_tool_result(
            "test_tool",
            "test_action", 
            True,
            "Test completed successfully",
            request_id="test-123",
            duration=0.5
        )
        
        print("✓ Enhanced logging works correctly")
        return True
        
    except Exception as e:
        print(f"✗ Enhanced logging test failed: {e}")
        return False


def test_configuration():
    """Test the enhanced configuration."""
    print("\nTesting enhanced configuration...")
    
    try:
        from config import config
        
        # Test that new configuration options are available
        assert hasattr(config, 'operation_timeouts')
        assert hasattr(config, 'enable_strict_validation')
        assert hasattr(config, 'enable_health_checks')
        assert hasattr(config, 'retry_exponential_backoff')
        
        # Test timeout configuration
        assert isinstance(config.operation_timeouts, dict)
        assert 'connection' in config.operation_timeouts
        assert 'script_operation' in config.operation_timeouts
        
        print("✓ Enhanced configuration loaded correctly")
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("Unity MCP Server Improvements Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Exception Hierarchy", test_exception_hierarchy),
        ("Validation Framework", test_validation_framework),
        ("Timeout Manager", test_timeout_manager),
        ("Enhanced Logging", test_enhanced_logging),
        ("Configuration", test_configuration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The improvements are working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
