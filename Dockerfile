# ==============================================================================
# JuriVision Pro — Dockerfile Multi-Stage Unificado (Google Cloud Run / Render)
# ==============================================================================
# Stage 1: Build estático de produção do Front-end (Vite)
FROM node:20-alpine AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime Python FastAPI servindo API REST + Bundle Estático SPA
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    SERVE_FRONTEND_STATIC=true \
    FREE_PLAN_PDF_LIMIT=3 \
    PORT=8000

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

COPY backend/ ./backend/
COPY ai_engine/ ./ai_engine/
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-8000}"]
