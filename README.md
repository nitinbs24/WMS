# Warehaven

**AI-Assisted 3D Warehouse Digital Twin & Slotting Optimization System**

Warehaven ingests product and order data, runs one of six slotting algorithms to decide where inventory should physically sit on the racks, and renders the result as an interactive 3D digital twin so a warehouse manager can see — and adjust — the entire facility at a glance.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite, react-three-fiber + drei (3D), TanStack Query, Zustand, React Router |
| Backend | FastAPI (Python 3.12), Pydantic v2, SQLAlchemy 2.0 async + asyncpg |
| Database | PostgreSQL 16 |
| Background Jobs | Redis 7 + arq |
| Auth | JWT (access + refresh tokens), bcrypt, role-based (Admin / Manager / Staff) |
| Logging | structlog (JSON in prod, pretty in dev) |
| Dev environment | Docker Compose (single command boot) |
| CI | GitHub Actions (lint + test on every PR) |

## Getting Started (Local)

### Prerequisites
- Docker & Docker Compose
- Node.js 22 (for frontend-only dev)
- Python 3.12 (for backend-only dev)

### Full stack (Docker Compose)

```bash
# 1. Copy env file and fill in secrets
cp .env.example .env

# 2. Start all services (api, worker, db, redis, web)
docker compose up

# 3. Run DB migrations
docker compose exec api alembic upgrade head

# Services:
#   API:      http://localhost:8000  (FastAPI + auto OpenAPI docs at /docs)
#   Frontend: http://localhost:5173
#   DB:       localhost:5432
#   Redis:    localhost:6379
```

Default admin credentials are set in `.env` (`SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD`).
The admin user and default threshold settings are created automatically on first startup.

### Backend only

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend only

```bash
cd frontend
npm install
npm run dev
```

## Repository Structure

```
warehaven/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routers (auth, users, layout, products, runs, ...)
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic v2 request/response schemas
│   │   ├── services/      # Business logic layer
│   │   ├── algorithms/    # Pure optimization algorithm modules (no framework deps)
│   │   │   ├── space/     # FFDH+CoM, BLF+Stratified, W-BFDH
│   │   │   └── picking/   # Golden Zone, Affinity Clustering, S-Shape Routing
│   │   ├── workers/       # arq background job definitions
│   │   ├── data_sources/  # Adapter interface (mock v1 / Odoo Phase 2)
│   │   └── core/          # Config, database, security, logging
│   ├── alembic/           # DB migrations
│   ├── seed/              # Mock dataset (JSON files)
│   └── tests/             # pytest test suite
├── frontend/
│   └── src/
│       ├── api/           # REST client (typed fetch wrappers)
│       ├── pages/         # Route-level page components
│       ├── scene/         # react-three-fiber 3D components (Phase 6)
│       ├── store/         # Zustand UI state
│       └── components/    # Shared UI components
├── docker-compose.yml
├── .env.example
└── docs/
    ├── Warehaven_PRD.md   # Product requirements
    └── Warehaven_TRD.md   # Technical requirements
```

## Optimization Algorithms

| Goal | Algorithm | Stage | Selectable? |
|---|---|---|---|
| Space Efficiency | Modified FFDH + CoM Validation | Item → Pallet | Yes (1 of 2) |
| Space Efficiency | BLF + Weight Stratification | Item → Pallet | Yes (1 of 2) |
| Space Efficiency | W-BFDH | Pallet → Slot | Always runs |
| Picking Efficiency | Ergonomic Golden Zone | SKU → Slot | Yes (1 of 3) |
| Picking Efficiency | Apriori Affinity Clustering | SKU → Slot | Yes (1 of 3) |
| Picking Efficiency | S-Shape Pick-Path Routing | SKU → Slot | Yes (1 of 3) |

All algorithms live in `backend/app/algorithms/` as **pure functions** — no DB session, no HTTP context. This makes them independently unit-testable and benchmarkable.

## Roles & Permissions

| Action | Admin | Manager | Staff |
|---|---|---|---|
| View 3D twin, search SKUs | ✓ | ✓ | ✓ |
| Trigger an optimization run | ✓ | ✓ | ✗ |
| Override a slot assignment | ✓ | ✓ | ✗ |
| Import warehouse layout | ✓ | ✗ | ✗ |
| Edit threshold settings | ✓ | ✗ | ✗ |

## Development Phases

| Phase | Scope | Status |
|---|---|---|
| **Phase 1** | Foundation: Docker, FastAPI skeleton, all models, frontend scaffold | ✅ Branch created |
| **Phase 2** | Auth, RBAC, user management end-to-end | 🔜 Next |
| **Phase 3** | Layout import, mock data generator | 🔜 |
| **Phase 4** | All 6 optimization algorithms (pure functions + unit tests) | 🔜 |
| **Phase 5** | Run execution (arq), background jobs, admin settings, exports | 🔜 |
| **Phase 6** | 3D digital twin, overlays, drag-and-drop override, SKU search | 🔜 |
| **Phase 7** | CI/CD polish, performance profiling, documentation | 🔜 |

## Running Tests

```bash
# Backend
cd backend && pytest -v --cov=app

# Frontend
cd frontend && npm test
```

## API Documentation

FastAPI auto-generates interactive API docs at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` (ReDoc) when the API is running.
