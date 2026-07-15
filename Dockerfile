# ── Stage 1: Build React frontend ────────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
# Empty VITE_API_URL = relative URLs (same-origin, served by FastAPI)
ENV VITE_API_URL=""
ENV VITE_WS_URL=""
RUN npm run build

# ── Stage 2: Python backend + serve frontend ──────────────────────────────────
FROM python:3.11-slim

# Install git (needed for GitPython and workspace cloning)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built React app from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# HF Spaces requires port 7860
ENV PORT=7860
ENV HOST=0.0.0.0

# Create workspace dir for cloned repos
RUN mkdir -p /app/workspace

EXPOSE 7860

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860"]
