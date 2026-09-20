FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/api \
    PORT=8080

WORKDIR /app

COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

COPY schema /app/schema
COPY seeds /app/seeds
COPY api /app/api

WORKDIR /app/api
EXPOSE 8080

CMD ["sh", "-c", "echo Starting on 0.0.0.0:${PORT:-8080} && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
