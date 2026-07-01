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

# Install system dependencies for Playwright (browser rendering) and SQLite
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser engines (Chromium is used for Twitter/website scraping)
RUN playwright install chromium

# Copy frontend compiled assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy backend application files
COPY . .

# Expose port and run the unified server (with auto-started background workers)
ENV PORT=8000
ENV ZAPWAY_AUTO_START_WORKERS=true
EXPOSE 8000

CMD ["python", "-m", "backend.main"]
