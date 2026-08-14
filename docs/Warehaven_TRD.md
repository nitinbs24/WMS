# Technical Requirements Document: Warehaven

**Status:** Draft v1.0
**Date:** August 14, 2026
**Companion doc:** Warehaven PRD v1.0 (product scope, decisions, rationale)
**Companion doc:** Warehouse Optimization — Algorithm Implementation Report (V.V.C.E Mysore, July 2026) — canonical spec for algorithm mechanics/pseudocode
**Deployment scope:** Local-only build (Docker Compose). Production hosting details in this doc describe the future, gated phase (see PRD §10).

This document translates the PRD's product decisions into concrete engineering specs: schema, API contracts, module boundaries, and technical constraints. Where the PRD says *what* and *why*, this says *how*. It assumes the reader has the PRD and the algorithm report open alongside it.

---

## 1. System Architecture

```
┌─────────────────────┐        ┌──────────────────────────┐
│   React SPA (Vite)   │ HTTPS  │        FastAPI app        │
│  react-three-fiber    │◄──────►│  (REST API, auth, valid.) │
│  TanStack Query        │       └───────────┬────────────┘
└─────────────────────┘                       │
                                                │ enqueues jobs
                                    ┌───────────▼────────────┐
                                    │      Redis (broker)      │
                                    └───────────┬────────────┘
                                                │
                                    ┌───────────▼────────────┐
                                    │   arq worker process     │
                                    │ (runs optimization jobs) │
                                    │  → calls algorithm       │
                                    │    modules (§7)          │
                                    └───────────┬────────────┘
                                                │
                                    ┌───────────▼────────────┐
                                    │       PostgreSQL          │
                                    └────────────────────────┘
```

- The **API process** never runs an optimization algorithm inline — it only validates the request, writes an `optimization_runs` row with status `queued`, and enqueues a job. This keeps every API response fast regardless of catalog size.
- The **worker process** is a separate container even in local dev (§10), so its resource usage (CPU-bound algorithm execution) never competes with or blocks API request handling.
- The **algorithm modules** (§7) have zero dependency on FastAPI, SQLAlchemy sessions, or HTTP — they take plain data structures in and return plain data structures out, so they're independently unit-testable and match 1:1 with the pseudocode in the algorithm report.

---

## 2. Repository Structure

```
warehaven/
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI routers, one file per domain (§5)
│   │   │   ├── auth.py
│   │   │   ├── layout.py
│   │   │   ├── products.py
│   │   │   ├── runs.py
│   │   │   ├── assignments.py
│   │   │   ├── exceptions.py
│   │   │   ├── settings.py
│   │   │   └── schedules.py
│   │   ├── models/              # SQLAlchemy models (§4)
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # business logic, orchestrates models + algorithms
│   │   ├── algorithms/          # pure, framework-free algorithm modules (§7)
│   │   │   ├── space/
│   │   │   │   ├── ffdh_com.py
│   │   │   │   ├── blf_stratified.py
│   │   │   │   └── wbfdh.py
│   │   │   └── picking/
│   │   │       ├── golden_zone.py
│   │   │       ├── affinity_clustering.py
│   │   │       └── s_shape_routing.py
│   │   ├── workers/             # arq task definitions (§8)
│   │   ├── data_sources/        # adapter interface + mock/odoo implementations (PRD §8.8)
│   │   ├── core/                # config, security, logging setup
│   │   └── main.py
│   ├── alembic/                 # migrations
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── scene/                # react-three-fiber components (racks, slots, pallets)
│   │   ├── pages/                # run config, admin settings, reports
│   │   ├── api/                  # generated/typed client against OpenAPI schema
│   │   └── store/                # Zustand UI state
│   └── package.json
├── docker-compose.yml
└── .env.example
```

---

## 3. Domain Enums

