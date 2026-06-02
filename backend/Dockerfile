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

# Application dependencies (from poetry.lock, excluding unstructured and its ML extras).
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
    "pyjwt==2.13.0" \
    "tiktoken==0.13.0" \
    "pandas>=2.0,<3" \
    "python-multipart==0.0.30"

# Unstructured without ML/vision extras — install core package with --no-deps, then only
# the libraries needed for fast PDF, Office, and spreadsheet parsing.
ARG UNSTRUCTURED_VERSION=0.16.25
RUN pip install --no-cache-dir "unstructured==${UNSTRUCTURED_VERSION}" --no-deps && \
    pip install --no-cache-dir \
      "pdfminer.six" \
      "pypdf" \
      "pi-heif" \
      "unstructured.pytesseract>=0.3.12" \
      "openpyxl" \
      "xlrd" \
      "networkx" \
      "backoff" \
      "beautifulsoup4" \
      "chardet" \
      "dataclasses-json" \
      "emoji" \
      "filetype" \
      "html5lib" \
      "langdetect" \
      "lxml" \
      "nltk" \
      "numpy<2" \
      "psutil" \
      "python-iso639" \
      "python-magic" \
      "python-oxmsg" \
      "rapidfuzz" \
      "requests" \
      "tqdm" \
      "typing-extensions" \
      "unstructured-client" \
      "wrapt"

RUN mkdir -p /usr/local/nltk_data && \
    NLTK_DATA=/usr/local/nltk_data python -m nltk.downloader averaged_perceptron_tagger_eng punkt_tab

COPY backend/ .
COPY scripts /app/scripts

FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    libreoffice-writer-nogui \
    libmagic1 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NLTK_DATA=/usr/local/nltk_data

WORKDIR /app/backend

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/nltk_data /usr/local/nltk_data
COPY --from=builder /app/backend /app/backend
COPY --from=builder /app/scripts /app/scripts

EXPOSE 8000

CMD ["sh", "-c", "DATABASE_URL=$(echo \"$DATABASE_URL\" | sed 's/postgresql+asyncpg/postgresql/') alembic upgrade head && python /app/scripts/seed.py --dev && uvicorn main:app --host 0.0.0.0 --port 8000"]
