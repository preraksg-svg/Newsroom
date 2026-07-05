import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.db.queries import init_db
from backend.headline_engine import initialize_headline_engine
from backend.thumbnail_engine import initialize_thumbnail_engine
from bandit_engine import initialize_bandit_engine
from ab_testing import initialize_ab_testing
from thumbnail_ab_testing import initialize_thumbnail_ab_testing

# Initialize database schema before importing route modules that depend on services.
init_db()

# Auto-seed sources if registry is empty
try:
    from backend.db.queries import get_db
    with get_db() as conn:
        cur = conn.cursor()
        # Ensure source_scores table exists and is seeded
        cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='source_scores'")
        has_table = cur.fetchone()[0] > 0
        is_empty = True
        if has_table:
            cur.execute("SELECT count(*) FROM source_scores")
            is_empty = cur.fetchone()[0] == 0
            
        if is_empty:
            print("[BACKEND] source_scores table is empty! Seeding reliable sources...")
            from seed_reliable_sources import seed
            seed()
except Exception as se:
    print(f"[BACKEND] Auto-seeding failed or skipped: {se}")

initialize_headline_engine()
initialize_thumbnail_engine()
initialize_bandit_engine()
initialize_ab_testing()
initialize_thumbnail_ab_testing()


from backend.routes.api_routes import router

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("ZAPWAY_AUTO_START_WORKERS", "false").lower() in {"0", "false", "no"}:
        print("[BACKEND] Worker auto-start explicitly disabled. Run 'python run_workers.py' separately.")
        yield
        return

    try:
        print("[BACKEND] Starting background worker engines directly inside FastAPI event loop...")
        import sys
        import asyncio
        if PROJECT_ROOT not in sys.path:
            sys.path.append(PROJECT_ROOT)
        import run_workers
        asyncio.create_task(run_workers.main())
        print("[BACKEND] Background worker engines successfully initialized within the same process.")
        yield
    except Exception as e:
        print(f"[BACKEND] Failed to start workers inline: {e}")
        yield



app = FastAPI(title="Zapway Production API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import FileResponse

# Static files for audio/images
STATIC_DIR = os.path.join(os.path.dirname(__file__), '../static')
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include modular routes
app.include_router(router)

# Serve Frontend Production Build
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), '../frontend/dist')

# Mount assets explicitly to handle static files efficiently
ASSETS_DIR = os.path.join(FRONTEND_DIST, "assets")
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    # Check if a specific file exists in the root of dist (e.g. favicon, manifest)
    file_path = os.path.join(FRONTEND_DIST, full_path)
    if full_path != "" and os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Fallback to index.html for all other paths (SPA)
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend build not found. Run 'npm run build' in the frontend directory."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
