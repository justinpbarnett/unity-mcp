# Unity MCP Server - Production Deployment Guide

This guide provides comprehensive instructions for deploying the production-ready Unity MCP Server in various environments.

## 🚀 Quick Deployment

### Prerequisites
- **Python 3.8+** with pip package manager
- **Unity 2021.3+** with Unity MCP Bridge package installed
- **Network connectivity** between Python server and Unity Editor
- **Administrative privileges** for port binding (if using privileged ports)

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/usexless/unity-mcp.git
cd unity-mcp/UnityMcpServer

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy default configuration
cp src/config.py src/config_local.py

# Edit configuration (optional)
nano src/config_local.py
```

**Key Configuration Options:**
```python
# Network settings
unity_host = "localhost"  # Unity Editor host
unity_port = 6400        # Unity MCP Bridge port
mcp_port = 6500          # MCP server port

# Timeout settings (seconds)
operation_timeouts = {
    "connection": 10.0,
    "script_operation": 30.0,
    "scene_operation": 60.0,
    "gameobject_operation": 30.0,
    "asset_operation": 45.0,
    # ... customize as needed
}

# Production settings
enable_strict_validation = True
enable_health_checks = True
enable_performance_logging = True
log_level = "INFO"
```

### 3. Unity Setup

1. **Install Unity MCP Bridge Package**
   - Open Unity Package Manager
   - Add package from git URL or local path
   - Import Unity MCP Bridge package

2. **Configure Unity MCP Bridge**
   ```csharp
   // In Unity, configure the MCP Bridge settings
   Host: localhost
   Port: 6400
   Auto-connect: true
   ```

3. **Verify Unity Setup**
   - Start Unity Editor
   - Check that MCP Bridge is active in the console
   - Verify no connection errors

### 4. Start the Server

```bash
cd src
python server.py
```

**Expected Output:**
```json
{"timestamp": "2025-01-27T12:00:00.000Z", "level": "INFO", "message": "Unity MCP Server starting up"}
{"timestamp": "2025-01-27T12:00:01.000Z", "level": "INFO", "message": "Successfully connected to Unity"}
{"timestamp": "2025-01-27T12:00:01.100Z", "level": "INFO", "message": "Server ready on port 6500"}
```

### 5. Verify Deployment

```bash
# Test health check
curl http://localhost:6500/health

# Expected response:
{
  "success": true,
  "data": {
    "status": "healthy",
    "connection": {"healthy": true},
    "server": {"version": "2.0.0"}
  }
}
```

## 🏭 Production Deployment

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
EXPOSE 6500

CMD ["python", "src/server.py"]
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  unity-mcp-server:
    build: .
    ports:
      - "6500:6500"
    environment:
      - UNITY_HOST=host.docker.internal
      - UNITY_PORT=6400
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

**Deploy:**
```bash
docker-compose up -d
```

### Kubernetes Deployment

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: unity-mcp-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: unity-mcp-server
  template:
    metadata:
      labels:
        app: unity-mcp-server
    spec:
      containers:
      - name: unity-mcp-server
        image: unity-mcp-server:latest
        ports:
        - containerPort: 6500
        env:
        - name: UNITY_HOST
          value: "unity-editor-service"
        - name: UNITY_PORT
          value: "6400"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: unity-mcp-server-service
spec:
  selector:
    app: unity-mcp-server
  ports:
  - port: 6500
    targetPort: 6500
  type: LoadBalancer
```

### Systemd Service (Linux)

**unity-mcp-server.service:**
```ini
[Unit]
Description=Unity MCP Server
After=network.target

[Service]
Type=simple
User=unity-mcp
WorkingDirectory=/opt/unity-mcp-server/src
ExecStart=/opt/unity-mcp-server/venv/bin/python server.py
Restart=always
RestartSec=10

Environment=PYTHONPATH=/opt/unity-mcp-server/src
Environment=LOG_LEVEL=INFO

[Install]
WantedBy=multi-user.target
```

