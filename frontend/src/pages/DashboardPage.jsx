import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { runsApi } from '../api/runs';

const STATUS_META = {
  queued:                    { color: '#64748b', bg: 'rgba(100,116,139,.12)', label: 'Queued' },
  running:                   { color: '#f59e0b', bg: 'rgba(245,158,11,.12)', label: 'Running' },
  completed:                 { color: '#10b981', bg: 'rgba(16,185,129,.12)', label: 'Completed' },
  completed_with_exceptions: { color: '#f59e0b', bg: 'rgba(245,158,11,.12)', label: 'With Exceptions' },
  failed:                    { color: '#ef4444', bg: 'rgba(239,68,68,.12)', label: 'Failed' },
};

function StatusBadge({ status }) {
  const m = STATUS_META[status] || { color: '#94a3b8', bg: 'rgba(148,163,184,.1)', label: status };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 10px', borderRadius: 20, background: m.bg, color: m.color, fontSize: 12, fontWeight: 600 }}>
      {status === 'running' && (
        <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: m.color, animation: 'pulse 1s ease-in-out infinite', flexShrink: 0 }} />
      )}
      {m.label}
    </span>
  );
}

function LiveRunBanner({ runs }) {
  const liveRuns = runs.filter(r => r.status === 'running' || r.status === 'queued');
  if (!liveRuns.length) return null;
  return (
    <div style={{
      background: 'rgba(245,158,11,.08)',
      border: '1px solid rgba(245,158,11,.25)',
      borderRadius: 10, padding: '12px 18px', marginBottom: 20,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#f59e0b', animation: 'pulse 1s ease-in-out infinite', flexShrink: 0 }} />
      <span style={{ color: '#f59e0b', fontWeight: 600, fontSize: 13 }}>
        {liveRuns.length} run{liveRuns.length > 1 ? 's' : ''} in progress
      </span>
      <span style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>
        Auto-refreshing every 5 seconds…
      </span>
      <Link to="/runs" style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--color-primary-light)' }}>
        View details →
      </Link>
    </div>
  );
}

export default function DashboardPage() {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: runsApi.list,
    refetchInterval: 5000,
  });

  const recentRuns = runs.slice(0, 6);
  const lastCompleted = runs.find(r => r.status === 'completed' || r.status === 'completed_with_exceptions');
  const totalExceptions = runs.reduce((sum, r) => sum + (r.summary_metrics?.exceptions ?? 0), 0);

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>Warehouse optimization overview</p>
        </div>
        <Link to="/runs/new">
          <button className="btn btn-primary">+ New Run</button>
        </Link>
      </div>

      {/* Live run banner */}
      <LiveRunBanner runs={runs} />

      {/* Stats row */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        {[
          { label: 'Total Runs', value: runs.length, color: 'var(--color-primary-light)', icon: '🚀' },
          { label: 'Completed', value: runs.filter(r => r.status === 'completed' || r.status === 'completed_with_exceptions').length, color: 'var(--color-success)', icon: '✅' },
          { label: 'Open Exceptions', value: totalExceptions, color: totalExceptions > 0 ? 'var(--color-warning)' : 'var(--color-text-muted)', icon: '⚠' },
          { label: 'Last Fill Rate', value: lastCompleted?.summary_metrics?.fill_rate_pct != null ? `${lastCompleted.summary_metrics.fill_rate_pct}%` : '—', color: 'var(--color-accent)', icon: '📊' },
        ].map((stat) => (
          <div key={stat.label} className="card" style={{ position: 'relative', overflow: 'hidden' }}>
            <div style={{ fontSize: 22, marginBottom: 8 }}>{stat.icon}</div>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>{stat.label}</div>
            <div style={{ fontSize: 30, fontWeight: 800, color: stat.color, marginTop: 4 }}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Recent runs table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Recent Optimization Runs</span>
          <Link to="/runs" style={{ fontSize: 13, color: 'var(--color-primary-light)' }}>View all →</Link>
        </div>
        <div className="table-wrapper">
          {isLoading ? (
            <div style={{ height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)', gap: 10 }}>
              <div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
              Loading…
            </div>
          ) : recentRuns.length === 0 ? (
            <div className="empty-state">
              <h3>No runs yet</h3>
              <p>Start your first optimization run to see results here.</p>
              <Link to="/runs/new"><button className="btn btn-primary btn-sm">Start a run</button></Link>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Goal</th>
                  <th>Algorithm</th>
                  <th>Status</th>
                  <th>Fill Rate</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr key={run.id}>
                    <td className="font-mono" style={{ fontSize: 11 }}>{run.id.slice(0, 8)}…</td>
                    <td>{run.goal.replace(/_/g, ' ')}</td>
                    <td style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>{run.algorithm.replace(/_/g, ' ')}</td>
                    <td><StatusBadge status={run.status} /></td>
                    <td style={{ fontVariantNumeric: 'tabular-nums', fontSize: 13 }}>
                      {run.summary_metrics?.fill_rate_pct != null ? `${run.summary_metrics.fill_rate_pct}%` : '—'}
                    </td>
                    <td style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Quick action strip */}
      <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
        <Link to="/runs/new" style={{ flex: 1 }}>
          <div className="card" style={{ padding: '16px 20px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 14, transition: 'border-color 0.15s', border: '1px solid var(--color-border-subtle)' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-primary-light)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-border-subtle)'}
          >
            <span style={{ fontSize: 28 }}>🚀</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14 }}>Launch New Run</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Configure algorithm &amp; scope</div>
            </div>
          </div>
        </Link>
        <Link to="/twin" style={{ flex: 1 }}>
          <div className="card" style={{ padding: '16px 20px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 14, transition: 'border-color 0.15s', border: '1px solid var(--color-border-subtle)' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-accent)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-border-subtle)'}
          >
            <span style={{ fontSize: 28 }}>🏭</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14 }}>3D Digital Twin</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>View warehouse in real-time</div>
            </div>
          </div>
        </Link>
        <Link to="/admin/settings" style={{ flex: 1 }}>
          <div className="card" style={{ padding: '16px 20px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 14, transition: 'border-color 0.15s', border: '1px solid var(--color-border-subtle)' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-primary)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-border-subtle)'}
          >
            <span style={{ fontSize: 28 }}>⚙️</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14 }}>Threshold Settings</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Tune algorithm parameters</div>
            </div>
          </div>
        </Link>
      </div>
    </div>
  );
}
