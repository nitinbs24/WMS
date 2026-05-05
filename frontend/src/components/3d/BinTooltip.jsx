import { Html } from '@react-three/drei';
import { X, Package, Layers, TrendingUp, MapPin } from 'lucide-react';

/**
 * BinTooltip — 3D-anchored Bin Detail Panel
 *
 * Rendered as an HTML overlay anchored to the clicked bin's 3D position
 * using Drei's <Html> component. The panel is positioned in screen space
 * but follows the 3D object as the camera orbits.
 *
 * Props:
 *  - bin       — the bin data object from the Zustand store
 *  - onClose() — called when the user dismisses the panel
 */

const ZONE_CONFIG = {
  golden: { label: 'Golden Zone', className: 'bin-tooltip__zone--golden' },
  upper:  { label: 'Upper Zone',  className: 'bin-tooltip__zone--upper'  },
  lower:  { label: 'Lower Zone',  className: 'bin-tooltip__zone--lower'  },
  floor:  { label: 'Floor Zone',  className: 'bin-tooltip__zone--floor'  },
};

function OccupancyBar({ pct, color }) {
  return (
    <div style={{ marginTop: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Occupancy</span>
        <span style={{ fontSize: '0.7rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color }}>
          {pct}%
        </span>
      </div>
      <div className="occupancy-bar">
        <div
          className="occupancy-bar__fill"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function BinTooltip({ bin, onClose }) {
  if (!bin) return null;

  const zone = ZONE_CONFIG[bin.ergonomic_zone] ?? ZONE_CONFIG.floor;
  const occupancyColor = bin.color_hex ?? '#22c55e';

  // Anchor the HTML panel slightly above and to the right of the bin
  const anchorPos = [
    bin.position.x + (bin.dimensions?.l ?? 1.2) * 0.6,
    bin.position.y + (bin.dimensions?.h ?? 1.5) * 0.7,
    bin.position.z,
  ];

  return (
    <Html
      position={anchorPos}
      distanceFactor={14}
      zIndexRange={[100, 0]}
      occlude={false}
      style={{ pointerEvents: 'auto' }}
    >
      <div className="bin-tooltip" style={{ animation: 'fade-in 0.2s ease' }}>
        {/* ── Header ────────────────────────────────────── */}
        <div className="bin-tooltip__header">
          <span className="bin-tooltip__id">{bin.bin_id}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className={`bin-tooltip__zone ${zone.className}`}>
              {zone.label}
            </span>
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                padding: '2px',
              }}
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* ── Data Rows ─────────────────────────────────── */}
        <div className="bin-tooltip__row">
          <span className="bin-tooltip__label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Package size={12} /> SKU
          </span>
          <span className="bin-tooltip__value">{bin.sku ?? '—'}</span>
        </div>

        <div className="bin-tooltip__row">
          <span className="bin-tooltip__label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Layers size={12} /> Dimensions
          </span>
          <span className="bin-tooltip__value" style={{ fontSize: '0.75rem' }}>
            {bin.dimensions
              ? `${bin.dimensions.l}×${bin.dimensions.w}×${bin.dimensions.h}m`
              : '—'}
          </span>
        </div>

        <div className="bin-tooltip__row">
          <span className="bin-tooltip__label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <TrendingUp size={12} /> Slot Score
          </span>
          <span className="bin-tooltip__value">
            {bin.slot_score !== undefined ? (bin.slot_score * 100).toFixed(0) + '%' : '—'}
          </span>
        </div>

        <div className="bin-tooltip__row">
          <span className="bin-tooltip__label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <MapPin size={12} /> Position
          </span>
          <span className="bin-tooltip__value" style={{ fontSize: '0.75rem' }}>
            ({bin.position.x.toFixed(1)}, {bin.position.y.toFixed(1)}, {bin.position.z.toFixed(1)})
          </span>
        </div>

        {/* ── Occupancy Bar ─────────────────────────────── */}
        <OccupancyBar pct={bin.occupancy_pct ?? 0} color={occupancyColor} />
      </div>
    </Html>
  );
}
