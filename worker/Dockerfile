# Dedicated Dockerfile for Python Worker
FROM python:3.11-slim

# Install system compilation binaries (g++, gcc, build-essential, openjdk) and Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    default-jdk-headless \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli || true \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create shared workspace directory for compilation & execution
RUN mkdir -p /runtime-workspaces

# Copy backend dependencies and install
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app and worker modules
COPY backend/app ./backend/app
COPY worker ./worker

ENV PYTHONPATH="/app/backend:/app/worker:${PYTHONPATH}"
ENV WORKER_WORKSPACE_DIR="/runtime-workspaces"

CMD ["python", "worker/worker.py"]
