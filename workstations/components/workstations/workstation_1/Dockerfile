# Workstation Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy workstation app and run script
COPY components/ ./components/
COPY workstation_run.py .

# Expose port
EXPOSE 5001

# Run the app
CMD ["python", "workstation_run.py"]
