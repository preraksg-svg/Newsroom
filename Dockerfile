# Stage 1: Build the Frontend React Application
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the FastAPI Python Backend
FROM python:3.11-slim
WORKDIR /app

# Install basic system utilities
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Configure Playwright to use a shared directory and install browser with all system dependencies
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir /ms-playwright && PLAYWRIGHT_BROWSERS_PATH=/ms-playwright playwright install --with-deps chromium

# Copy frontend compiled assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy backend application files
COPY . .

# Expose port and run the unified server (with auto-started background workers)
ENV PORT=8000
ENV ZAPWAY_AUTO_START_WORKERS=true
EXPOSE 8000

CMD sh -c "python scratch/cleanup_existing_stories.py && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"
