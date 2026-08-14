/**
 * Admin Settings — Threshold Settings page.
 * Shows currently active version, editable form, and version history.
 * Each save creates a new immutable version (old versions preserved).
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

function useThresholds() {
  return useQuery({
    queryKey: ['thresholds'],
    queryFn: () => api.get('/api/v1/settings/thresholds'),
  });
}
function useThresholdHistory() {
  return useQuery({
    queryKey: ['thresholds-history'],
    queryFn: () => api.get('/api/v1/settings/thresholds/history'),
  });
}

const FIELDS = [
  { key: 'heavy_weight_kg',    label: 'Heavy Weight Threshold (kg)', description: 'Pallets above this weight are treated as "heavy" and restricted to level 1 only', min: 100, max: 2000, step: 10 },
  { key: 'medium_weight_kg',   label: 'Medium Weight Threshold (kg)', description: 'Pallets above this but below heavy threshold may only go on levels 1–2', min: 50, max: 1000, step: 10 },
  { key: 'com_threshold',      label: 'CoM Threshold (FFDH)', description: 'Maximum centre-of-mass offset as a fraction of the pallet half-dimension', min: 0.1, max: 1.0, step: 0.05 },
  { key: 'blf_com_threshold',  label: 'CoM Threshold (BLF)', description: 'Slightly looser CoM threshold used by the BLF + Stratification algorithm', min: 0.1, max: 1.0, step: 0.05 },
  { key: 'aisle_a_density_cap', label: 'Aisle-A Density Cap', description: 'Maximum fraction of slots in aisle A that may hold A-class products (congestion limit)', min: 0.1, max: 1.0, step: 0.05 },
  { key: 'pick_lookback_days', label: 'Pick Lookback Window (days)', description: 'How far back pick history is counted when computing SKU frequencies', min: 7, max: 365, step: 1 },
];

const ERGO_LEVELS = ['L1', 'L2', 'L3', 'L4'];

export default function AdminSettingsPage() {
  const queryClient = useQueryClient();
  const { data: active, isLoading } = useThresholds();
  const { data: history = [] } = useThresholdHistory();
  const [form, setForm] = useState(null);
  const [saved, setSaved] = useState(false);

  const currentForm = form ?? active;

  const { mutate: saveVersion, isPending, error } = useMutation({
    mutationFn: (body) => api.post('/api/v1/settings/thresholds', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['thresholds'] });
      queryClient.invalidateQueries({ queryKey: ['thresholds-history'] });
      setForm(null);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const handleChange = (key, value) => {
    setForm(f => ({ ...(f ?? active), [key]: value }));
    setSaved(false);
  };

  const handleErgoChange = (level, value) => {
    setForm(f => ({
      ...(f ?? active),
      ergonomic_factors: { ...(f ?? active)?.ergonomic_factors, [level]: parseFloat(value) },
    }));
  };

  const handleSave = () => {
    if (!currentForm) return;
    saveVersion({
      heavy_weight_kg: parseFloat(currentForm.heavy_weight_kg),
      medium_weight_kg: parseFloat(currentForm.medium_weight_kg),
      com_threshold: parseFloat(currentForm.com_threshold),
      blf_com_threshold: parseFloat(currentForm.blf_com_threshold),
      aisle_a_density_cap: parseFloat(currentForm.aisle_a_density_cap),
      ergonomic_factors: currentForm.ergonomic_factors,
      pick_lookback_days: parseInt(currentForm.pick_lookback_days),
    });
  };

  const isDirty = form !== null;

  return (
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      <div className="page-header">
        <div>
          <h2>Threshold Settings</h2>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>
            Each save creates a new immutable version. Past runs keep their snapshot for auditing.
          </p>
        </div>
        {active && (
          <div style={{ padding: '6px 14px', background: 'rgba(16,185,129,.1)', border: '1px solid rgba(16,185,129,.25)', borderRadius: 8, fontSize: 13, color: '#10b981', fontWeight: 600 }}>
            Active: v{active.version}
          </div>
        )}
      </div>

      {error && (
        <div style={{ background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 8, padding: '12px 16px', marginBottom: 16, color: 'var(--color-danger)', fontSize: 13 }}>
          {error?.body?.detail || 'Failed to save settings'}
        </div>
      )}

      {saved && (
        <div style={{ background: 'rgba(16,185,129,.1)', border: '1px solid rgba(16,185,129,.25)', borderRadius: 8, padding: '12px 16px', marginBottom: 16, color: '#10b981', fontSize: 13 }}>
          ✓ New version saved successfully.
        </div>
      )}

      {isLoading ? (
        <div className="card" style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)' }}>Loading…</div>
      ) : (
        <>
          {/* Main settings form */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">
              <span className="card-title">Safety Thresholds</span>
              {isDirty && <span style={{ fontSize: 12, color: 'var(--color-warning)', padding: '2px 8px', background: 'rgba(245,158,11,.1)', borderRadius: 12 }}>Unsaved changes</span>}
            </div>
            <div style={{ padding: '4px 20px 20px', display: 'flex', flexDirection: 'column', gap: 20 }}>
              {FIELDS.map(field => (
                <div key={field.key}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                    <label style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text)' }}>{field.label}</label>
                    <span style={{ fontSize: 18, fontWeight: 800, color: 'var(--color-primary-light)', fontVariantNumeric: 'tabular-nums', minWidth: 60, textAlign: 'right' }}>
                      {currentForm?.[field.key] ?? '—'}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={field.min}
                    max={field.max}
                    step={field.step}
                    value={currentForm?.[field.key] ?? field.min}
                    onChange={e => handleChange(field.key, parseFloat(e.target.value))}
                    style={{ width: '100%', accentColor: 'var(--color-primary-light)', cursor: 'pointer' }}
                  />
                  <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4 }}>{field.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Ergonomic factors */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">
              <span className="card-title">Ergonomic Level Factors</span>
            </div>
            <div style={{ padding: '4px 20px 20px', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
              {ERGO_LEVELS.map(lvl => (
                <div key={lvl}>
                  <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)', display: 'block', marginBottom: 8 }}>
                    {lvl} {lvl === 'L2' && <span style={{ fontSize: 10, color: '#10b981', background: 'rgba(16,185,129,.1)', padding: '1px 6px', borderRadius: 8 }}>golden</span>}
                  </label>
                  <input
                    type="number"
                    className="form-input"
                    min={0}
                    max={1}
                    step={0.05}
                    value={currentForm?.ergonomic_factors?.[lvl] ?? 1}
                    onChange={e => handleErgoChange(lvl, e.target.value)}
                    style={{ textAlign: 'center' }}
                  />
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4, textAlign: 'center' }}>
                    {lvl === 'L1' && 'Floor level' }
                    {lvl === 'L2' && 'Waist height' }
                    {lvl === 'L3' && 'Shoulder' }
                    {lvl === 'L4' && 'Overhead' }
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Save */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginBottom: 32 }}>
            {isDirty && (
              <button className="btn btn-ghost" onClick={() => { setForm(null); setSaved(false); }}>
                Reset
              </button>
            )}
            <button
              id="save-thresholds-btn"
              className="btn btn-primary"
              onClick={handleSave}
              disabled={isPending || !isDirty}
              style={{ minWidth: 160, justifyContent: 'center' }}
            >
              {isPending ? 'Saving…' : `Save as v${(active?.version ?? 0) + 1}`}
            </button>
          </div>

          {/* Version history */}
          {history.length > 0 && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">Version History</span>
              </div>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Version</th>
                      <th>Heavy (kg)</th>
                      <th>Medium (kg)</th>
                      <th>CoM</th>
                      <th>Lookback</th>
                      <th>Active</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[...history].sort((a, b) => b.version - a.version).map(v => (
                      <tr key={v.id} style={{ opacity: v.is_active ? 1 : 0.5 }}>
                        <td><strong>v{v.version}</strong></td>
                        <td>{v.heavy_weight_kg}</td>
                        <td>{v.medium_weight_kg}</td>
                        <td>{v.com_threshold}</td>
                        <td>{v.pick_lookback_days}d</td>
                        <td>
                          {v.is_active
                            ? <span style={{ color: '#10b981', fontWeight: 600 }}>✓ Active</span>
                            : <span style={{ color: 'var(--color-text-muted)' }}>–</span>
                          }
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                          {new Date(v.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