| Enum | Values |
|---|---|
| `user_role` | `admin`, `manager`, `staff` |
| `optimization_goal` | `space_efficiency`, `picking_efficiency` |
| `space_algorithm` | `ffdh_com`, `blf_stratified` *(W-BFDH is not user-selectable — see PRD §5.3; it always runs as the fixed slot-assignment step for whichever of these two ran)* |
| `picking_algorithm` | `golden_zone`, `affinity_clustering`, `s_shape_routing` |
| `run_scope` | `full`, `incremental` |
| `run_status` | `queued`, `running`, `completed`, `completed_with_exceptions`, `failed` |
| `slot_status` | `empty`, `occupied`, `reserved` |
| `abc_class` | `A`, `B`, `C` |
| `exception_status` | `open`, `resolved` |
| `import_status` | `validating`, `valid`, `invalid`, `applied` |

---

## 4. Database Schema (PostgreSQL)

All tables use `UUID` primary keys (`gen_random_uuid()`), `created_at`/`updated_at` timestamps (`timestamptz`, default `now()`), unless noted.

```sql
-- users
users (
  id UUID PK,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role user_role NOT NULL,
  created_at, updated_at
)

-- warehouses (single row in v1, FK kept for future multi-warehouse)
warehouses ( id UUID PK, name TEXT NOT NULL, created_at )

-- aisles
aisles (
  id UUID PK,
  warehouse_id UUID FK → warehouses,
  code TEXT NOT NULL,
  orientation TEXT NOT NULL,       -- 'horizontal' | 'vertical'
  direction TEXT,                  -- set by S-Shape routing runs
  created_at
)

-- racks
racks (
  id UUID PK,
  warehouse_id UUID FK → warehouses,
  aisle_id UUID FK → aisles,
  code TEXT NOT NULL,
  pos_x NUMERIC, pos_y NUMERIC, pos_z NUMERIC,
  level_count INT NOT NULL,
  created_at
)

-- slots
slots (
  id UUID PK,
  rack_id UUID FK → racks,
  level INT NOT NULL,
  clearance_height NUMERIC NOT NULL,
  weight_capacity NUMERIC NOT NULL,
  pos_x NUMERIC, pos_y NUMERIC, pos_z NUMERIC,
  is_aisle_boundary BOOLEAN DEFAULT FALSE,   -- used by S-Shape routing
  status slot_status NOT NULL DEFAULT 'empty',
  current_pallet_id UUID FK → pallets NULL,
  created_at, updated_at,
  UNIQUE (rack_id, level)
)

-- products (mirrors Odoo product.template; odoo_product_id nullable until Phase 2)
products (
  id UUID PK,
  sku TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  length NUMERIC NOT NULL, width NUMERIC NOT NULL, height NUMERIC NOT NULL,
  weight NUMERIC NOT NULL,
  category TEXT,
  abc_class abc_class,
  odoo_product_id INT NULL,
  created_at, updated_at
)

-- pallets
pallets (
  id UUID PK,
  computed_height NUMERIC, computed_weight NUMERIC, computed_volume NUMERIC,
  stability_status TEXT,   -- 'stable' | 'unstable'
  created_at
)

-- pallet_items (items placed within a pallet; drives CoM calc)
pallet_items (
  id UUID PK,
  pallet_id UUID FK → pallets,
  product_id UUID FK → products,
  quantity INT NOT NULL,
  x_pos NUMERIC, y_pos NUMERIC, z_pos NUMERIC   -- position within the pallet, for CoM
)

-- pick_events (mirrors Odoo stock.move; drives frequency-based algorithms)
pick_events (
  id UUID PK,
  product_id UUID FK → products,
  occurred_at TIMESTAMPTZ NOT NULL,
  quantity INT NOT NULL,
  odoo_move_id INT NULL
)

-- order_lines (mirrors Odoo sale.order.line; drives affinity clustering)
order_lines (
  id UUID PK,
  order_id UUID NOT NULL,
  product_id UUID FK → products,
  occurred_at TIMESTAMPTZ NOT NULL,
  odoo_order_line_id INT NULL
)

-- optimization_runs
optimization_runs (
  id UUID PK,
  goal optimization_goal NOT NULL,
  algorithm TEXT NOT NULL,               -- value from space_algorithm or picking_algorithm
  scope run_scope NOT NULL,
  triggered_by UUID FK → users NULL,     -- NULL = scheduled run
  status run_status NOT NULL DEFAULT 'queued',
  started_at, completed_at,
  thresholds_snapshot JSONB NOT NULL,    -- copy of active ThresholdSettings at run time
  summary_metrics JSONB,                 -- fill rate / travel estimate / exception count etc.
  created_at
)

-- slot_assignments
slot_assignments (
  id UUID PK,
  run_id UUID FK → optimization_runs,
  pallet_id UUID FK → pallets NULL,      -- NULL for picking-efficiency runs (SKU-level, no pallet)
  product_id UUID FK → products NULL,    -- populated for picking-efficiency runs
  slot_id UUID FK → slots,
  score NUMERIC,
  is_override BOOLEAN DEFAULT FALSE,
  overridden_by UUID FK → users NULL,
  overridden_at TIMESTAMPTZ NULL,
  created_at
)

-- exceptions
exceptions (
  id UUID PK,
  run_id UUID FK → optimization_runs,
  pallet_id UUID FK → pallets NULL,
  product_id UUID FK → products NULL,
  reason_code TEXT NOT NULL,   -- e.g. 'NO_CLEARANCE_MATCH', 'NO_WEIGHT_CAPACITY', 'COM_VIOLATION'
  reason_detail TEXT,
  status exception_status NOT NULL DEFAULT 'open',
  resolved_by UUID FK → users NULL,
  resolved_at TIMESTAMPTZ NULL,
  created_at
)

-- threshold_settings (versioned; see PRD §5.8)
threshold_settings (
  id UUID PK,
  version INT NOT NULL,
  heavy_weight_kg NUMERIC NOT NULL DEFAULT 600,
  medium_weight_kg NUMERIC NOT NULL DEFAULT 300,
  com_threshold NUMERIC NOT NULL DEFAULT 0.55,
  blf_com_threshold NUMERIC NOT NULL DEFAULT 0.60,
  aisle_a_density_cap NUMERIC NOT NULL DEFAULT 0.35,
  ergonomic_factors JSONB NOT NULL DEFAULT '{"L1":0.90,"L2":1.00,"L3":0.70,"L4":0.50}',
  pick_lookback_days INT NOT NULL DEFAULT 90,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_by UUID FK → users,
  created_at
)

-- layout_imports
layout_imports (
  id UUID PK,
  uploaded_by UUID FK → users,
  file_path TEXT NOT NULL,      -- local volume path (dev) / object storage key (prod)
  status import_status NOT NULL DEFAULT 'validating',
  validation_errors JSONB,
  created_at
)

-- schedules (recurring runs, PRD §5.4)
schedules (
  id UUID PK,
  goal optimization_goal NOT NULL,
  algorithm TEXT NOT NULL,
  scope run_scope NOT NULL,
  cron_expression TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_by UUID FK → users,
  created_at
)
```

