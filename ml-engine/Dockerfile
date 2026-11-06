FROM python:3.10-slim

# TensorFlow slim build; install CPU-only to keep image size manageable
RUN pip install --no-cache-dir \
    scikit-learn \
    pandas \
    numpy \
    joblib \
    matplotlib \
    influxdb-client \
    redis \
    fastapi \
    "uvicorn[standard]" \
    tensorflow-cpu \
    keras \
    xgboost

WORKDIR /app

COPY trainer.py .
COPY detector.py .
COPY xgboost_suite.py .

EXPOSE 8000

CMD ["python", "-u", "trainer.py"]
