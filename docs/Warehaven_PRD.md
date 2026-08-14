# Product Requirements Document: Warehaven
### AI-Assisted 3D Warehouse Digital Twin & Slotting Optimization System

**Status:** Draft v1.0
**Date:** August 14, 2026
**Author:** [Your name / team]
**Related docs:** Warehouse Optimization — Algorithm Implementation Report (V.V.C.E Mysore, July 2026)
**Deployment scope:** The system described here is built and run **locally** for now (local Docker Compose, no cloud hosting). Production deployment (§8.5) is a separate, later phase gated behind additional requirements to be defined — see §10.

---

## 1. Overview

Warehaven is a warehouse management add-on that ingests product and order data from an Odoo ERP instance, runs one of several slotting algorithms to decide where inventory should physically sit on the racks, and renders the result as an interactive 3D digital twin so a warehouse manager can see — and adjust — the entire facility at a glance.

The system optimizes for one of two goals, selected by the manager per run:

1. **Space Efficiency** — maximize cubic fill rate of every occupied rack slot.
2. **Picking Efficiency** — minimize forklift travel time and picker effort.

Six candidate algorithms (three per goal) were selected and documented in the accompanying literature review. This PRD defines how those algorithms are exposed to the user, what the surrounding product looks like, and what's in scope for v1.

---

## 2. Problem Statement

Warehouses that assign storage locations manually or by static rule-of-thumb (e.g., "always put it wherever there's space") tend to accumulate two costs over time: wasted cubic volume (space inefficiency) and excess forklift travel per pick (time/labor inefficiency). Both costs compound as SKU count and order volume grow. Existing ERP systems like Odoo hold the data needed to fix this — product dimensions, weights, and order/pick history — but don't do anything with it spatially, and give the manager no way to *see* the warehouse as it actually is.

Warehaven closes that gap: it turns Odoo's transactional data into a physical slotting decision, and turns that decision into something a manager can look at and trust.

---

## 3. Goals & Non-Goals

### 3.1 Goals (v1)
- Let a manager choose an optimization objective (space or picking efficiency) and an algorithm within that objective, and run it against the current catalog.
- Produce a safe, explainable slot assignment (every placement traceable to the rule/score that produced it).
- Visualize the resulting warehouse state as an interactive 3D model, rack by rack, slot by slot.
- Allow manual override of any assignment directly in the 3D view.
- Work fully against mock/seed data now, with a clean integration seam for live Odoo data later.

### 3.2 Non-Goals (v1)
- Live, bidirectional sync with a production Odoo instance (Phase 2 — see §12).
- Real-time forklift tracking or IoT sensor integration.
- Automatic multi-warehouse / multi-site optimization (single warehouse only in v1).
- Mobile app for pickers (web only in v1; picklists can be exported/viewed, not executed, on mobile).
- **Cloud production deployment.** The system runs locally for now; cloud hosting (§8.5) is deferred to a later phase gated behind requirements TBD (§10).

---

## 4. Users & Roles

| Role | Description | Key permissions |
|---|---|---|
| **Admin** | Configures the system: warehouse layout import, safety thresholds, user accounts | Full access: import layout, edit thresholds, manage users, run any algorithm |
| **Manager** | Day-to-day operator: runs optimizations, reviews and overrides placements | Select goal/algorithm, trigger runs, view 3D twin, drag-and-drop override, view reports |
| **Staff** | Warehouse floor worker needing to locate items | View-only: 3D twin, slot search, picklists |

Auth is a simple username/password + role model in v1 (no Odoo SSO yet — see Open Questions).

---

## 5. Functional Requirements

### 5.1 Warehouse Layout Configuration
- Admin imports the physical layout via a **JSON or CSV config file** defining:
  - Racks: id, aisle, position (x, y, z), number of levels
  - Slots: per-rack level, clearance height, weight capacity, position
  - Aisles: id, direction/orientation, adjacent racks
- System validates the import (no overlapping coordinates, no orphaned racks) and reports errors before committing.
- Layout can be re-imported/updated; existing slot assignments are preserved where slot IDs match.
- v1 supports **one warehouse** per deployment.