**Indexes worth calling out at build time:** `slots(rack_id, status)` (fast lookup of open slots during algorithm runs), `pick_events(product_id, occurred_at)` and `order_lines(order_id)` (both hit hard by the frequency and affinity algorithms), `slot_assignments(run_id)`.

---

## 5. API Specification

Base path: `/api/v1`. All endpoints except `/auth/login` require a valid JWT; role required is noted per endpoint. Request/response bodies are illustrative field lists, not exhaustive schemas — full Pydantic schemas live in `backend/app/schemas/`.

### 5.1 Auth
| Method & Path | Role | Notes |
|---|---|---|
| `POST /auth/login` | — | `{email, password}` → `{access_token, refresh_token, user}` |
| `POST /auth/refresh` | any | `{refresh_token}` → new `access_token` |
| `GET /auth/me` | any | current user + role |

### 5.2 Users
| Method & Path | Role |
|---|---|
| `GET /users` | admin |
| `POST /users` | admin |
| `PATCH /users/{id}` | admin |
| `DELETE /users/{id}` | admin |

### 5.3 Warehouse Layout
| Method & Path | Role | Notes |
|---|---|---|
| `POST /layout/import` | admin | multipart file upload (JSON or CSV, PRD §5.1) → `{import_id, status: 'validating'}` |
| `GET /layout/imports/{id}` | admin | validation result: `valid` / `invalid` + `validation_errors[]` |
| `POST /layout/imports/{id}/apply` | admin | commits a `valid` import; upserts racks/aisles/slots, preserving assignments where slot IDs match |
| `GET /layout` | any | full current warehouse structure (racks, aisles, slots) — this is what seeds the 3D scene (§9) |

