import { useEffect, useState, useMemo } from 'react';
import { Warehouse, Activity, AlertTriangle, Wifi, WifiOff, Radio } from 'lucide-react';
import useWarehouseStore from './store/useWarehouseStore';
import { generateInitialState, startAutoSimulation, stopAutoSimulation, isSimulationRunning } from './simulator/mockDataGenerator';

/**
 * App — Main Application Shell
 * 
 * Phase B1: Sets up the layout, header with connection status,
 * and initializes the mock data generator.
 * Phase B2 will add the 3D canvas here.
 */

function ConnectionStatusBadge({ status }) {
  const labels = {
    connected: 'LIVE',
    connecting: 'CONNECTING',
    disconnected: 'OFFLINE',
  };

  return (
    <div className={`connection-status connection-status--${status}`}>
      <span className="connection-status__dot" />
      <span>{labels[status] || 'UNKNOWN'}</span>
    </div>
  );
}

function StatsBar() {
  const bins = useWarehouseStore((s) => s.bins);
  const errors = useWarehouseStore((s) => s.errors);
  const pathLength = useWarehouseStore((s) => s.paths.length);
  const binCount = Object.keys(bins).length;
  const errorCount = errors.filter((e) => !e.dismissedAt).length;

  return (
    <div className="stats-bar">
      <div className="stat-item">
        <span className="stat-item__label">Bins</span>
        <span className="stat-item__value">{binCount}</span>
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
  const errors = useMemo(
    () => allErrors.filter((e) => !e.dismissedAt).slice(0, 3),
    [allErrors]
  );

  if (errors.length === 0) return null;

  return (
    <div className="error-toast-container">
      {errors.map((error) => (
        <div key={error.id} className="error-toast">
          <AlertTriangle size={16} />
          <span>{error.message}</span>
          <span
            className="error-toast__dismiss"
            onClick={() => dismissError(error.id)}
          >
            ✕
          </span>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const connectionStatus = useWarehouseStore((s) => s.connectionStatus);
  const [simulating, setSimulating] = useState(false);

  // For Module B1: use mock data. In B2+ this will be replaced with real WebSocket.
  const handleToggleSimulation = () => {
    if (isSimulationRunning()) {
      stopAutoSimulation();
      setSimulating(false);
    } else {
      startAutoSimulation(2000);
      setSimulating(true);
    }
  };

  const handleSeedWarehouse = () => {
    const state = generateInitialState();
    useWarehouseStore.getState().fullResync(state);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => stopAutoSimulation();
  }, []);

  return (
    <div className="app-layout">
      {/* ── Header ──────────────────────────────────── */}
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
          <button className="btn btn--ghost btn--sm" onClick={handleSeedWarehouse}>
            <Activity size={14} />
            Seed Data
          </button>
          <button
            className={`btn ${simulating ? 'btn--primary' : 'btn--ghost'} btn--sm`}
            onClick={handleToggleSimulation}
          >
            <Radio size={14} />
            {simulating ? 'Stop Sim' : 'Start Sim'}
          </button>

          {/* Show mock mode indicator since we're not using real WS yet */}
          <ConnectionStatusBadge
            status={simulating ? 'connected' : connectionStatus}
          />
        </div>
      </header>

      {/* ── Main Content ────────────────────────────── */}
      <main className="app-main">
        <div className="canvas-container">
          {/* Module B2 will insert the <Canvas> here */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            flexDirection: 'column',
            gap: '1rem',
            background: 'var(--gradient-glow)',
          }}>
            <Warehouse size={64} color="var(--accent-blue)" style={{ opacity: 0.4 }} />
            <p style={{
              color: 'var(--text-muted)',
              fontSize: 'var(--text-lg)',
              fontWeight: 500,
            }}>
              3D Canvas — Module B2
            </p>
            <p style={{
              color: 'var(--text-muted)',
              fontSize: 'var(--text-sm)',
              maxWidth: '400px',
              textAlign: 'center',
              lineHeight: 1.6,
            }}>
              State management and WebSocket foundation are ready.
              Click <strong>"Seed Data"</strong> to populate the store, then <strong>"Start Sim"</strong> to see live state updates in the console.
            </p>
          </div>
        </div>

        {/* Error Toasts */}
        <ErrorToasts />
      </main>
    </div>
  );
}
