# ── Stage 1: build website_app frontend ────────────────────────────────────────
FROM node:22-slim AS frontend-build
WORKDIR /build/website_app
COPY website_app/package*.json ./
RUN npm ci --prefer-offline
COPY website_app/ ./
RUN npm run build

# ── Stage 2: Python runtime ──────────────────────────────────────────────────────
FROM python:3.11-slim

# System deps for OpenCV headless + Pillow + Shapely
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps first (cached unless requirements.txt changes)
COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App source
COPY apps/api/ ./apps/api/

# Pre-seeded data (images, overlays, PDFs, SQLite) — Railway will overlay
# the persistent volume on /data, so the container's /data/agriscout.db acts
# as the fallback only on first boot before the volume is mounted.
COPY data/ ./data/
COPY demo/ ./demo/

# Frontend build output – FastAPI mounts website_app/dist at startup when found
COPY --from=frontend-build /build/website_app/dist ./website_app/dist

# Entrypoint: seed (idempotent), then serve
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/apps/api

# Railway injects PORT; default to 8000 locally
EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
