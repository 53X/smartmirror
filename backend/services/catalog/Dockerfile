FROM python:3.12-slim

WORKDIR /app
COPY backend/shared /app/backend/shared
COPY backend/services/catalog /app/backend/services/catalog

WORKDIR /app/backend/services/catalog
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app/backend/shared:.
ENV CATALOG_DATA_DIR=/data/catalog
EXPOSE 8002

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8002}"]