### 5.4 Products (mock catalog in v1)
| Method & Path | Role |
|---|---|
| `GET /products` | any |
| `GET /products/{sku}` | any |
| `POST /products/seed` | admin (dev-only; loads the mock dataset) |

### 5.5 Optimization Runs
| Method & Path | Role | Notes |
|---|---|---|
| `POST /runs` | manager, admin | `{goal, algorithm, scope}` → `{run_id, status: 'queued'}`; enqueues an arq job (§8), never runs inline |
| `GET /runs` | any | list/history, filterable by goal/status |
| `GET /runs/{id}` | any | status + `summary_metrics` once complete |
| `GET /runs/{id}/assignments` | any | full `slot_assignments` result set for that run — this is what the 3D view renders |
| `POST /runs/{id}/rollback` | manager, admin | reverts slot `status`/`current_pallet_id` to the prior run's state |

### 5.6 Assignments (manual override)
| Method & Path | Role | Notes |
|---|---|---|
| `PATCH /assignments/{id}` | manager, admin | `{slot_id}` — re-validates against active `threshold_settings` before accepting; `409` with `reason_code` if unsafe (PRD §5.6) |

### 5.7 Exceptions
| Method & Path | Role |
|---|---|
| `GET /runs/{id}/exceptions` | any |
| `PATCH /exceptions/{id}` | manager, admin — mark resolved, optionally with a manual assignment |

### 5.8 Admin Settings
| Method & Path | Role | Notes |
|---|---|---|
| `GET /settings/thresholds` | any | currently active version |
| `PUT /settings/thresholds` | admin | creates a **new version**, does not mutate the old one (PRD §5.8 — past runs stay auditable against the thresholds active at the time) |

### 5.9 Schedules
| Method & Path | Role |
|---|---|
| `GET /schedules` | admin |
| `POST /schedules` | admin |
| `DELETE /schedules/{id}` | admin |

### 5.10 Reporting
| Method & Path | Role |
|---|---|
| `GET /runs/{id}/export.csv` | any |
| `GET /runs/{id}/report` | any — summary used by the report view in PRD §5.9 |

---

## 6. RBAC Matrix (summary)

| Capability | Admin | Manager | Staff |
|---|---|---|---|
| View 3D twin, search SKUs | ✓ | ✓ | ✓ |
| Trigger a run | ✓ | ✓ | ✗ |
| Override a slot assignment | ✓ | ✓ | ✗ |
| Resolve exceptions | ✓ | ✓ | ✗ |
| Import/apply warehouse layout | ✓ | ✗ | ✗ |
| Edit threshold settings | ✓ | ✗ | ✗ |
| Manage users | ✓ | ✗ | ✗ |
| Manage schedules | ✓ | ✗ | ✗ |

Enforced server-side via a FastAPI dependency (`require_role(*roles)`) on each router — never trust client-side role checks alone.

---

## 7. Algorithm Module Interfaces

Every algorithm module is a pure function: no DB session, no HTTP context, no side effects. The calling service (`app/services/optimization_service.py`) is responsible for loading data in, and persisting the `AssignmentResult` out. This makes each module directly unit-testable against the pseudocode in the algorithm report.