**Install and start:**
```bash
sudo cp unity-mcp-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable unity-mcp-server
sudo systemctl start unity-mcp-server
```

## 🔧 Configuration Management

### Environment Variables

The server supports configuration via environment variables:

```bash
# Network configuration
export UNITY_HOST=localhost
export UNITY_PORT=6400
export MCP_PORT=6500

# Timeout configuration
export CONNECTION_TIMEOUT=10
export SCRIPT_OPERATION_TIMEOUT=30
export SCENE_OPERATION_TIMEOUT=60

# Feature flags
export ENABLE_STRICT_VALIDATION=true
export ENABLE_HEALTH_CHECKS=true
export ENABLE_PERFORMANCE_LOGGING=true

# Logging configuration
export LOG_LEVEL=INFO
export LOG_FILE_MAX_SIZE=10485760  # 10MB
export LOG_FILE_BACKUP_COUNT=5
```

### Configuration File

**config_production.py:**
```python
from dataclasses import dataclass
import os

@dataclass
class ProductionConfig:
    # Network settings
    unity_host: str = os.getenv("UNITY_HOST", "localhost")
    unity_port: int = int(os.getenv("UNITY_PORT", "6400"))
    mcp_port: int = int(os.getenv("MCP_PORT", "6500"))
    
    # Timeout settings
    operation_timeouts = {
        "connection": float(os.getenv("CONNECTION_TIMEOUT", "10.0")),
        "script_operation": float(os.getenv("SCRIPT_OPERATION_TIMEOUT", "30.0")),
        "scene_operation": float(os.getenv("SCENE_OPERATION_TIMEOUT", "60.0")),
        # ... add all timeout configurations
    }
    
    # Production settings
    enable_strict_validation: bool = os.getenv("ENABLE_STRICT_VALIDATION", "true").lower() == "true"
    enable_health_checks: bool = os.getenv("ENABLE_HEALTH_CHECKS", "true").lower() == "true"
    enable_performance_logging: bool = os.getenv("ENABLE_PERFORMANCE_LOGGING", "true").lower() == "true"
    
    # Logging settings
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file_max_size: int = int(os.getenv("LOG_FILE_MAX_SIZE", "10485760"))
    log_file_backup_count: int = int(os.getenv("LOG_FILE_BACKUP_COUNT", "5"))

# Use production config
config = ProductionConfig()
```

## 📊 Monitoring & Observability

### Health Checks

**Endpoint:** `GET /health`

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": 1643284800.0,
    "connection": {
      "healthy": true,
      "metrics": {
        "total_connections": 5,
        "successful_commands": 42,
        "average_response_time": 0.15
      }
    },
    "operations": {
      "active_count": 0
    },
    "server": {
      "version": "2.0.0",
      "uptime": 3600.0
    }
  }
}
```

### Metrics Collection

**Prometheus Integration:**
```python
# Add to server.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics
REQUEST_COUNT = Counter('unity_mcp_requests_total', 'Total requests', ['tool', 'status'])
REQUEST_DURATION = Histogram('unity_mcp_request_duration_seconds', 'Request duration', ['tool'])
ACTIVE_CONNECTIONS = Gauge('unity_mcp_active_connections', 'Active connections')

# Start metrics server
start_http_server(8000)
```

### Log Aggregation

**Fluentd Configuration:**
```xml
<source>
  @type tail
  path /app/logs/unity_mcp_server.log
  pos_file /var/log/fluentd/unity_mcp_server.log.pos
  tag unity.mcp.server
  format json
</source>

<match unity.mcp.server>
  @type elasticsearch
  host elasticsearch
  port 9200
  index_name unity-mcp-server
