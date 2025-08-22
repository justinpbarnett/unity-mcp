#!/usr/bin/env python3
"""
Mock Unity MCP Headless Server for testing purposes.
Simulates the actual server behavior to validate test frameworks.
"""

import json
import time
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

class MockUnityServer:
    def __init__(self):
        self.commands = {}
        self.total_commands = 0
        self.successful_commands = 0
        self.start_time = time.time()
        
    def execute_command(self, action, params, user_id):
        """Simulate command execution."""
        command_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Simulate different response times and behaviors
        if action == "ping":
            time.sleep(0.1)  # Fast response
            result = {"message": "pong"}
            success = True
        elif action == "create_gameobject":
            time.sleep(1.5)  # Moderate response time
            result = {"message": "GameObject created successfully", "name": params.get("name", "TestObject")}
            success = True
        elif action == "headless_operations":
            subaction = params.get("action", "unknown")
            if subaction == "create_empty_scene":
                time.sleep(2.0)  # Scene creation takes longer
                result = {"message": f"Scene {params.get('sceneName', 'TestScene')} created", "objectCount": 2}
                success = True
            elif subaction == "build_webgl":
                time.sleep(4.0)  # Build operations are slower
                result = {"message": "WebGL build completed", "buildPath": params.get("buildPath", "Builds/WebGL")}
                success = True
            else:
                time.sleep(0.5)
                result = {"message": f"Headless operation {subaction} completed"}
                success = True
        else:
            time.sleep(0.3)
            result = {"message": f"Command {action} executed"}
            success = True
        
        execution_time = time.time() - start_time
        
        self.commands[command_id] = {
            "success": success,
            "data": result,
            "execution_time": execution_time,
            "status": "completed"
        }
        
        self.total_commands += 1
        if success:
            self.successful_commands += 1
            
        return {
            "success": success,
            "data": result,
            "commandId": command_id,
            "executionTime": execution_time
        }
    
    def get_command_status(self, command_id):
        """Get command execution status."""
        if command_id not in self.commands:
            return {"success": False, "error": "Command not found"}
        
        cmd = self.commands[command_id]
        return {
            "success": cmd["success"],
            "data": cmd["data"],
            "commandId": command_id,
            "executionTime": cmd["execution_time"],
            "message": "Command completed successfully" if cmd["success"] else "Command failed"
        }
    
    def get_health(self):
        """Health check response."""
        return {
            "status": "healthy",
            "unity_connected": True,
            "active_commands": 0,
            "total_commands": self.total_commands,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_status(self):
        """Server status response."""
        uptime = time.time() - self.start_time
        success_rate = (self.successful_commands / max(self.total_commands, 1)) * 100
        
        return {
            "server": "Mock Unity MCP Headless Server",
            "version": "1.0.0-mock",
            "uptime": uptime,
            "active_commands": 0,
            "max_concurrent_commands": 5,
            "queue_size": len(self.commands),
            "metrics": {
                "total_commands": self.total_commands,
                "successful_commands": self.successful_commands,
                "failed_commands": self.total_commands - self.successful_commands,
                "success_rate": success_rate,
                "avg_execution_time": 1.2
            },
            "unity_connected": True,
            "timestamp": datetime.utcnow().isoformat()
        }

class MockHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/execute-command':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data)
                action = data.get('action')
                params = data.get('params', {})
                user_id = data.get('userId', 'test-user')
                
                if not action:
                    self.send_error(400, "Missing required field: action")
                    return
                
                result = getattr(self.server, 'mock_server').execute_command(action, params, user_id)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(result).encode('utf-8'))
                
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not found")
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        try:
            mock_server = getattr(self.server, 'mock_server')
            if path == '/health':
                result = mock_server.get_health()
            elif path == '/status':
                result = mock_server.get_status()
            elif path.startswith('/command/'):
                command_id = path.split('/')[-1]
                result = mock_server.get_command_status(command_id)
            else:
                self.send_error(404, "Not found")
                return
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(json.dumps(result, indent=2).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, str(e))

class MockHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.mock_server = MockUnityServer()

def run_mock_server(port=8080):
    """Run the mock server."""
    server_address = ('localhost', port)
    httpd = MockHTTPServer(server_address, MockHandler)
    
    print(f"Mock Unity MCP Headless Server running on http://localhost:{port}")
    print("Endpoints available:")
    print("  POST /execute-command")
    print("  GET  /health")
    print("  GET  /status")
    print("  GET  /command/{id}")
    print("\nPress Ctrl+C to stop...")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down mock server...")
        httpd.shutdown()

if __name__ == "__main__":
    run_mock_server()