```python
# Shared result contract
class SlotAssignmentResult(TypedDict):
    assignments: list[Assignment]      # (pallet_or_product_id, slot_id, score)
    exceptions: list[Exception_]       # (pallet_or_product_id, reason_code, detail)

# Item -> Pallet layer (Space Efficiency, user picks one of these two)
def ffdh_com.build_pallets(items: list[Item], pallet_dims: Dims, thresholds: Thresholds) -> list[Pallet]: ...
def blf_stratified.build_pallets(items: list[Item], pallet_dims: Dims, thresholds: Thresholds) -> list[Pallet]: ...

# Pallet -> Slot layer (Space Efficiency, always runs regardless of which builder ran)
def wbfdh.assign(pallets: list[Pallet], slots: list[Slot], thresholds: Thresholds) -> SlotAssignmentResult: ...

# SKU -> Slot layer (Picking Efficiency, user picks exactly one)
def golden_zone.assign(skus: list[SKU], slots: list[Slot], pick_history: PickHistory, thresholds: Thresholds) -> SlotAssignmentResult: ...
def affinity_clustering.assign(skus: list[SKU], slots: list[Slot], order_lines: OrderLines, thresholds: Thresholds) -> SlotAssignmentResult: ...
def s_shape_routing.assign(skus: list[SKU], rack_grid: RackGrid, thresholds: Thresholds) -> SlotAssignmentResult: ...
```

Orchestration in `optimization_service.py` for a Space Efficiency run:
```python
pallets = (ffdh_com.build_pallets if algorithm == "ffdh_com" else blf_stratified.build_pallets)(items, pallet_dims, thresholds)
result = wbfdh.assign(pallets, open_slots, thresholds)
```

`thresholds` is always the currently-active `threshold_settings` row (§4), passed explicitly rather than read from global config — this is what makes `thresholds_snapshot` on `optimization_runs` accurate and each run's safety behavior reproducible.

---

## 8. Background Job Architecture (arq)

| Task | Trigger | Behavior |
|---|---|---|
| `run_optimization(run_id)` | enqueued by `POST /runs` | loads run config + input data, calls the algorithm module(s) per §7, writes `slot_assignments` + `exceptions`, updates `optimization_runs.status` |
| `scheduled_run_dispatch` | arq's own cron scheduling, driven by `schedules` table | creates a new `optimization_runs` row (`triggered_by = NULL`) then enqueues `run_optimization` |

**Job lifecycle:** `queued` → `running` → `completed` \| `completed_with_exceptions` \| `failed`.
**Retry policy:** one automatic retry on unhandled exception; on second failure, status becomes `failed` and it surfaces in the run list with the error — never silently dropped.
**Idempotency:** each job is keyed by `run_id`; re-enqueuing an already-running or completed run is a no-op guarded at the service layer.

---

## 9. 3D Visualization Data Contract

The frontend never computes layout geometry itself — it renders exactly what `GET /layout` and `GET /runs/{id}/assignments` return.

- **Coordinate system:** right-handed, Y-up (Three.js default). Units: meters.
- **Origin:** the warehouse's dock/entry point, `(0, 0, 0)`.

```json
// GET /layout
{
  "warehouse": { "id": "...", "name": "..." },
  "aisles": [{ "id": "...", "code": "A1", "orientation": "horizontal", "direction": null }],
  "racks": [{ "id": "...", "aisle_id": "...", "code": "R1", "position": {"x":0,"y":0,"z":0}, "level_count": 4 }],
  "slots": [{ "id": "...", "rack_id": "...", "level": 1, "position": {"x":0,"y":0,"z":0},
              "clearance_height": 1.2, "weight_capacity": 800, "is_aisle_boundary": false, "status": "empty" }]
}
```

```json
// GET /runs/{id}/assignments
{
  "run_id": "...",
  "assignments": [
    { "slot_id": "...", "pallet_id": "...", "product_skus": ["SKU-001"], "score": 0.87, "is_override": false }
  ],
  "exceptions": [
    { "product_sku": "SKU-042", "reason_code": "NO_CLEARANCE_MATCH", "reason_detail": "..." }
  ]
}
```

**Performance note:** at the 5,000-SKU / medium-scale end (PRD §6), rendering every slot as an individual mesh will strain frame rate. Use `InstancedMesh` for repeated rack/slot geometry rather than one mesh per slot — this is a rendering decision, not a data contract change, so it doesn't affect the API shape above.

