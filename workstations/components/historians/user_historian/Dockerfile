# Historian Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy components
COPY components/ ./components/
COPY run.py .

# Create logs directory
RUN mkdir -p logs db

# Expose port
EXPOSE 5000

# Run the app
CMD ["python", "run.py"]
