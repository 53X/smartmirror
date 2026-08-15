FROM python:3.12-slim

WORKDIR /app
COPY backend/shared /app/backend/shared
COPY backend/services/ai_service /app/backend/services/ai_service

WORKDIR /app/backend/services/ai_service
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app/backend/shared:.
ENV AI_DATA_DIR=/data/ai
EXPOSE 8003

CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8003}"]
