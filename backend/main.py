"""
Ceyel — Process Intelligence with Cryptographic Trust
Main FastAPI application entrypoint.

Registers all module routers and serves the frontend dashboard as static files.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database.db import init_db
from backend.ingestion.router import router as ingestion_router
from backend.process_mining.router import router as mining_router
from backend.conformance.router import router as conformance_router
from backend.prediction.router import router as prediction_router
from backend.trust.router import router as trust_router
from backend.blockchain.router import router as blockchain_router

# ── App initialization ──────────────────────────────────────────────────────

app = FastAPI(
    title="Ceyel — Process Intelligence API",
    description=(
        "4-layer process intelligence system with cryptographic trust. "
        "Layers: Event Ingestion → Process Mining → Trust (Merkle) → Blockchain Ledger."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow the browser dashboard to call the API freely when served from the
# same origin or from a dev server on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register API routers ────────────────────────────────────────────────────

app.include_router(ingestion_router)
app.include_router(mining_router)
app.include_router(conformance_router)
app.include_router(prediction_router)
app.include_router(trust_router)
app.include_router(blockchain_router)

# ── Static frontend ─────────────────────────────────────────────────────────

# BASE_DIR is the root project directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_dashboard():
        """Serve the frontend dashboard at the root URL."""
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# Mount the data/ directory so the browser can fetch /data/sample_events.json
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

# ── Startup event ───────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    """Initialize the SQLite database tables on first run."""
    init_db()
    print("[OK] Ceyel backend started. Database initialized.")
    print("[INFO] Dashboard: http://localhost:8000")
    print("[INFO] API Docs:  http://localhost:8000/docs")
