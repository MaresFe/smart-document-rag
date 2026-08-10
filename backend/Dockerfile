FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/home/app/.cache/huggingface

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        libgomp1 \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-tur \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/backend

COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /workspace/uploads /home/app/.cache/huggingface \
    && chown -R app:app /workspace /home/app

COPY --chown=app:app backend/ ./
COPY --chown=app:app docker/backend/entrypoint.sh /usr/local/bin/smart-rag-entrypoint
RUN chmod 755 /usr/local/bin/smart-rag-entrypoint

USER app

EXPOSE 8000

ENTRYPOINT ["smart-rag-entrypoint"]
