import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { runsApi } from '../api/runs';

const SPACE_ALGORITHMS = [
  { value: 'ffdh_com', label: 'Modified FFDH + CoM Validation', description: 'First-Fit Decreasing Height with Centre-of-Mass stability check' },
  { value: 'blf_stratified', label: 'BLF + Weight Stratification', description: 'Bottom-Left Fill with weight-class layering' },
];

const PICKING_ALGORITHMS = [
  { value: 'golden_zone', label: 'Ergonomic Golden Zone', description: 'Frequency-based slotting to ergonomic rack levels' },
  { value: 'affinity_clustering', label: 'Apriori Affinity Clustering', description: 'Groups co-ordered SKUs into adjacent slots' },
  { value: 's_shape_routing', label: 'S-Shape Pick-Path Routing', description: 'Minimises total picker travel distance' },
];

export default function RunConfigPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [goal, setGoal] = useState('');
  const [algorithm, setAlgorithm] = useState('');
  const [scope, setScope] = useState('full');

  const algorithms = goal === 'space_efficiency' ? SPACE_ALGORITHMS : goal === 'picking_efficiency' ? PICKING_ALGORITHMS : [];

  const { mutate, isPending, error } = useMutation({
    mutationFn: () => runsApi.create(goal, algorithm, scope),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      navigate('/runs');
    },
  });

  const canSubmit = goal && algorithm && scope;

  return (
    <div style={{ maxWidth: 680 }}>
      <div className="page-header">
        <div>
          <h2>New Optimization Run</h2>
          <p>Configure and trigger a slotting optimization</p>
        </div>
      </div>

      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
        {/* Step 1: Goal */}
        <div>
          <div className="form-label" style={{ marginBottom: 12 }}>1. Optimization objective</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { value: 'space_efficiency', label: 'Space Efficiency', desc: 'Maximize cubic fill rate of every rack slot' },
              { value: 'picking_efficiency', label: 'Picking Efficiency', desc: 'Minimize forklift travel time and picker effort' },
            ].map((g) => (
              <button
                key={g.value}
                id={`goal-${g.value}`}
                className="btn btn-outline"
                style={{
                  flexDirection: 'column', alignItems: 'flex-start', padding: '14px 16px',
                  height: 'auto', textAlign: 'left',
                  borderColor: goal === g.value ? 'var(--color-primary)' : undefined,
                  background: goal === g.value ? 'rgba(99,102,241,.08)' : undefined,
                  color: goal === g.value ? 'var(--color-text)' : undefined,
                }}
                onClick={() => { setGoal(g.value); setAlgorithm(''); }}
              >
                <span style={{ fontWeight: 600, fontSize: 14 }}>{g.label}</span>
                <span style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4 }}>{g.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Step 2: Algorithm */}
        {goal && (
          <div>
            <div className="form-label" style={{ marginBottom: 12 }}>
              2. {goal === 'space_efficiency' ? 'Pallet-building strategy' : 'Slotting algorithm'}
            </div>
            {goal === 'space_efficiency' && (
              <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 12 }}>
                W-BFDH always runs as the fixed pallet→slot placement step, regardless of your choice here.
              </p>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {algorithms.map((alg) => (
                <button
                  key={alg.value}
                  id={`algo-${alg.value}`}
                  className="btn btn-outline"
                  style={{
                    justifyContent: 'flex-start', flexDirection: 'column', alignItems: 'flex-start',
                    padding: '12px 14px', height: 'auto', textAlign: 'left',
                    borderColor: algorithm === alg.value ? 'var(--color-primary)' : undefined,
                    background: algorithm === alg.value ? 'rgba(99,102,241,.08)' : undefined,
                    color: algorithm === alg.value ? 'var(--color-text)' : undefined,
                  }}
                  onClick={() => setAlgorithm(alg.value)}
                >
                  <span style={{ fontWeight: 600, fontSize: 13.5 }}>{alg.label}</span>
                  <span style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 3 }}>{alg.description}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Scope */}
        {algorithm && (
          <div>
            <div className="form-label" style={{ marginBottom: 12 }}>3. Scope</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {[
                { value: 'full', label: 'Full re-slot', desc: 'Recomputes placement for the entire warehouse' },
                { value: 'incremental', label: 'Incremental', desc: 'Only places new/changed stock, leaves existing assignments' },
              ].map((s) => (
                <button
                  key={s.value}
                  id={`scope-${s.value}`}
                  className="btn btn-outline"
                  style={{
                    flexDirection: 'column', alignItems: 'flex-start', padding: '12px 14px',
                    height: 'auto', textAlign: 'left',
                    borderColor: scope === s.value ? 'var(--color-primary)' : undefined,
                    background: scope === s.value ? 'rgba(99,102,241,.08)' : undefined,
                    color: scope === s.value ? 'var(--color-text)' : undefined,
                  }}
                  onClick={() => setScope(s.value)}
                >
                  <span style={{ fontWeight: 600, fontSize: 13.5 }}>{s.label}</span>
                  <span style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 3 }}>{s.desc}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,.1)', borderRadius: 8, color: 'var(--color-danger)', fontSize: 13 }}>
            {error.message}
          </div>
        )}

        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
          <button className="btn btn-outline" onClick={() => navigate('/runs')}>Cancel</button>
          <button
            id="run-submit"
            className="btn btn-primary"
            disabled={!canSubmit || isPending}
            onClick={() => mutate()}
          >
            {isPending ? 'Queuing run…' : 'Run Optimization'}
          </button>
        </div>
      </div>
    </div>
  );
}
