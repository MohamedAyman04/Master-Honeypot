FROM master-honeypot-workstation-1:latest

WORKDIR /app

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8010 8443

CMD ["python", "app.py"]
