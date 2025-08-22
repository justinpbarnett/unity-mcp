#!/usr/bin/env python3
"""
Test script for Unity MCP Headless API validation and load testing.

This script validates the REST API endpoints and tests concurrent command handling
to ensure the system meets the milestone requirements:
- Handles 5 concurrent commands without crashing
- Response time < 5s for simple operations  
- 90% success rate under load
"""

import asyncio
import json
import time
import requests
import concurrent.futures
from typing import Dict, List, Any, Optional
import logging
import sys
import argparse
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result data structure."""
    test_name: str
    success: bool
    response_time: float
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class UnityMCPTester:
    """Test suite for Unity MCP Headless API."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Test metrics
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results: List[TestResult] = []
        
    def log_result(self, result: TestResult):
        """Log and store test result."""
        self.test_results.append(result)
        self.total_tests += 1
        
        if result.success:
            self.passed_tests += 1
            logger.info(f"✓ {result.test_name} - {result.response_time:.3f}s")
        else:
            self.failed_tests += 1
            logger.error(f"✗ {result.test_name} - {result.error}")
    
    def test_health_endpoint(self) -> TestResult:
        """Test health check endpoint."""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/health")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return TestResult(
                    test_name="Health Check",
                    success=True,
                    response_time=response_time,
                    data=data
                )
            else:
                return TestResult(
                    test_name="Health Check",
                    success=False,
                    response_time=response_time,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        except Exception as e:
            return TestResult(
                test_name="Health Check",
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    def test_status_endpoint(self) -> TestResult:
        """Test status endpoint."""
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/status")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return TestResult(
                    test_name="Status Check",
                    success=True,
                    response_time=response_time,
                    data=data
                )
            else:
                return TestResult(
                    test_name="Status Check",
                    success=False,
                    response_time=response_time,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        except Exception as e:
            return TestResult(
                test_name="Status Check",
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    def test_simple_command(self, action: str, params: Optional[Dict[str, Any]] = None) -> TestResult:
        """Test a simple Unity command execution."""
        start_time = time.time()
        try:
            command_data = {
                "action": action,
                "params": params or {},
                "userId": "test-user"
            }
            
            response = self.session.post(
                f"{self.base_url}/execute-command",
                json=command_data,
                headers={"Content-Type": "application/json"}
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return TestResult(
                    test_name=f"Command: {action}",
                    success=data.get('success', False),
                    response_time=response_time,
                    data=data,
                    error=data.get('error') if not data.get('success', False) else None
                )
            else:
                return TestResult(
                    test_name=f"Command: {action}",
                    success=False,
                    response_time=response_time,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        except Exception as e:
            return TestResult(
                test_name=f"Command: {action}",
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    def test_concurrent_commands(self, num_concurrent: int = 5) -> List[TestResult]:
        """Test concurrent command execution."""
        logger.info(f"Testing {num_concurrent} concurrent commands...")
        
        # Define test commands
        test_commands = [
            {"action": "create_gameobject", "params": {"action": "create", "name": f"TestCube_{i}", "primitiveType": "Cube"}}
            for i in range(num_concurrent)
        ]
        
        results = []
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            # Submit all commands concurrently
            futures = [
                executor.submit(self._execute_command_sync, cmd)
                for cmd in test_commands
            ]
            
            # Collect results
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    result = future.result()
                    result.test_name = f"Concurrent Command {i+1}"
                    results.append(result)
                except Exception as e:
                    results.append(TestResult(
                        test_name=f"Concurrent Command {i+1}",
                        success=False,
                        response_time=0,
                        error=str(e)
                    ))
        
        total_time = time.time() - start_time
        logger.info(f"Concurrent test completed in {total_time:.3f}s")
        
        return results
    
    def _execute_command_sync(self, command_data: Dict[str, Any]) -> TestResult:
        """Execute a single command synchronously."""
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.base_url}/execute-command",
                json=command_data,
                headers={"Content-Type": "application/json"}
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return TestResult(
                    test_name=command_data["action"],
                    success=data.get('success', False),
                    response_time=response_time,
                    data=data,
                    error=data.get('error') if not data.get('success', False) else None
                )
            else:
                return TestResult(
                    test_name=command_data["action"],
                    success=False,
                    response_time=response_time,
                    error=f"HTTP {response.status_code}: {response.text}"
                )
        except Exception as e:
            return TestResult(
                test_name=command_data["action"],
                success=False,
                response_time=time.time() - start_time,
                error=str(e)
            )
    
    def test_headless_operations(self) -> List[TestResult]:
        """Test headless-specific operations."""
        logger.info("Testing headless operations...")
        
        operations = [
            {
                "action": "headless_operations",
                "params": {"action": "create_empty_scene", "sceneName": "TestScene"}
            },
            {
                "action": "headless_operations", 
                "params": {"action": "create_basic_objects", "cubeCount": 3, "sphereCount": 2}
            },
            {
                "action": "headless_operations",
                "params": {"action": "setup_basic_lighting"}
            },
            {
                "action": "headless_operations",
                "params": {"action": "get_scene_info"}
            }
        ]
        
        results = []
        for op in operations:
            result = self.test_simple_command(op["action"], op["params"])
            result.test_name = f"Headless: {op['params']['action']}"
            results.append(result)
            
        return results
    
    def performance_test(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Run performance test for specified duration."""
        logger.info(f"Running performance test for {duration_seconds} seconds...")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        request_count = 0
        success_count = 0
        error_count = 0
        response_times = []
        
        while time.time() < end_time:
            # Test a simple command
            result = self.test_simple_command("get_scene_info", {"action": "get_scene_info"})
            
            request_count += 1
            if result.success:
                success_count += 1
            else:
                error_count += 1
            
            response_times.append(result.response_time)
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.1)
        
        # Calculate statistics
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        success_rate = (success_count / request_count * 100) if request_count > 0 else 0
        
        return {
            "duration": duration_seconds,
            "total_requests": request_count,
            "successful_requests": success_count,
            "failed_requests": error_count,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0
        }
    
    def run_full_test_suite(self, include_performance: bool = False) -> Dict[str, Any]:
        """Run the complete test suite."""
        logger.info("Starting Unity MCP Headless API Test Suite")
        logger.info(f"Target URL: {self.base_url}")
        
        # Basic connectivity tests
        self.log_result(self.test_health_endpoint())
        self.log_result(self.test_status_endpoint())
        
        # Simple command tests
        simple_commands = [
            ("ping", {}),
            ("manage_scene", {"action": "get_hierarchy"}),
            ("manage_gameobject", {"action": "find", "searchTerm": "Main Camera"})
        ]
        
        for action, params in simple_commands:
            self.log_result(self.test_simple_command(action, params))
        
        # Headless operations tests
        headless_results = self.test_headless_operations()
        for result in headless_results:
            self.log_result(result)
        
        # Concurrent command test
        concurrent_results = self.test_concurrent_commands(5)
        for result in concurrent_results:
            self.log_result(result)
        
        # Performance test (optional)
        perf_results = None
        if include_performance:
            perf_results = self.performance_test(30)  # 30 second performance test
        
        # Calculate overall metrics
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        avg_response_time = sum(r.response_time for r in self.test_results) / len(self.test_results) if self.test_results else 0
        
        # Check milestone requirements
        milestone_results = {
            "concurrent_commands_ok": len([r for r in concurrent_results if r.success]) == 5,
            "response_time_ok": all(r.response_time < 5.0 for r in self.test_results if r.success),
            "success_rate_ok": success_rate >= 90
        }
        
        return {
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time
            },
            "milestone_requirements": milestone_results,
            "performance_test": perf_results,
            "test_results": [
                {
                    "name": r.test_name,
                    "success": r.success,
                    "response_time": r.response_time,
                    "error": r.error
                }
                for r in self.test_results
            ]
        }
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test summary."""
        print("\n" + "="*60)
        print("UNITY MCP HEADLESS API TEST RESULTS")
        print("="*60)
        
        summary = results["summary"]
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Avg Response Time: {summary['avg_response_time']:.3f}s")
        
        print("\nMILESTONE REQUIREMENTS:")
        milestone = results["milestone_requirements"]
        print(f"✓ Concurrent Commands (5): {'PASS' if milestone['concurrent_commands_ok'] else 'FAIL'}")
        print(f"✓ Response Time (<5s): {'PASS' if milestone['response_time_ok'] else 'FAIL'}")
        print(f"✓ Success Rate (≥90%): {'PASS' if milestone['success_rate_ok'] else 'FAIL'}")
        
        if results["performance_test"]:
            print("\nPERFORMANCE TEST:")
            perf = results["performance_test"]
            print(f"Duration: {perf['duration']}s")
            print(f"Total Requests: {perf['total_requests']}")
            print(f"Success Rate: {perf['success_rate']:.1f}%")
            print(f"Avg Response Time: {perf['avg_response_time']:.3f}s")
        
        print("\n" + "="*60)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Unity MCP Headless API Test Suite")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL of the headless server")
    parser.add_argument("--performance", action="store_true", help="Include performance testing")
    parser.add_argument("--output", help="Output results to JSON file")
    
    args = parser.parse_args()
    
    # Create tester instance
    tester = UnityMCPTester(args.url)
    
    try:
        # Run test suite
        results = tester.run_full_test_suite(include_performance=args.performance)
        
        # Print summary
        tester.print_summary(results)
        
        # Save results to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nResults saved to {args.output}")
        
        # Exit with appropriate code
        if results["summary"]["success_rate"] >= 90:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()