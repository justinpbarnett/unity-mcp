# Unity MCP Server - Docker Setup

This repository contains Docker configuration for running the Unity MCP server in a container.

## Prerequisites

- [Podman](https://podman.io/get-started) or [Docker](https://docs.docker.com/get-docker/)
- Unity Editor with the Unity MCP Bridge package installed

## Getting Started

### 1. Build and Start the Docker Container

```bash
docker build -t unity-mcp:latest
```

This will build the Docker image and start the Unity MCP server in a container.

### 2. Configure Your MCP Client

Configure your MCP client (Claude, Cursor, etc.) to use the dockerized server:

```json
{
  "mcpServers": {
    "UnityMCP": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "--name",
        "unity-mcp-server",
        "--unity-host=host.docker.internal",
        "--unity-port=6400"
      ]
    }
  }
}
```

```json
{
  "mcpServers": {
    "UnityMCP": {
      "command": "podman",
      "args": [
        "run",
        "--rm",
        "--name",
        "unity-mcp-server",
        "--unity-host=host.container.internal",
        "--unity-port=6400"
      ]
    }
  }
}
```

## Stopping the Container

To stop the container:

```bash
docker stop unity-mcp-server
``` 
