# ── Builder ───────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install uv

# Layer 1: install dependencies only (cached until pyproject.toml changes)
COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

# Layer 2: copy source and install the package itself
COPY src/ ./src/
RUN uv sync --no-dev --no-editable


# ── Development ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS development

# Install system deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxcb1 libxkbcommon0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    curl wget && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install Playwright browsers
RUN playwright install chromium

COPY . .

CMD ["celery", "-A", "scholarscout.contexts.crawler.workers.celery_app", "worker", \
     "--loglevel=info"]


# ── Production ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxcb1 libxkbcommon0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --no-create-home appuser

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

RUN playwright install chromium

COPY --chown=appuser:appgroup src/ ./src/

USER appuser

CMD ["celery", "-A", "scholarscout.contexts.crawler.workers.celery_app", "worker", \
     "--loglevel=info"]