</match>
```

## 🔒 Security Considerations

### Network Security

1. **Firewall Configuration**
   ```bash
   # Allow only necessary ports
   ufw allow 6500/tcp  # MCP server port
   ufw allow 6400/tcp  # Unity bridge port (if remote)
   ```

2. **TLS/SSL Configuration**
   ```python
   # Add to config.py
   enable_tls = True
   tls_cert_file = "/path/to/cert.pem"
   tls_key_file = "/path/to/key.pem"
   ```

### Authentication & Authorization

```python
# Add to server.py
from functools import wraps

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not validate_token(auth_header):
            return {"success": False, "error": "Unauthorized"}, 401
        return f(*args, **kwargs)
    return decorated_function

@mcp.tool()
@require_auth
def manage_script(ctx: Context, ...):
    # Tool implementation
```

### Input Sanitization

```python
# Enhanced validation in production
config.enable_strict_validation = True
config.validate_unity_paths = True
config.sanitize_file_paths = True
config.max_request_size = 10 * 1024 * 1024  # 10MB
```

## 🚨 Troubleshooting

### Common Issues

1. **Connection Refused**
   ```
   Error: Could not connect to Unity at localhost:6400
   ```
   **Solution:**
   - Verify Unity Editor is running
   - Check Unity MCP Bridge is active
   - Confirm port 6400 is not blocked by firewall

2. **Timeout Errors**
   ```
   Error: Operation 'manage_script.create' timed out after 30 seconds
   ```
   **Solution:**
   - Increase timeout in configuration
   - Check Unity Editor performance
   - Verify Unity project is not corrupted

3. **Validation Errors**
   ```
   Error: Parameter 'name': Must match pattern: ^[a-zA-Z_][a-zA-Z0-9_]*$
   ```
   **Solution:**
   - Check parameter format requirements
   - Use valid Unity naming conventions
   - Review validation rules in documentation

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python server.py

# Or modify config.py
config.log_level = "DEBUG"
config.include_stack_traces = True
```

### Performance Tuning

```python
# Optimize for high-load scenarios
config.operation_timeouts = {
    "connection": 5.0,      # Faster connection timeout
    "script_operation": 60.0, # Longer for complex scripts
    # ... adjust based on workload
}

config.max_retries = 5
config.retry_exponential_backoff = True
config.retry_max_delay = 60.0
```

## 📈 Scaling & High Availability

### Load Balancing

```nginx
# nginx.conf
upstream unity_mcp_servers {
    server unity-mcp-1:6500;
    server unity-mcp-2:6500;
    server unity-mcp-3:6500;
}

server {
    listen 80;
    location / {
        proxy_pass http://unity_mcp_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Database Integration

```python
# Add persistent storage for metrics and logs
import sqlite3

class MetricsStore:
    def __init__(self, db_path="metrics.db"):
        self.conn = sqlite3.connect(db_path)
        self.init_tables()
    
    def init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                timestamp REAL,
                tool_name TEXT,
                operation TEXT,
                duration REAL,
                success BOOLEAN
            )
        """)
```

## 🎯 Performance Benchmarks

### Expected Performance

| Metric | Target | Typical |
|--------|--------|---------|
| **Connection Time** | <5s | 1-2s |
| **Script Operations** | <30s | 5-15s |
| **Scene Operations** | <60s | 10-30s |
| **Asset Operations** | <45s | 10-25s |
| **Error Response Time** | <100ms | 50ms |
| **Health Check Response** | <50ms | 20ms |

### Load Testing

```bash
# Install load testing tools
pip install locust

# Create load test script
cat > load_test.py << EOF
from locust import HttpUser, task, between

class UnityMcpUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def health_check(self):
        self.client.get("/health")
    
    @task(3)
    def manage_script(self):
        self.client.post("/tools/manage_script", json={
            "action": "read",
            "name": "TestScript",
            "path": "Assets/Scripts/"
        })
EOF

# Run load test
locust -f load_test.py --host=http://localhost:6500
```

---

**🎉 Your Unity MCP Server is now ready for production deployment with industrial-grade reliability and monitoring!**