### 5.2 Product Catalog & Order Data Ingestion
- v1 source: **mock/seed dataset** shaped identically to the eventual Odoo payload, so the ingestion layer doesn't need to change when Odoo is connected later. Mock data should include, per SKU: dimensions (l/w/h), weight, category/ABC class, and a synthetic pick-history log (to drive the picking-efficiency algorithms).
- Data model mirrors the Odoo objects referenced in the algorithm report: `product.template` (dimensions, weight, packaging), `stock.move` (pick frequency), `sale.order.line` (order co-occurrence), `stock.quant` (current stock levels).
- A dedicated ingestion/adapter layer isolates this mapping so swapping the mock source for live Odoo JSON-RPC calls later is a backend-only change (see §10, §12).

### 5.3 Optimization Engine

**Design clarification (confirm in review):** the two objectives don't decompose into "3 independent alternatives" identically.

- **Picking Efficiency** — the three algorithms (Ergonomic Golden Zone, Apriori Affinity Clustering, S-Shape Routing) each independently produce a complete SKU→slot assignment. The manager picks exactly **one of the three** to run.
- **Space Efficiency** — the algorithms sit at two different pipeline stages:
  - *Item → pallet* (how items get built into a pallet load): **Modified FFDH+CoM** or **BLF+Weight Stratification** — these two are true alternatives to each other.
  - *Pallet → slot* (where a built pallet goes on the rack): **W-BFDH** — this step always runs, regardless of which pallet-building method was used, since nothing else in the report performs slot assignment for this objective.
  - So for Space Efficiency, the manager's choice is really: **FFDH+CoM vs. BLF+Stratification** for pallet building, with W-BFDH always executing as the placement step. The UI should present this as "choose your pallet-building strategy," not a flat 3-way choice, or the third "algorithm" (W-BFDH) has nothing to be chosen against.

| Goal | Algorithm | Pipeline stage | Selectable? |
|---|---|---|---|
| Space Efficiency | Modified FFDH + CoM Validation | Item → Pallet | Yes (1 of 2) |
| Space Efficiency | BLF + Weight Stratification | Item → Pallet | Yes (1 of 2) |
| Space Efficiency | W-BFDH | Pallet → Slot | Always runs |
| Picking Efficiency | Ergonomic Golden Zone Frequency Slotting | SKU → Slot | Yes (1 of 3) |
| Picking Efficiency | Apriori Affinity Clustering + Congestion Dampening | SKU → Slot | Yes (1 of 3) |
| Picking Efficiency | S-Shape Pick-Path Routing Integrated Slotting | SKU → Slot | Yes (1 of 3) |

- Every hard safety rule from the report is enforced regardless of algorithm choice: weight-class level restrictions, CoM stability threshold, aisle A-class density cap.
- If an item/pallet cannot be placed safely, the run does not silently drop it — it raises an **exception** (see §5.7).

### 5.4 Run Execution & Scheduling
- **Manual trigger**: Manager selects goal + algorithm + scope (full or incremental) and clicks "Run Optimization."
- **Scheduled trigger**: Admin can configure a recurring background run (e.g., nightly for picking-efficiency re-scoring, as the report recommends for frequency-based algorithms) with the same goal/algorithm/scope settings.
- **Scope**:
  - *Full re-slot*: recomputes placement for the entire warehouse.
  - *Incremental*: only places new/changed stock (new receipts, updated dimensions/weights), leaving existing assignments untouched. This matches the "partial re-slotting" behavior the report calls out for W-BFDH.
- Each run produces a versioned result set (see §7 data model) so past runs remain inspectable, and a run can be rolled back.