---

## 10. Local Development Environment

`docker-compose.yml` services:

| Service | Image/build | Port | Notes |
|---|---|---|---|
| `api` | build: `backend/` | 8000 | FastAPI + Uvicorn, hot reload in dev |
| `worker` | build: `backend/` (same image, different entrypoint) | — | runs `arq app.workers.WorkerSettings` |
| `db` | `postgres:16` | 5432 | volume-mounted for persistence across restarts |
| `redis` | `redis:7` | 6379 | broker for arq |
| `web` | build: `frontend/` | 5173 | Vite dev server |

`.env.example` (key variables):
```
DATABASE_URL=postgresql+asyncpg://warehaven:warehaven@db:5432/warehaven
REDIS_URL=redis://redis:6379/0
JWT_SECRET=change-me
JWT_ACCESS_TTL_MIN=30
JWT_REFRESH_TTL_DAYS=7
LAYOUT_STORAGE_PATH=/data/layout-imports   # local volume; becomes an S3 bucket key prefix in the production phase
```

`docker compose up` should bring up the full stack with no external accounts, secrets, or cloud services required — this is the baseline "clone and run" experience for the current phase.

---

## 11. Non-Functional Requirements — Technical Detail

| Area | Requirement |
|---|---|
| API latency | Non-run endpoints: p95 < 300ms locally. Run-triggering endpoint (`POST /runs`) must return immediately (job enqueue only, no algorithm execution inline). |
| Algorithm performance | Target SLA for a full run at 5,000 SKUs is **TBD** — profile first, especially the O(k×n²) Apriori Affinity Clustering path (PRD §12, open question). |
| Determinism | Same input + same `thresholds_snapshot` → identical output, byte-for-byte on the `slot_assignments` rows produced. |
| Error handling | All API errors return a structured `{error_code, message, detail?}` body — no bare 500s with stack traces leaking to the client. |
| Logging | Structured JSON logs (`structlog`), one line per request with `request_id`, `user_id`, `role`, `path`, `status`, `duration_ms`; algorithm runs log `run_id` on every line for traceability. |
| Test coverage | Algorithm modules (§7): unit tests directly against the pseudocode's stated behavior, including safety-constraint edge cases (e.g., a pallet that violates CoM must be rejected, not silently placed). API layer: integration tests per router. |

---

## 12. Layout Import Validation Rules

Applies to both JSON and CSV formats accepted by `POST /layout/import` (PRD §5.1):

- Every `slot` must reference an existing `rack` id in the same import.
- No two slots on the same rack may share a `level`.
- `clearance_height > 0` and `weight_capacity > 0` for every slot — zero or negative values are hard validation errors, not warnings.
- No two racks may have overlapping `(pos_x, pos_y, pos_z)` footprints (exact overlap check; full 3D collision detection is out of scope for v1 — flagged as a known limitation, not a blocker).
- On re-import, a slot is matched to its existing row by `id` (if present in the file) to preserve current assignments; slots without a matching `id` are treated as new.
- Validation errors are returned as a list of `{row_or_slot_ref, field, message}` objects — not a single pass/fail flag — so the Admin can fix everything in one pass instead of one error at a time.

---

## 13. Mock Data Generation Strategy

The tables in §4 (`pick_events`, `order_lines`) exist to feed the Picking Efficiency algorithms, but populating them with uniformly random data would give those algorithms nothing real to work with — frequency-based and affinity-based slotting only look meaningfully different from random placement if the underlying data actually has skew and structure. This section specifies what the generator has to deliberately engineer, per algorithm consumer.

