# syntax=docker/dockerfile:1.6

# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY tests/ ./tests/
COPY pyproject.toml ./

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app -d /app app

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

USER app

EXPOSE 8080

ENV HEALTH_PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["celery", "-A", "app.celery_app", "worker", "--loglevel=info", "--concurrency=4", "-Q", "notifications"]
