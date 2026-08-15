FROM python:3.12-slim

WORKDIR /app
COPY backend/shared /app/backend/shared
COPY backend/services/gateway /app/backend/services/gateway

WORKDIR /app/backend/services/gateway
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app/backend/shared:.
EXPOSE 8001

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