### 5.5 3D Visualization (Digital Twin)
- Full interactive 3D rendering of the warehouse (React + Three.js): racks, aisles, and individual slots rendered at their configured coordinates.
- Slot-level detail on hover/click: SKU, quantity, weight, fill %, assigning algorithm, last-updated timestamp.
- Color-coded overlays, switchable by the manager:
  - Fill rate / space utilization heat map
  - Pick frequency heat map (for picking-efficiency runs)
  - Weight-class / safety-tier view
  - Aisle direction arrows (for S-Shape routing runs, per the report's requirement)
- Search bar: find a SKU and the camera navigates to / highlights its slot(s).
- Toggle between the "before" and "after" state of a run to visually compare.

### 5.6 Manual Override
- Manager can drag a pallet/SKU from one slot to another directly in the 3D view.
- Overrides are validated against the same hard safety rules (weight-class level, capacity) before being accepted — an unsafe manual drop is rejected with an explanation, not silently allowed.
- Overridden slots are visually flagged (e.g., outline/badge) and excluded from being reassigned by subsequent automatic runs unless the manager explicitly clears the override.
- Every override is logged (who, when, from/to slot) for auditability.

### 5.7 Alerts & Exception Handling
- When an algorithm cannot find a valid slot for a pallet (as the pseudocode's "RAISE alert" paths describe), it's surfaced as an **unplaced-item queue**, not a silent failure.
- Manager/Admin sees a list of unplaced items with the reason (no slot met clearance, no slot met weight capacity, etc.) and can manually assign or adjust constraints.
- Optional: notification (in-app banner at minimum) when a scheduled run completes with exceptions.

### 5.8 Admin Settings
- All report-defined thresholds are editable via an admin settings screen, versioned per change (so past runs can be audited against the thresholds that were active at the time):
  - Weight-class breakpoints (default: heavy >600kg, medium 300–600kg, light ≤300kg)
  - CoM stability threshold (default: 0.55 / 0.60 depending on algorithm)
  - Aisle A-class density cap (default: 0.35)
  - Ergonomic level factors (default: L1 0.90, L2 1.00, L3 0.70, L4 0.50)
  - Pick-history lookback window (default: 90 days)
- Changing a threshold does **not** retroactively alter past run results — it only affects runs going forward.

### 5.9 Reporting / Export
- Export current slot assignment as CSV (for handoff to floor staff or import elsewhere).
- Export a summary report per run: fill rate achieved, estimated travel-time reduction, number of exceptions, thresholds used.

---

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Scale | Designed and tested for 500–5,000 SKUs, multiple aisles, multi-level racks |
| Performance | A full-warehouse run should complete in an acceptable interactive timeframe (target: define exact SLA after profiling — the Apriori Affinity algorithm is O(k×n²) and is the likely bottleneck at the top of the SKU range) |
| Determinism | Given identical input and thresholds, a run must produce identical output (auditability) |
| Auditability | Every slot assignment traceable to: run ID, algorithm, timestamp, and (if overridden) the user who changed it |
| Safety | Hard safety constraints (weight/CoM/congestion) can never be bypassed by algorithm choice or override — only explicitly relaxed by Admin via settings, with the change logged |
| Browser support | Modern evergreen browsers; 3D view requires WebGL support |

---

## 7. Data Model (v1 sketch)

- **Warehouse**: id, name
- **Rack**: id, warehouse_id, aisle_id, position, level_count
- **Aisle**: id, warehouse_id, orientation, direction (for S-Shape routing)
- **Slot**: id, rack_id, level, clearance_height, weight_capacity, position, current_pallet_id, status
- **Product**: id, sku, name, l/w/h, weight, category, abc_class *(mirrors Odoo `product.template`)*
- **Pallet**: id, product_id(s), computed height/weight/volume, stability_status
- **PickEvent**: product_id, timestamp *(mirrors Odoo `stock.move`)*
- **OrderLine**: order_id, product_id *(mirrors Odoo `sale.order.line`, for affinity clustering)*
- **OptimizationRun**: id, goal, algorithm, scope (full/incremental), triggered_by (user_id or "scheduled"), started_at, status, thresholds_snapshot
- **SlotAssignment**: id, run_id, pallet_id, slot_id, score, is_override, overridden_by, overridden_at
- **Exception**: id, run_id, pallet_id, reason, status (open/resolved)
- **User**: id, name, role
- **ThresholdSettings**: versioned key/value config (see §5.8)

---

## 8. Technical Architecture & Stack (Finalized)

Backend framework decision: **FastAPI over Django.** Reasoning: the admin settings screens and all CRUD UI are already being built as custom React views (§5.8), so Django's biggest built-in advantage — the free server-rendered admin panel — isn't needed here. FastAPI's async-native design fits three things this product actually needs: concurrent, non-blocking Odoo JSON-RPC calls in Phase 2; a natural path to WebSocket/streaming updates for long-running optimization jobs; and Pydantic-based validation, which maps directly onto the layout-import validation requirement in §5.1. Django would mean less boilerplate for auth/RBAC out of the box, but that gap is small and well-trodden in FastAPI (see Auth below) — it's not enough to offset the async/validation fit.

### 8.1 Frontend
- **React** (Vite build tooling — fast dev/build, no server-rendering needed for this app)
- **react-three-fiber** + **drei** as the React binding for Three.js, rather than raw imperative Three.js — keeps the 3D scene declarative and maintainable alongside the rest of the React app
- **TanStack Query (React Query)** for server-state (fetching/caching run results, catalog data); lightweight local state (Zustand) only where needed for UI-only state (camera, selected slot, override drafts)
- **Tailwind CSS** + a headless component set (e.g. shadcn/ui) for the non-3D UI chrome — forms, tables, admin settings, run configuration panels

### 8.2 Backend
- **FastAPI** (Python 3.12) — REST endpoints for layout import, catalog ingestion, run triggering/status, overrides, admin settings, reporting
- **Pydantic v2** — request/response validation, and reused directly to validate uploaded layout JSON/CSV files (§5.1) with structured error messages
- **SQLAlchemy 2.0 (async)** + **Alembic** for schema migrations
- **Auth**: JWT-based session (`python-jose` + `passlib` for hashing, or `fastapi-users` to avoid hand-rolling it), with role checked via a FastAPI dependency on every protected route — maps directly onto Admin/Manager/Staff from §4
- **Optimization engine**: standalone, framework-agnostic Python module(s) implementing the six algorithms as pure functions over the data model — deliberately decoupled from the API layer so each algorithm can be unit-tested and benchmarked in isolation (important given the safety constraints in §6) without spinning up the web app

### 8.3 Database & Storage
- **PostgreSQL** — relational, handles the rack/slot/pallet/assignment relationships cleanly, has a `JSONB` column type useful for the `thresholds_snapshot` field on each run (§7), and every low-cost host in §8.5 offers a managed free/cheap tier
- **Object storage** (S3-compatible — e.g. Cloudflare R2 or Supabase Storage, both have free tiers) for uploaded layout config files, rather than local disk, so uploads survive redeploys/restarts on the hosting platforms below

### 8.4 Background Jobs & Scheduling
- **Redis** + **arq** (a lightweight async task queue that pairs naturally with FastAPI, cheaper to run than Celery for this scale) for: executing optimization runs outside the request/response cycle (so a 5,000-SKU run doesn't block or time out an API call), and for the scheduled/recurring runs from §5.4
- Run status is polled by the frontend via a `/runs/{id}/status` endpoint in v1; upgrading this to a WebSocket push (FastAPI supports this natively) is a low-effort future enhancement once there's a concrete need for live progress in the 3D view — not required for v1

### 8.5 Local Development Environment (current phase)
Everything runs on a developer machine with no external cloud dependency:
- **Docker Compose** spins up: the FastAPI app, Postgres, Redis, and the frontend dev server, all networked together with one command.
- **File storage**: layout config uploads (§5.1) write to a local volume/directory in this phase, behind the same storage interface that will later point at S3-compatible object storage — so switching to cloud storage in the production phase is a config change, not a rewrite.
- **Background jobs**: arq worker runs as its own container in the same Compose stack, against the local Redis — same code path as production, just pointed at local infra.
- **Auth/data**: seeded via the mock data layer (§5.2, §8.7); no external accounts or secrets needed to run the full app end-to-end.
- CI (lint + test via GitHub Actions on every PR) is still worth having at this stage, even with no deploy step yet — catches regressions before production infra is ever stood up.

### 8.6 Production Hosting (future phase — not built yet)
This is the target once the gating requirements in §10 are defined and met; it is **not** part of the current build. Given low-cost/free-tier priority and no dedicated DevOps: avoid raw AWS/GCP/Azure — the operational overhead isn't worth it at this scale. Recommended when the time comes:
- **Frontend**: Vercel or Netlify (free tier, ideal for a Vite/React SPA, global CDN, git-push deploys)
- **Backend + worker**: Render or Railway (both offer a free/low-cost web service + background worker + managed Postgres + managed Redis in one place, HTTPS and env-var management included — genuinely production-grade at this scale, just without the AWS complexity)
- **Database**: managed Postgres via the same platform, or Neon/Supabase if a serverless Postgres with a more generous free tier is preferred
- Because everything is already containerized with **Docker** for local dev (§8.5), moving to any of these hosts — or later to AWS/GCP/K8s if usage outgrows this tier — doesn't require re-architecting, just pointing the same containers at managed infra

### 8.7 CI/CD, Testing & Monitoring
- **GitHub Actions**: lint + test on every PR now; a deploy step gets added once §8.6 is actually being stood up
- **Testing**: `pytest` + `pytest-asyncio` for the API and — critically — the optimization algorithms themselves (safety-constraint correctness deserves direct unit tests, not just integration coverage); `Vitest` + React Testing Library on the frontend
- **Error tracking**: Sentry (free tier covers both frontend and backend) — wire up once there's a real deployment to monitor; not essential for local-only dev
- **Logging**: structured JSON logging (`structlog` or stdlib logging with a JSON formatter) from day one — directly supports the auditability requirement in §6 and makes the eventual move to hosted log viewers trivial

### 8.8 Data Source Integration
- **v1**: mock data layer shaped to match Odoo's object structure, loaded from seed files, sitting behind an adapter interface
- **Phase 2**: Odoo JSON-RPC client replacing the mock layer behind that same interface, so nothing else in the app needs to change

---

## 9. Success Metrics

To be treated as the project's evaluation criteria / demo goals:

- **Space efficiency runs**: measurable improvement in average cubic fill rate vs. a naive/random baseline placement, on the same mock catalog.
- **Picking efficiency runs**: measurable reduction in estimated total travel distance per pick wave vs. baseline, computed against the mock pick-history data.
- **Zero unsafe placements**: no run, including manual overrides, ever violates a hard safety constraint.
- **Usability**: a manager can go from "select goal" to "see the result in 3D" in a small number of clicks, with every slot's assignment explainable on click.

*(Exact target numbers, e.g. "+15% fill rate," should be set once the mock dataset and baseline are built — flagged as an open item below.)*

---

## 10. Phased Roadmap

**Phase 1 — Local build (current scope):**
Mock data, layout import, all 6 algorithms, 3D twin, manual override, scheduling, admin settings, reporting — fully functional, running entirely locally via Docker Compose (§8.5). No cloud hosting.

**Phase 2 — Live Odoo integration:**
Odoo JSON-RPC connection to `product.template`, `stock.move`, `sale.order.line`, `stock.quant`, replacing the mock data layer. Can be developed and tested locally against a local/sandbox Odoo instance before any cloud deployment happens.

**Phase 3 — Production deployment (gated):**
Move to the hosting stack in §8.6 (Vercel/Netlify + Render/Railway + managed Postgres/Redis). **Gate condition: to be defined** — held until the additional requirements referenced in this phase are specified and met. Flagged as an open question below.

**Phase 4 (candidate, not committed):**
Multi-warehouse support, Odoo-based SSO/auth, mobile picklist view for Staff, real pipeline mode (running FFDH/BLF → W-BFDH and Golden Zone → Affinity → S-Shape as the layered sequence the report originally recommends, as an optional "advanced mode" alongside the single-algorithm mode in v1).

---

## 11. Assumptions

- The "one warehouse" scope for v1 is acceptable even if the eventual production use case is multi-site.
- A synthetic/mock dataset can be constructed that's representative enough of real Odoo data to meaningfully evaluate algorithm performance and demo the product.
- Render/Railway-class hosting (rather than raw AWS/GCP/Azure) is acceptable for the production deployment at this scale and budget; this can be revisited if usage grows beyond what those platforms comfortably handle.

---

## 12. Open Questions

1. ~~Confirm the Space Efficiency algorithm framing in §5.3~~ — **Resolved**: pallet-building method choice (FFDH+CoM vs. BLF), with W-BFDH always running as the fixed slot-assignment step.
2. ~~Final backend framework~~ — **Resolved**: FastAPI (see §8).
3. What's the target performance SLA for a full run at the 5,000-SKU end of the range (especially for the O(k×n²) Apriori Affinity algorithm)?
4. Should Staff be able to see cost/pricing data in the 3D view, or only physical/location data?
5. Exact baseline definition for the Success Metrics in §9 (random placement? alphabetical? current manual process?).
6. Any specific Odoo version/edition targeted for Phase 2, to confirm JSON-RPC field names match current Odoo schema.
7. Confirm Render vs. Railway (or another low-cost host) once someone's had a chance to compare their current free/low-tier limits and Redis/worker support directly — recommendation in §8.6 is directional, not a final pick.
8. **What exactly gates the move to production (§10, Phase 3)?** Right now this is an unnamed placeholder — worth listing the specific requirements here once known, so Phase 3 has a checkable definition of "ready" rather than an open-ended "later."

---

## 13. Supporting Reference

Full algorithm mechanisms, pseudocode, complexity, and academic citations for all six algorithms are documented in the companion **Warehouse Optimization — Algorithm Implementation Report** (V.V.C.E Mysore, July 2026) and are treated as the technical spec for §5.3's optimization engine.
