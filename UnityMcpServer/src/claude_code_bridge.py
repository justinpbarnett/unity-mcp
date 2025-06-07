#!/usr/bin/env python3
"""
HTTP Bridge for Unity MCP Server to work with Claude Code.
This creates REST endpoints that Claude Code can access via HTTP.
"""

from flask import Flask, request, jsonify
import json
import logging
from unity_connection import get_unity_connection
from config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format=config.log_format
)
logger = logging.getLogger("claude-code-bridge")

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Global Unity connection
unity_conn = None

def get_unity_conn():
    """Get or create Unity connection."""
    global unity_conn
    if unity_conn is None:
        try:
            unity_conn = get_unity_connection()
            logger.info("Connected to Unity via bridge")
        except Exception as e:
            logger.error(f"Failed to connect to Unity: {e}")
            unity_conn = None
    return unity_conn

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    conn = get_unity_conn()
    if conn and conn.sock:
        return jsonify({"status": "connected", "unity": True})
    else:
        return jsonify({"status": "disconnected", "unity": False}), 503

@app.route('/unity/scene', methods=['GET', 'POST'])
def manage_scene():
    """Scene management endpoint."""
    conn = get_unity_conn()
    if not conn:
        return jsonify({"success": False, "message": "Not connected to Unity"}), 503
    
    try:
        if request.method == 'GET':
            # Default action: get hierarchy
            params = {"action": "get_hierarchy"}
        else:
            params = request.get_json() or {}
            
        response = conn.send_command("manage_scene", params)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Scene management error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/unity/gameobject', methods=['GET', 'POST'])
def manage_gameobject():
    """GameObject management endpoint."""
    conn = get_unity_conn()
    if not conn:
        return jsonify({"success": False, "message": "Not connected to Unity"}), 503
    
    try:
        if request.method == 'GET':
            # Default action: list all objects
            params = {"action": "find", "name": "", "tag": ""}
        else:
            params = request.get_json() or {}
            
        response = conn.send_command("manage_gameobject", params)
        return jsonify(response)
    except Exception as e:
        logger.error(f"GameObject management error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/unity/console', methods=['GET', 'POST'])
def read_console():
    """Console reading endpoint."""
    conn = get_unity_conn()
    if not conn:
        return jsonify({"success": False, "message": "Not connected to Unity"}), 503
    
    try:
        if request.method == 'GET':
            params = {"action": "get"}
        else:
            params = request.get_json() or {}
            
        response = conn.send_command("read_console", params)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Console reading error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/unity/script', methods=['POST'])
def manage_script():
    """Script management endpoint."""
    conn = get_unity_conn()
    if not conn:
        return jsonify({"success": False, "message": "Not connected to Unity"}), 503
    
    try:
        params = request.get_json() or {}
        response = conn.send_command("manage_script", params)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Script management error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/unity/editor', methods=['GET', 'POST'])
def manage_editor():
    """Editor management endpoint."""
    conn = get_unity_conn()
    if not conn:
        return jsonify({"success": False, "message": "Not connected to Unity"}), 503
    
    try:
        if request.method == 'GET':
            params = {"action": "get_info"}
        else:
            params = request.get_json() or {}
            
        response = conn.send_command("manage_editor", params)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Editor management error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/unity/menu', methods=['POST'])
def execute_menu_item():
    """Menu execution endpoint."""
    conn = get_unity_conn()
    if not conn:
        return jsonify({"success": False, "message": "Not connected to Unity"}), 503
    
    try:
        params = request.get_json() or {}
        response = conn.send_command("execute_menu_item", params)
        return jsonify(response)
    except Exception as e:
        logger.error(f"Menu execution error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Claude Code Bridge for Unity MCP")
    logger.info("Available endpoints:")
    logger.info("  GET  /health - Check connection status")
    logger.info("  GET  /unity/scene - Get scene hierarchy")
    logger.info("  POST /unity/scene - Scene operations")
    logger.info("  GET  /unity/gameobject - List GameObjects")
    logger.info("  POST /unity/gameobject - GameObject operations")
    logger.info("  GET  /unity/console - Read Unity console")
    logger.info("  GET  /unity/editor - Get editor info")
    logger.info("  POST /unity/script - Script operations")
    logger.info("  POST /unity/menu - Execute menu items")
    
    app.run(host='0.0.0.0', port=6501, debug=False)