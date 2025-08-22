#!/usr/bin/env python3
"""
Simple load testing script for Unity MCP Headless Server.
Tests concurrent command handling and response times.
"""

import requests
import time
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

class LoadTester:
    def __init__(self, base_url="http://localhost:8080", max_workers=10):
        self.base_url = base_url
        self.max_workers = max_workers
        self.results = []
        self.lock = threading.Lock()
    
    def send_command(self, command_data):
        """Send a single command and measure response time."""
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.base_url}/execute-command",
                json=command_data,
                timeout=10
            )
            response_time = time.time() - start_time
            
            result = {
                "success": response.status_code == 200,
                "response_time": response_time,
                "status_code": response.status_code,
                "command": command_data["action"]
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result["api_success"] = data.get("success", False)
                except:
                    result["api_success"] = False
            
            with self.lock:
                self.results.append(result)
            
            return result
        
        except Exception as e:
            response_time = time.time() - start_time
            result = {
                "success": False,
                "response_time": response_time,
                "error": str(e),
                "command": command_data["action"]
            }
            
            with self.lock:
                self.results.append(result)
            
            return result
    
    def run_concurrent_test(self, num_requests=20, command_type="ping"):
        """Run concurrent requests test."""
        print(f"Running {num_requests} concurrent {command_type} commands...")
        
        # Create test commands
        commands = [
            {
                "action": command_type,
                "params": {"test_id": i},
                "userId": f"load-test-{i}"
            }
            for i in range(num_requests)
        ]
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.send_command, cmd) for cmd in commands]
            
            for future in as_completed(futures):
                result = future.result()
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful_requests = len([r for r in self.results if r["success"]])
        avg_response_time = sum(r["response_time"] for r in self.results) / len(self.results)
        max_response_time = max(r["response_time"] for r in self.results)
        min_response_time = min(r["response_time"] for r in self.results)
        
        print(f"\nLoad Test Results:")
        print(f"Total requests: {num_requests}")
        print(f"Successful requests: {successful_requests}")
        print(f"Success rate: {successful_requests/num_requests*100:.1f}%")
        print(f"Total time: {total_time:.3f}s")
        print(f"Requests per second: {num_requests/total_time:.1f}")
        print(f"Average response time: {avg_response_time:.3f}s")
        print(f"Min response time: {min_response_time:.3f}s")
        print(f"Max response time: {max_response_time:.3f}s")
        
        return {
            "total_requests": num_requests,
            "successful_requests": successful_requests,
            "success_rate": successful_requests/num_requests*100,
            "total_time": total_time,
            "requests_per_second": num_requests/total_time,
            "avg_response_time": avg_response_time,
            "min_response_time": min_response_time,
            "max_response_time": max_response_time
        }

def main():
    # Test server availability
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        print(f"Server health check: {response.status_code}")
        if response.status_code == 200:
            print(f"Health data: {response.json()}")
    except Exception as e:
        print(f"Server not available: {e}")
        return
    
    # Run load tests
    tester = LoadTester()
    
    # Test 1: Basic ping commands
    print("\n" + "="*50)
    print("TEST 1: Basic ping commands (5 concurrent)")
    tester.results = []
    tester.run_concurrent_test(5, "ping")
    
    # Test 2: GameObject creation
    print("\n" + "="*50)
    print("TEST 2: GameObject creation (5 concurrent)")
    tester.results = []
    tester.run_concurrent_test(5, "manage_gameobject")
    
    # Test 3: Heavy load
    print("\n" + "="*50)
    print("TEST 3: Heavy load test (10 concurrent)")
    tester.results = []
    tester.run_concurrent_test(10, "ping")

if __name__ == "__main__":
    main()