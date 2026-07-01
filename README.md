# Zapway Newsroom - Unified Production Stack

AI-driven automated newsroom for the EV industry. This repository has been consolidated into a single production-grade backend package.

## Installation

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright Browsers:**
   (Required for social media scraping)
   ```bash
   playwright install chromium
   ```

3. **Environment Variables:**
   Copy `.env.example` to `.env` and fill in your keys (`GROQ_API_KEY`, etc.).
   ```bash
   cp .env.example .env
   ```

## Running the System

### 1. Start the API Server (Production Entry Point)
The API server handles the dashboard, editorial actions, and serves the frontend.
```bash
python -m backend.main
```
The server will run on `http://localhost:8000`.

### 2. Start the Background Workers
Run the multi-channel ingestion, AI processing, and media generation loops.
**IMPORTANT:** Heavy editorial actions (Audio, Images, Social Bundles) are enqueued and processed by the `Media Worker`. You MUST have this running for those assets to generate.
```bash
python run_workers.py
```

Workers are not auto-started by the API by default. To opt into API-managed worker startup, set:
```bash
set ZAPWAY_AUTO_START_WORKERS=1
python -m backend.main
```

### 3. Frontend Development
For active UI development with hot-reloading:
```bash
cd frontend
npm install
npm run dev
```
Development dashboard: `http://localhost:5173`.

### 4. Production Build & Verification
To verify the full-stack integration:
1. Build the frontend: `cd frontend && npm run build`
2. Start the unified backend: `python -m backend.main`
3. Access the full app (API + UI) at `http://localhost:8000`

### 5. Quick Verification
Verify the backend package is correctly initialized:
```bash
python -c "import backend.db.queries; import backend.services.news_service; print('Production Backend Verified')"
```

## Features
- **Multi-Channel Ingestion:** Automated YouTube, Twitter, and Web scraping.
- **AI Orchestration:** Groq-powered intelligence for summarization and editing.
- **Unified DB Schema:** Single source of truth for editorial and analytics.
- **Asset Pipeline:** Automated generation of audio (gTTS) and images.
