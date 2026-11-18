FROM python:3.11-slim
WORKDIR /app/backend
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
ENV STORAGE_DIR=/data/storage MODELS_CACHE_DIR=/data/models_cache \
    DATABASE_URL=sqlite+aiosqlite:////data/awaaz.db
EXPOSE 8000
# download_models.py skips files that already exist, so this is safe with a volume
CMD ["sh","-c","python scripts/download_models.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]