### 13.1 Pick frequency (`pick_events`) — feeds Golden Zone Frequency Slotting, S-Shape Routing
- Assign each mock SKU an `abc_class` using a **Pareto-style split**, not a uniform one — e.g. ~20% of SKUs designated `A` and weighted to receive ~70–80% of total pick volume, `B` a smaller mid-tier share, `C` the long tail. This is what makes `abc_class` (already a `products` column, §4) and the frequency ranking in Golden Zone Slotting actually mean something.
- Generate `pick_events` rows per SKU at a rate proportional to its class, with `occurred_at` timestamps spread across a window **longer than** `pick_lookback_days` (default 90, §4 `threshold_settings`) — this is necessary to actually exercise the rolling-window logic (events outside the window should be excluded, and that's only testable if some exist).
- Optional but valuable: bias a handful of SKUs to have *most* of their pick volume concentrated in a recent sub-window (a step-change in frequency), to exercise the "lag" disadvantage the algorithm report calls out for Golden Zone Slotting — a newly popular SKU sitting in a suboptimal slot until the next scheduled re-run.

### 13.2 Order co-occurrence (`order_lines`) — feeds Apriori Affinity Clustering
- Generate synthetic multi-line orders (1–5 line items each), but **deliberately seed a set of affinity groups** — e.g. 8–15 groups of 2–4 SKUs that co-occur in the same order at a rate well above what random assortment would produce (the report's own example: "ordered together 80% of the time"). Without this, the co-occurrence matrix the algorithm builds is just noise, and clustering has nothing real to find.
- Mix seeded-affinity orders with genuinely random baseline orders (most orders should **not** follow a seeded pattern) — this keeps the dataset realistic and gives a meaningful before/after comparison for the Success Metrics in PRD §9, rather than an artificially perfect clustering result.
- Optional: bias one or two affinity groups to be **seasonal** (concentrated in one part of the timestamp range, absent elsewhere), to exercise the algorithm report's documented weakness — that a Q4-only pairing can look irrelevant if the clustering window includes Q1.

### 13.3 Reproducibility
- The generator takes a fixed random seed by default, so the same mock dataset (and therefore the same algorithm results) can be regenerated on demand — this matters for demoing, for writing algorithm unit tests against known expected output, and for the audit/determinism requirement already stated in §11.
- Generation parameters (SKU count, Pareto skew ratio, number of affinity groups, seasonal bias on/off) should be config values, not hardcoded, so the dataset can be scaled up toward the 5,000-SKU end of PRD §6's range to test performance without rewriting the generator.

---

## 14. Security Considerations

- Passwords hashed with `bcrypt` via `passlib`; never logged, never returned in any API response.
- JWT access tokens short-lived (30 min default); refresh tokens longer-lived (7 days default) and revocable by clearing them server-side on logout.
- Every mutating endpoint validated through Pydantic schemas — no raw dict access to request bodies.
- SQL access exclusively through SQLAlchemy's parameterized queries — no raw string-interpolated SQL anywhere in the codebase.
- CORS restricted to the known frontend origin(s); wide open only in local dev, tightened before the production phase (PRD §8.6).
- Login endpoint rate-limited (basic fixed-window limiter is sufficient for this scale) to blunt credential-stuffing attempts even in a low-traffic deployment.

---

## 15. Open Technical Questions

1. Full JSON Schema (or CSV column spec) for layout import — §12 states the *rules*, but the literal schema file should be written and checked into the repo before import UI work starts.
2. Exact retry/backoff parameters for arq jobs (§8) — one retry is assumed; confirm before Phase 1 sign-off.
3. Unit system for product/pallet/rack dimensions — this doc assumes **meters/kilograms** throughout for consistency with the 3D scene (§9); confirm this matches how the mock dataset (and eventually Odoo) will report dimensions, since `product.template` in Odoo is often in different units by installation.
4. Whether `GET /layout` and `GET /runs/{id}/assignments` should be combined into one endpoint for the frontend's initial load, to avoid a request waterfall on first paint of the 3D scene.
5. Confirm arq's cron scheduling is sufficient for §5.4's "nightly/weekly" scheduled runs, or whether a more explicit schedule table + dispatcher (as sketched in §8) is preferred regardless — current spec already assumes the latter.
6. Exact mock-data generation parameters (§13) — Pareto skew ratio, number/strength of seeded affinity groups, whether seasonal bias is included in v1 — need concrete values before the generator is built, since these directly determine what the Success Metrics comparison in PRD §9 will actually show.
