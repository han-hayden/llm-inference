# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AICP LLM Inference Performance Testing Tool — a full-stack platform that proxies LLM API requests, collects performance metrics (TTFT, TPOT, TPS, E2E latency, token counts, cache hits), runs load tests, compares baseline vs optimized results, and generates PDF reports.

## Development Commands

### Frontend (Vue 3 + TypeScript + Vite)
```bash
cd frontend
npm install
npm run dev          # Dev server on port 3000 (proxies /api/ and /proxy/ to :8081)
npm run build        # vue-tsc -b && vite build
npx vue-tsc --noEmit # Type-check only (no emit)
```

Mock mode: set `VITE_USE_MOCK=true` in `frontend/.env.development` to use fake API data without a backend.

### Backend (Python 3.11 + FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload
```

All config via env vars with `AICP_` prefix (see `backend/app/config.py`). Default credentials: admin/changeme.

### Docker
```bash
docker build -f docker/Dockerfile -t aicp-perf-tool:1.0.0 .
# Exposes: 8080 (nginx+frontend), 8081 (API), 22 (SSH optional)
# Volume: /data/results
```

## Architecture

```
frontend/ (Vue 3, Naive UI, ECharts, Axios)
  ├── src/api/index.ts        — All API client functions (axios instance)
  ├── src/api/mock.ts          — Dev mock interceptor (conditional)
  ├── src/router/index.ts      — Routes: /config, /analysis, /benchmark, /compare, /records
  └── src/views/               — Page components (LayoutView wraps all pages with sidebar)

backend/app/ (FastAPI, SQLAlchemy, aiohttp)
  ├── main.py                  — App init, lifespan (DB init + default user), router registration
  ├── config.py                — Pydantic BaseSettings (AICP_ prefix)
  ├── models/
  │   ├── database.py          — SQLAlchemy async engine + session (aiosqlite)
  │   └── schemas.py           — ORM models: User, ProxyConfig, Task
  ├── auth/router.py           — JWT auth (python-jose, passlib)
  ├── proxy/forwarder.py       — Core: transparent proxy with metrics extraction
  ├── collect/                 — Start/stop collection, task lifecycle, CSV/JSON writer
  ├── files/router.py          — Read task CSV data (performance + QA)
  ├── metrics/router.py        — Compute distributions & summary stats from CSV
  ├── benchmark/router.py      — Async load testing (replay QA pairs concurrently)
  ├── compare/router.py        — Baseline vs optimized comparison
  ├── report/router.py         — PDF generation (ReportLab + matplotlib)
  └── analysis/                — Suggestion engine (placeholder)
```

### Request Flow
Frontend (:3000 dev / :8080 prod via nginx) → FastAPI (:8081) → SQLite + CSV/JSON files in `/data/results/`

### Data Storage
- SQLite DB at `/data/results/tasks.db` — tasks, users, proxy config
- CSV files per task: `performance_data_*.csv` (rotated every 1000 rows), `qa_data_*.csv`
- JSON: `summary_*.json` per task
- PDF reports in `/data/results/reports/`

## Key Conventions

- **Frontend styling**: Dark theme, glass-morphism cards (`rgba(255,255,255,0.04)` + backdrop-filter), accent gradient `linear-gradient(135deg, #00f0ff, #7c3aed)`. All pages use `.glass-card` and `.accent-btn` CSS classes.
- **API pattern**: Every API function in `frontend/src/api/index.ts` returns an Axios response. Views destructure with `res.data?.data ?? res.data` to handle both `{data: {…}}` and flat response shapes.
- **Backend routers**: Each feature module has its own `router.py` with an `APIRouter`. Registered in `main.py` with prefix `/api/<module>`.
- **No tests or linting configured** in the main project. The `llm-inference-forward/` subdirectory is a separate open-source project.
- **Language**: UI text is in Chinese. Code comments and variable names are in English.

## Deployment

- **Docker**: Multi-stage build (Node 20 → Python 3.11 slim). Supervisor manages nginx + uvicorn + sshd.
- **Kubernetes**: Helm chart in `helm-chart/`. NodePort service, 10Gi PVC for data.
- **Env vars**: `AICP_ADMIN_PASSWORD`, `SSH_ENABLED`, `AICP_DATA_DIR`, `AICP_SECRET_KEY`.
