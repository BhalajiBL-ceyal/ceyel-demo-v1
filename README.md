# Ceyel — Process Intelligence with Cryptographic Trust

> A fully local, production-style process intelligence system with event ingestion, process mining, ML prediction, SHA-256 Merkle trust, and a simulated blockchain ledger.

---

##  Quick Start (Windows)

**One double-click is all you need:**

```
ceyel/run.bat
```

The batch file will:
1. Check Python is installed
2. Install all dependencies (`pip install -r requirements.txt`)
3. Start the FastAPI backend on `http://localhost:8000`
4. Open the dashboard in your browser automatically

> **Requires:** Python 3.9+ on PATH. Download from [python.org](https://python.org).

---

##  Loading Sample Data

After the server starts, click **"📥 Load Sample Data"** on the dashboard to load 60 pre-built loan approval events across 10 cases. This also commits the genesis blockchain block automatically.

Alternatively, from the command line inside the `ceyel/` folder:
```powershell
python load_sample_data.py
```

Or directly via curl (requires curl on PATH):
```powershell
curl -X POST http://localhost:8000/api/events/bulk -H "Content-Type: application/json" -d @data/sample_events.json
```

---

##  Architecture

```
ceyel/
│
├── backend/
│   ├── main.py                   ← FastAPI app entry point
│   ├── database/
│   │   └── db.py                 ← SQLite via SQLAlchemy
│   ├── ingestion/
│   │   ├── models.py             ← Pydantic schemas
│   │   ├── service.py            ← Normalize + hash + store events
│   │   └── router.py             ← POST /api/events, GET /api/events
│   ├── process_mining/
│   │   ├── graph.py              ← DFG, variants, cycle time
│   │   └── router.py             ← GET /api/mining/*
│   ├── conformance/
│   │   ├── checker.py            ← Missing/extra/order deviation detection
│   │   └── router.py             ← POST /api/conformance/check
│   ├── prediction/
│   │   ├── model.py              ← RandomForest remaining time + delay risk
│   │   └── router.py             ← GET /api/prediction/{case_id}
│   ├── trust/
│   │   ├── hasher.py             ← SHA-256 canonical event hashing
│   │   ├── merkle.py             ← Merkle Tree, root, inclusion proofs
│   │   └── router.py             ← GET /api/trust/root, /proof/{case_id}
│   └── blockchain/
│       ├── ledger.py             ← Append-only JSON block ledger
│       └── router.py             ← POST /api/blockchain/commit
│
├── frontend/
│   ├── index.html                ← Single-page dashboard
│   ├── app.js                    ← D3 DFG graph + Chart.js + API calls
│   └── style.css                 ← Premium dark-mode design system
│
├── data/
│   ├── sample_events.json        ← 60 sample loan approval events
│   ├── ceyel.db                  ← SQLite database (auto-created)
│   └── ledger.json               ← Blockchain ledger (auto-created)
│
├── output/                       ← Output directory for exports
├── requirements.txt
├── load_sample_data.py           ← Script to preload data via API
├── run.bat                       ← Windows launcher
└── README.md
```

---

##  API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/events` | Ingest single event |
| POST | `/api/events/bulk` | Ingest array of events |
| GET  | `/api/events` | List all events |
| GET  | `/api/events/{case_id}` | Get events for a case |
| GET  | `/api/mining/dfg` | Directly-Follows Graph |
| GET  | `/api/mining/variants` | Process variants |
| GET  | `/api/mining/cycle-time` | Cycle time per case |
| GET  | `/api/mining/stats` | Summary statistics |
| POST | `/api/conformance/check` | Custom conformance check |
| GET  | `/api/conformance/default` | Default loan process check |
| GET  | `/api/prediction` | Predictions for all cases |
| GET  | `/api/prediction/{case_id}` | Prediction for one case |
| GET  | `/api/trust/root` | Global Merkle root |
| GET  | `/api/trust/proof/{case_id}` | Inclusion proof for a case |
| GET  | `/api/trust/hashes` | All event hashes |
| POST | `/api/blockchain/commit` | Commit new block |
| GET  | `/api/blockchain/chain` | Full ledger |
| GET  | `/api/blockchain/verify` | Verify chain integrity |

> **Interactive Docs:** `http://localhost:8000/docs`

---

## 4-Layer System Design

| Layer | Module | Description |
|-------|--------|-------------|
| **Layer 1** | Event Ingestion | JSON events → SQLite, SHA-256 hashed |
| **Layer 2** | Process Mining | DFG, variants, cycle time, conformance, ML prediction |
| **Layer 3** | Trust (Cryptographic) | Merkle Tree, inclusion proofs, tamper detection |
| **Layer 4** | Blockchain Simulation | Append-only local ledger, chain integrity verification |

---

##  Dependencies

```
fastapi          — Web framework
uvicorn          — ASGI server
sqlalchemy       — SQLite ORM
pydantic         — Data validation
networkx         — Graph analytics (process mining)
scikit-learn     — ML prediction (RandomForest)
numpy            — Numerical operations
aiofiles         — Async file serving
```

Install manually: `pip install -r requirements.txt`
