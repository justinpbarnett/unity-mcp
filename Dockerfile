# Unity MCP Headless Server Dockerfile
# Multi-stage build for optimized container size

FROM python:3.11-slim as python-base

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install dependencies
COPY UnityMcpBridge/UnityMcpServer~/src/pyproject.toml .
RUN pip install --upgrade pip && \
    pip install httpx>=0.27.2 mcp[cli]>=1.4.1 requests>=2.28.0

# Unity Stage - Install Unity Hub and Unity Editor
FROM python-base as unity-stage

# Install Unity Hub
RUN wget -qO - https://hub.unity3d.com/linux/keys/public | gpg --dearmor | tee /usr/share/keyrings/Unity_Technologies_ApS.gpg > /dev/null && \
    echo "deb [signed-by=/usr/share/keyrings/Unity_Technologies_ApS.gpg] https://hub.unity3d.com/linux/repos/deb stable main" | tee /etc/apt/sources.list.d/unityhub.list && \
    apt-get update && \
    apt-get install -y unityhub && \
    rm -rf /var/lib/apt/lists/*

# Set Unity environment variables
ENV UNITY_LICENSE_FILE=/tmp/Unity_v2022.x.ulf
ENV UNITY_USERNAME=""
ENV UNITY_PASSWORD=""
ENV UNITY_SERIAL=""
ENV UNITY_VERSION="2022.3.45f1"

# Accept Unity license and install Unity Editor (headless)
RUN unityhub --headless install --version ${UNITY_VERSION} --changeset 63b2b3067b8e --child-modules || true

# Final stage - Combine Python server and Unity
FROM unity-stage as final

# Copy Unity MCP source code
COPY UnityMcpBridge/UnityMcpServer~/src/ /app/server/
COPY UnityMcpBridge/ /app/unity-mcp-bridge/

# Copy test scripts and documentation
COPY test_headless_api.py /app/
COPY load_test.py /app/
COPY README-HEADLESS.md /app/

# Create necessary directories
RUN mkdir -p /app/unity-projects /app/builds /tmp/unity-logs

# Set environment variables for headless operation
ENV UNITY_HEADLESS=true \
    UNITY_MCP_AUTOSTART=true \
    UNITY_MCP_PORT=6400 \
    UNITY_MCP_LOG_PATH=/tmp/unity-logs/unity-mcp.log \
    LOG_LEVEL=INFO

# Expose ports
EXPOSE 8080 6400

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Function to cleanup on exit\n\
cleanup() {\n\
    echo "Shutting down Unity MCP Headless Server..."\n\
    kill -TERM "$unity_pid" 2>/dev/null || true\n\
    kill -TERM "$server_pid" 2>/dev/null || true\n\
    wait\n\
}\n\
\n\
trap cleanup SIGTERM SIGINT\n\
\n\
# Create log directory\n\
mkdir -p /tmp/unity-logs\n\
\n\
# Start Unity in headless mode with project\n\
echo "Starting Unity in headless mode..."\n\
if [ -n "$UNITY_PROJECT_PATH" ]; then\n\
    unity-editor -batchmode -projectPath "$UNITY_PROJECT_PATH" -mcp-autostart -mcp-port "$UNITY_MCP_PORT" &\n\
    unity_pid=$!\n\
    echo "Unity started with PID $unity_pid"\n\
else\n\
    echo "Warning: UNITY_PROJECT_PATH not set, Unity will not start"\n\
    unity_pid=""\n\
fi\n\
\n\
# Wait for Unity to initialize\n\
sleep 10\n\
\n\
# Start the headless HTTP server\n\
echo "Starting Unity MCP Headless HTTP Server..."\n\
cd /app/server\n\
python3 headless_server.py --host 0.0.0.0 --port 8080 --unity-port "$UNITY_MCP_PORT" --log-level "$LOG_LEVEL" &\n\
server_pid=$!\n\
echo "Headless server started with PID $server_pid"\n\
\n\
# Wait for both processes\n\
wait\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Set working directory
WORKDIR /app

# Run entrypoint
CMD ["/app/entrypoint.sh"]

# Build metadata
LABEL maintainer="Unity MCP Team" \
      version="1.0.0" \
      description="Unity MCP Headless Server for containerized Unity operations"