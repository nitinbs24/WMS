# Warehouse Digital Twin

A real-time 3D warehouse digital twin that captures live inventory events from Odoo ERP, streams them via an Apache Kafka pipeline, processes them through a spatial validation and optimization engine, and renders an interactive WebGL 3D scene in the browser at 60 FPS.

This project implements an **Agentic Supply Chain Digital Twin**, integrating Industry 5.0 enhancements like Explainable AI (XAI) overlays, ergonomic slotting optimization, and natural language AI operational intelligence.

## System Architecture

The system is fully event-driven and decoupled into 6 sequential phases:

1. **Source Data Generation**: Odoo ERP and PostgreSQL WAL record physical warehouse events (e.g., goods receipt, picks).
2. **Event Streaming**: Debezium CDC captures database changes and streams them to Apache Kafka.
3. **Middleware Ingestion**: A FastAPI backend consumes Kafka events and translates them into validated 3D geometry using PostGIS.
4. **Algorithmic Optimization**: Custom FFD (bin packing), Google OR-Tools (TSP routing), and A* pathfinding optimize storage and picking.
5. **Real-Time Transmission**: Processed data is pushed to the frontend via WebSockets with sub-second latency.
6. **Frontend Rendering**: React Three Fiber and Zustand translate the data into a high-performance, interactive 3D WebGL environment.

---

## Folder Structure

The repository is organized to support independent parallel development by a two-person team.

```text
warehouse-digital-twin/
│
├── infrastructure/                 # Shared Docker/DevOps Environment
│   ├── docker-compose.yml          # Spinups for Odoo, Postgres+PostGIS, Kafka, Debezium, Schema Registry
│   ├── debezium/                   # Configuration payloads to attach Debezium to Postgres WAL
│   └── postgres/                   # Initialization scripts for PostGIS extensions
│
├── backend/                        # Person A Domain: Data Pipeline & Algorithms
│   ├── alembic/                    # Database migrations tracking PostGIS schema versions
│   ├── app/                        # Main FastAPI application
│   │   ├── algorithms/             # FFD bin packing, A* pathfinding, TSP routing, SKU affinity
│   │   ├── api/                    # WebSocket handlers and REST endpoints (/simulate)
│   │   ├── core/                   # Environment config and Kafka client setup
│   │   ├── db/                     # SQLAlchemy ORM models mapping to PostGIS geometries
│   │   ├── schemas/                # Pydantic models enforcing the JSON payload contract
│   │   └── services/               # ETL logic and PostGIS spatial validation (ST_3DIntersects)
│   ├── scripts/                    # Scripts to seed initial warehouse state from Odoo to PostGIS
│   └── tests/                      # Pytest unit tests for algorithms and spatial logic
│
└── frontend/                       # Person B Domain: 3D Rendering & UI
    ├── src/                        
    │   ├── components/             
    │   │   ├── 3d/                 # React Three Fiber (WebGL) elements: Canvas, InstancedBins, Paths
    │   │   └── ui/                 # React DOM HTML overlays: Dashboard, Tooltips, AI Panel
    │   ├── hooks/                  # Custom hooks (e.g., useWebSocket with exponential backoff)
    │   ├── services/               # API clients for REST endpoints and LLM integrations
    │   ├── simulator/              # Mock Data Generator for independent UI development
    │   ├── store/                  # Zustand global state (bins, paths, occupancies, scores)
    │   └── utils/                  # Helper functions (e.g., occupancy heatmap color mapping)
    ├── index.html                  # Main HTML entry point
    └── package.json                # Frontend dependencies (three, @react-three/fiber, zustand)
```

## Getting Started

### Backend & Infrastructure (Person A)
1. Navigate to `infrastructure/` and run `docker-compose up -d` to start the Kafka and database stack.
2. Navigate to `backend/`, install Python requirements, run Alembic migrations, and start the FastAPI server.

### Frontend (Person B)
1. Navigate to `frontend/`.
2. Run `npm install` to install React and Three.js dependencies.
3. Run `npm run dev` to start the Vite development server.
4. The frontend initially uses the `mockDataGenerator` to simulate a live connection, allowing UI development without the backend running.

## The Handoff Contract
To allow complete developmental independence, the backend and frontend are decoupled by a strict **WebSocket JSON Payload Schema**. 
- **Person A** guarantees the backend produces this exact JSON.
- **Person B** uses the `mockDataGenerator` to simulate this JSON during development, allowing the 3D scene to be built independently. 
- Integration simply involves pointing the frontend WebSocket client to the live FastAPI URL.
