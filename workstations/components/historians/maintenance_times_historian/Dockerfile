FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY components/ ./components/
COPY database-files/ ./database-files/
EXPOSE 5002
CMD ["python", "-c", "from components.historians.maintenance_times_historian.app import create_app; app=create_app(); app.run(host='0.0.0.0', port=5002)"]
