import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsApi } from '../api/settings';
import { useAuthStore } from '../store/useAuthStore';

export default function AdminSettingsPage() {
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();

  const { data: thresholds, isLoading } = useQuery({
    queryKey: ['thresholds'],
    queryFn: settingsApi.getThresholds,
  });

  if (user?.role !== 'admin') {
    return (
      <div className="empty-state">
        <h3>Access denied</h3>
        <p>Only Admin users can access threshold settings.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720 }}>
      <div className="page-header">
        <div>
          <h2>Admin Settings</h2>
          <p>Safety thresholds — each save creates a new versioned record</p>
        </div>
      </div>

      {isLoading ? (
        <div className="card"><div style={{ padding: 24, color: 'var(--color-text-muted)' }}>Loading thresholds…</div></div>
      ) : thresholds ? (
        <div className="card">
          <div className="card-header">
            <span className="card-title">Active Thresholds — v{thresholds.version}</span>
            <span className="badge badge-success">Active</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {[
              { key: 'heavy_weight_kg', label: 'Heavy weight threshold (kg)' },
              { key: 'medium_weight_kg', label: 'Medium weight threshold (kg)' },
              { key: 'com_threshold', label: 'CoM stability threshold (FFDH)' },
              { key: 'blf_com_threshold', label: 'CoM stability threshold (BLF)' },
              { key: 'aisle_a_density_cap', label: 'Aisle A-class density cap' },
              { key: 'pick_lookback_days', label: 'Pick history lookback (days)' },
            ].map(({ key, label }) => (
              <div key={key} className="form-group">
                <label className="form-label">{label}</label>
                <input
                  className="form-input"
                  type="number"
                  step="any"
                  defaultValue={thresholds[key]}
                  disabled
                />
              </div>
            ))}
          </div>
          <p style={{ marginTop: 16, fontSize: 12, color: 'var(--color-text-muted)' }}>
            Threshold editing implemented in Phase 5. Each save creates a new version — past runs remain auditable against historical thresholds.
          </p>
        </div>
      ) : null}
    </div>
  );
}
