# Root Dockerfile for Hugging Face Spaces linked to this GitHub repo.
# Build context = repository root.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/apps/api/requirements.txt

COPY services/__init__.py /app/services/__init__.py
COPY services/translation /app/services/translation
COPY apps/api /app/apps/api

ENV PYTHONPATH=/app
EXPOSE 7860

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
