# OPC UA Server Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy components
COPY components/ ./components/

# Create logs directory
RUN mkdir -p logs

# Expose OPC UA port
EXPOSE 4840

# Run the server
CMD ["python", "components/opcua/opcua_1/opcua_server_run.py"]
