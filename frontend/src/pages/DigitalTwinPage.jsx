/**
 * Digital Twin 3D Viewer Page
 * Phase 6 — full 3D scene, overlays, search, before/after.
 * Placeholder renders a clear "coming in Phase 6" state.
 */
export default function DigitalTwinPage() {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="page-header" style={{ flexShrink: 0 }}>
        <div>
          <h2>3D Digital Twin</h2>
          <p>Interactive warehouse visualization — implemented in Phase 6</p>
        </div>
      </div>
      <div style={{
        flex: 1,
        background: 'var(--color-surface)',
        borderRadius: 12,
        border: '1px solid var(--color-border-subtle)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: 16, color: 'var(--color-text-muted)',
      }}>
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.3">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
          <line x1="12" y1="22.08" x2="12" y2="12"/>
        </svg>
        <span style={{ fontSize: 15 }}>3D scene — Phase 6</span>
        <span style={{ fontSize: 13, maxWidth: 320, textAlign: 'center' }}>
          react-three-fiber scene with racks, slots, heatmap overlays, SKU search, and drag-and-drop override
        </span>
      </div>
    </div>
  );
}
