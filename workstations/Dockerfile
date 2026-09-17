# Purdue Level 3 Enterprise Workstation Honeypot
FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install system dependencies & network tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    dnsutils \
    curl \
    iproute2 \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy components and runtime files
COPY components/ ./components/
COPY database-files/ ./database-files/
COPY workstation_run.py .

RUN mkdir -p /app/logs /app/database-files/workstations

EXPOSE 5001

CMD ["python", "workstation_run.py"]
