# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app/backend

# Application dependencies (ADR 002 lightweight extractors — no Unstructured ML stack).
RUN pip install --no-cache-dir \
    "alembic==1.18.4" \
    "asyncpg==0.31.0" \
    "bcrypt==5.0.0" \
    "boto3==1.43.18" \
    "fastapi==0.115.14" \
    "uvicorn[standard]==0.32.1" \
    "sqlalchemy==2.0.50" \
    "psycopg2-binary==2.9.12" \
    "pgvector==0.3.6" \
    "pydantic[email]==2.13.4" \
    "pydantic-settings==2.14.1" \
    "structlog==24.4.0" \
    "python-docx==1.2.0" \
    "pdfminer.six" \
    "openpyxl" \
    "pyjwt==2.13.0" \
    "tiktoken==0.13.0" \
    "pandas>=2.0,<3" \
    "python-multipart==0.0.30"

ENV TIKTOKEN_CACHE_DIR=/usr/local/tiktoken_cache
RUN mkdir -p "$TIKTOKEN_CACHE_DIR" && python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

# Bust remote build cache when backend sources change.
ARG BACKEND_CACHE_BUST=20260605
COPY backend/ .
COPY scripts /app/scripts
COPY docs/instructions /app/docs/instructions

FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer-nogui \
    libmagic1 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TIKTOKEN_CACHE_DIR=/usr/local/tiktoken_cache

WORKDIR /app/backend

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/tiktoken_cache /usr/local/tiktoken_cache
COPY --from=builder /app/backend /app/backend
COPY --from=builder /app/scripts /app/scripts
COPY --from=builder /app/docs/instructions /app/docs/instructions

EXPOSE 8000

CMD ["sh", "-c", "DATABASE_URL=$(echo \"$DATABASE_URL\" | sed 's/postgresql+asyncpg/postgresql/') alembic upgrade head && python /app/scripts/seed.py --dev && uvicorn main:app --host 0.0.0.0 --port 8000"]
