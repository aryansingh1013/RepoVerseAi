# Backend-only Dockerfile for Render (Free Tier)
FROM python:3.11-slim

# Install git (needed for GitPython and workspace cloning)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/
COPY app.py ./app.py

# Create workspace dir for cloned repos
RUN mkdir -p /app/workspace

# Render injects PORT at runtime — default to 10000 if not set
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

# Expose the default Render port
EXPOSE 10000

CMD ["python", "app.py"]

