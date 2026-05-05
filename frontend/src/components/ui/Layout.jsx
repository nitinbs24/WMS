import { useState } from 'react';
import {
  Warehouse,
  Activity,
  AlertTriangle,
  Radio,
  Eye,
  EyeOff,
  Camera,
} from 'lucide-react';
import useWarehouseStore from '../../store/useWarehouseStore';
import {
  generateInitialState,
  startAutoSimulation,
  stopAutoSimulation,
  isSimulationRunning,
} from '../../simulator/mockDataGenerator';

/**
 * Layout — Main Dashboard Wrapper
 *
 * Provides:
 *  - Header bar with branding, live stats, and controls
 *  - Camera mode toggle (perspective ↔ top-down)
 *  - Heatmap mode toggle (occupancy ↔ velocity)
 *  - Simulation controls (Seed Data, Start/Stop Sim)
 *  - Error toast notifications
 *  - Slot for the 3D canvas children
 *
 * Props:
 *  - children        — the Scene canvas
 *  - cameraMode      — 'perspective' | 'top'
 *  - onCameraToggle  — called to toggle camera mode
 */

// ── Sub-components ─────────────────────────────────────────────

function ConnectionStatusBadge({ status }) {
  const labels = { connected: 'LIVE', connecting: 'CONNECTING', disconnected: 'OFFLINE' };
  return (
    <div className={`connection-status connection-status--${status}`}>
      <span className="connection-status__dot" />
      <span>{labels[status] ?? 'UNKNOWN'}</span>
    </div>
  );
}

function StatsBar() {
  const bins = useWarehouseStore((s) => s.bins);
  const errors = useWarehouseStore((s) => s.errors);
  const pathLength = useWarehouseStore((s) => s.paths.length);
  const binCount = Object.keys(bins).length;
  const errorCount = errors.filter((e) => !e.dismissedAt).length;

  // Compute average occupancy
  const binValues = Object.values(bins);
  const avgOccupancy =
    binValues.length > 0
      ? Math.round(binValues.reduce((acc, b) => acc + (b.occupancy_pct ?? 0), 0) / binValues.length)
      : 0;

  return (
    <div className="stats-bar">
      <div className="stat-item">
        <span className="stat-item__label">Bins</span>
        <span className="stat-item__value">{binCount}</span>
      </div>
      <div className="stat-item">
        <span className="stat-item__label">Avg Occupancy</span>
        <span
          className="stat-item__value"
          style={{ color: avgOccupancy > 80 ? 'var(--accent-red)' : avgOccupancy > 60 ? 'var(--accent-amber)' : 'var(--accent-green)' }}
        >
          {avgOccupancy}%
        </span>
      </div>
      <div className="stat-item">
        <span className="stat-item__label">Path Nodes</span>
        <span className="stat-item__value">{pathLength}</span>
      </div>
      {errorCount > 0 && (
        <div className="stat-item">
          <AlertTriangle size={14} color="var(--accent-red)" />
          <span className="stat-item__value" style={{ color: 'var(--accent-red)' }}>
            {errorCount}
          </span>
        </div>
      )}
    </div>
  );
}

function ErrorToasts() {
  const allErrors = useWarehouseStore((s) => s.errors);
  const dismissError = useWarehouseStore((s) => s.dismissError);
  const errors = allErrors.filter((e) => !e.dismissedAt).slice(0, 3);

  if (errors.length === 0) return null;

  return (
    <div className="error-toast-container">
      {errors.map((error) => (
        <div key={error.id} className="error-toast">
          <AlertTriangle size={16} />
          <span>{error.message}</span>
          <span className="error-toast__dismiss" onClick={() => dismissError(error.id)}>✕</span>
        </div>
      ))}
    </div>
  );
}

// ── Main Layout ────────────────────────────────────────────────

export default function Layout({ children, cameraMode, onCameraToggle }) {
  const [simulating, setSimulating] = useState(false);
  const connectionStatus = useWarehouseStore((s) => s.connectionStatus);
  const heatmapMode = useWarehouseStore((s) => s.heatmapMode);
  const setHeatmapMode = useWarehouseStore((s) => s.setHeatmapMode);

  const handleToggleSimulation = () => {
    if (isSimulationRunning()) {
      stopAutoSimulation();
      setSimulating(false);
    } else {
      startAutoSimulation(1500);
      setSimulating(true);
    }
  };

  const handleSeedWarehouse = () => {
    const state = generateInitialState();
    useWarehouseStore.getState().fullResync(state);
  };

  return (
    <div className="app-layout">
      {/* ── Header ──────────────────────────────────────── */}
      <header className="app-header">
        <div className="app-header__brand">
          <div className="app-header__logo">
            <Warehouse size={20} />
          </div>
          <div>
            <div className="app-header__title">Warehouse Digital Twin</div>
            <div className="app-header__subtitle">Real-time 3D Visualization</div>
          </div>
        </div>

        <StatsBar />

        <div className="app-header__actions">
          {/* Heatmap toggle */}
          <button
            className="btn btn--ghost btn--sm"
            onClick={() => setHeatmapMode(heatmapMode === 'occupancy' ? 'velocity' : 'occupancy')}
            title="Toggle heatmap mode"
          >
            {heatmapMode === 'occupancy' ? <Eye size={14} /> : <EyeOff size={14} />}
            {heatmapMode === 'occupancy' ? 'Occupancy' : 'Velocity'}
          </button>

          {/* Camera toggle */}
          <button
            className="btn btn--ghost btn--sm"
            onClick={onCameraToggle}
            title="Toggle camera view"
          >
            <Camera size={14} />
            {cameraMode === 'top' ? '3D View' : 'Top View'}
          </button>

          {/* Seed data */}
          <button className="btn btn--ghost btn--sm" onClick={handleSeedWarehouse}>
            <Activity size={14} />
            Seed Data
          </button>

          {/* Simulation toggle */}
          <button
            className={`btn ${simulating ? 'btn--primary' : 'btn--ghost'} btn--sm`}
            onClick={handleToggleSimulation}
          >
            <Radio size={14} />
            {simulating ? 'Stop Sim' : 'Start Sim'}
          </button>

          <ConnectionStatusBadge status={simulating ? 'connected' : connectionStatus} />
        </div>
      </header>

      {/* ── Main Canvas Area ────────────────────────────── */}
      <main className="app-main">
        {children}
        <ErrorToasts />
      </main>
    </div>
  );
}
