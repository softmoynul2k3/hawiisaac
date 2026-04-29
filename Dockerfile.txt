# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

WORKDIR /app


RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc default-libmysqlclient-dev pkg-config   

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Final Stage ───
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-mysql-client curl && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN addgroup --system app && adduser --system --ingroup app app

COPY --from=builder /install /usr/local
COPY --chown=app:app . .

RUN mkdir -p /app/media /app/templates/static && chown -R app:app /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MEDIA_DIR=/app/media \
    MEDIA_ROOT=/app/media

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]