# syntax=docker/dockerfile:1

# --- frontend: build the Vite+ bundle ---
FROM node:24-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- runtime: FastAPI serving the API and, with SERVE_FRONTEND=1, the built bundle ---
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv

RUN useradd --create-home --uid 10001 dfis

COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY app ./app

COPY --from=frontend /build/frontend/dist ./frontend/dist

# app/main.py serves <repo>/frontend/dist when SERVE_FRONTEND=1
ENV SERVE_FRONTEND=1

USER dfis
EXPOSE 8000
# PORT lets a managed host (Render, Railway, Fly.io) choose the port; local default 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
