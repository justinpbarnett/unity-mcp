FROM python:3.12-slim

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv package manager
RUN pip install uv

# Copy required files
COPY config.py /app/
COPY server.py /app/
COPY unity_connection.py /app/
COPY pyproject.toml /app/
COPY __init__.py /app/
COPY tools/ /app/tools/

# Install dependencies using uv
RUN uv pip install --system -e .

# Create a simple entrypoint script to run the server with any provided arguments
RUN echo '#!/bin/sh\nexec uv run server.py "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Use the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"] 