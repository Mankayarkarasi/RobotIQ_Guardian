
FROM python:3.11-slim

WORKDIR /app

# Python configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080

# Install backend Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
COPY backend/adk-requirements.txt /app/backend/adk-requirements.txt

RUN pip install --no-cache-dir \
    -r /app/backend/requirements.txt

# Copy FastAPI backend and PoC data
COPY backend/ /app/backend/
COPY data/ /app/data/

# Cloud Run container port
EXPOSE 8080

# Start FastAPI
CMD ["sh", "-c", "exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
