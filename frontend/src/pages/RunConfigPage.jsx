/**
 * New Run configuration page.
 * Lets manager/admin pick goal + algorithm + scope, then trigger a run.
 * Polls status until completed/failed, then navigates to run history.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { runsApi } from '../api/runs';

const GOALS = [
  {
    id: 'space_efficiency',
    label: 'Space Efficiency',
    description: 'Optimise how products are packed onto pallets and placed into slots to maximise fill rate.',
    icon: '📦',
    algorithms: [
      { id: 'ffdh_com', label: 'FFDH + Centre-of-Mass', description: 'Layer-based packing with stability validation' },
      { id: 'blf_stratified', label: 'BLF + Weight Stratification', description: 'Heavy items on base, light on top' },
    ],
  },
  {
    id: 'picking_efficiency',
    label: 'Picking Efficiency',
    description: 'Assign SKUs to slots that minimise picker travel distance and fatigue.',
    icon: '🏃',
    algorithms: [
      { id: 'golden_zone', label: 'Ergonomic Golden Zone', description: 'High-frequency SKUs at waist-to-shoulder height' },
      { id: 'affinity_clustering', label: 'Apriori Affinity Clustering', description: 'Co-ordered items placed in adjacent slots' },
      { id: 's_shape_routing', label: 'S-Shape Routing', description: 'Serpentine path optimisation for batch picks' },
    ],
  },
];

const SCOPES = [
  { id: 'full', label: 'Full Warehouse', description: 'Re-optimise all slots from scratch' },
  { id: 'incremental', label: 'Incremental', description: 'Only re-assign slots that changed since last run' },
];

export default function RunConfigPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [goal, setGoal] = useState('space_efficiency');
  const [algorithm, setAlgorithm] = useState('ffdh_com');
  const [scope, setScope] = useState('full');
  const [launched, setLaunched] = useState(null);

  const selectedGoal = GOALS.find(g => g.id === goal);

  const { mutate, isPending, error } = useMutation({
    mutationFn: () => runsApi.create(goal, algorithm, scope),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      setLaunched(run);
    },
  });

  if (launched) {
    return (
      <div style={{ maxWidth: 560, margin: '0 auto', paddingTop: 40 }}>
        <div className="card" style={{ padding: '40px 32px', textAlign: 'center' }}>
          <div style={{ fontSize: 56, marginBottom: 16 }}>🚀</div>
          <h2 style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>Run queued!</h2>
          <p style={{ color: 'var(--color-text-muted)', marginBottom: 8, fontSize: 14 }}>
            Run <code style={{ background: 'var(--color-bg)', padding: '2px 6px', borderRadius: 4, fontSize: 12 }}>{launched.id.slice(0, 8)}…</code> has been queued.
          </p>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13, marginBottom: 28 }}>
            The arq worker will pick it up and execute the <strong>{launched.algorithm.replace(/_/g, ' ')}</strong> algorithm.
          </p>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
            <button className="btn btn-primary" onClick={() => navigate('/runs')}>
              View Run History
            </button>
            <button className="btn btn-ghost" onClick={() => { setLaunched(null); }}>
              Start Another Run
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      <div className="page-header">
        <div>
          <h2>New Optimization Run</h2>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>Configure and launch a warehouse optimization job.</p>
        </div>
      </div>

      {error && (
        <div style={{ background: 'rgba(239,68,68,.1)', border: '1px solid rgba(239,68,68,.3)', borderRadius: 8, padding: '12px 16px', marginBottom: 20, color: 'var(--color-danger)', fontSize: 13 }}>
          {error?.body?.detail || error?.message || 'Failed to start run'}
        </div>
      )}

      {/* Step 1 — Goal */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">1. Optimization Goal</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, padding: '0 20px 20px' }}>
          {GOALS.map(g => (
            <button
              key={g.id}
              onClick={() => { setGoal(g.id); setAlgorithm(g.algorithms[0].id); }}
              style={{
                background: goal === g.id ? 'rgba(14,165,233,0.1)' : 'var(--color-bg)',
                border: goal === g.id ? '1.5px solid var(--color-primary-light)' : '1.5px solid var(--color-border-subtle)',
                borderRadius: 10, padding: '16px', cursor: 'pointer', textAlign: 'left',
                transition: 'all 0.15s',
              }}
            >
              <div style={{ fontSize: 28, marginBottom: 8 }}>{g.icon}</div>
              <div style={{ fontWeight: 700, color: 'var(--color-text)', marginBottom: 4 }}>{g.label}</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)', lineHeight: 1.5 }}>{g.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Step 2 — Algorithm */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">2. Algorithm</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '0 20px 20px' }}>
          {selectedGoal?.algorithms.map(alg => (
            <button
              key={alg.id}
              onClick={() => setAlgorithm(alg.id)}
              style={{
                background: algorithm === alg.id ? 'rgba(14,165,233,0.08)' : 'transparent',
                border: algorithm === alg.id ? '1.5px solid var(--color-primary-light)' : '1.5px solid var(--color-border-subtle)',
                borderRadius: 8, padding: '14px 16px', cursor: 'pointer', textAlign: 'left',
                display: 'flex', alignItems: 'center', gap: 14, transition: 'all 0.15s',
              }}
            >
              <div style={{
                width: 18, height: 18, borderRadius: '50%', flexShrink: 0,
                border: '2px solid ' + (algorithm === alg.id ? 'var(--color-primary-light)' : 'var(--color-border)'),
                background: algorithm === alg.id ? 'var(--color-primary-light)' : 'transparent',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {algorithm === alg.id && <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#fff' }} />}
              </div>
              <div>
                <div style={{ fontWeight: 600, color: 'var(--color-text)', fontSize: 14 }}>{alg.label}</div>
                <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>{alg.description}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Step 3 — Scope */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <span className="card-title">3. Scope</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, padding: '0 20px 20px' }}>
          {SCOPES.map(s => (
            <button
              key={s.id}
              onClick={() => setScope(s.id)}
              style={{
                background: scope === s.id ? 'rgba(14,165,233,0.08)' : 'var(--color-bg)',
                border: scope === s.id ? '1.5px solid var(--color-primary-light)' : '1.5px solid var(--color-border-subtle)',
                borderRadius: 8, padding: '14px 16px', cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
              }}
            >
              <div style={{ fontWeight: 600, color: 'var(--color-text)', fontSize: 13 }}>{s.label}</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4 }}>{s.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Launch */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
        <button className="btn btn-ghost" onClick={() => navigate(-1)} disabled={isPending}>
          Cancel
        </button>
        <button
          id="launch-run-btn"
          className="btn btn-primary"
          onClick={() => mutate()}
          disabled={isPending}
          style={{ minWidth: 160, justifyContent: 'center' }}
        >
          {isPending ? 'Launching…' : '🚀 Launch Run'}
        </button>
      </div>
    </div>
  );
}
