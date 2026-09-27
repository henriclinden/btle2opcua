FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output for log streaming
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime dependencies for BlueZ D-Bus communication
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bluez \
       dbus \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY btle2opcua/ ./btle2opcua/

# Default OPC UA server port
EXPOSE 4840

# Run the gateway module
CMD ["python", "-m", "btle2opcua.main"]
