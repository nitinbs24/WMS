import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { runsApi } from '../api/runs';

const STATUS_COLORS = {
  queued: 'badge-neutral',
  running: 'badge-warning',
  completed: 'badge-success',
  completed_with_exceptions: 'badge-warning',
  failed: 'badge-danger',
};

export default function DashboardPage() {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: runsApi.list,
    refetchInterval: 5000,
  });

  const recentRuns = runs.slice(0, 5);

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Dashboard</h2>
          <p>Warehouse optimization overview</p>
        </div>
        <Link to="/runs/new">
          <button className="btn btn-primary">+ New Run</button>
        </Link>
      </div>

      {/* Stats row */}
      <div className="grid-4" style={{ marginBottom: 24 }}>
        {[
          { label: 'Total Runs', value: runs.length, color: 'var(--color-primary-light)' },
          { label: 'Completed', value: runs.filter(r => r.status === 'completed').length, color: 'var(--color-success)' },
          { label: 'Running', value: runs.filter(r => r.status === 'running').length, color: 'var(--color-warning)' },
          { label: 'Failed', value: runs.filter(r => r.status === 'failed').length, color: 'var(--color-danger)' },
        ].map((stat) => (
          <div key={stat.label} className="card">
            <div className="text-muted text-sm">{stat.label}</div>
            <div style={{ fontSize: 32, fontWeight: 800, color: stat.color, marginTop: 8 }}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Recent runs */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Recent Optimization Runs</span>
          <Link to="/runs" style={{ fontSize: 13, color: 'var(--color-primary-light)' }}>View all →</Link>
        </div>
        <div className="table-wrapper">
          {isLoading ? (
            <div style={{ height: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)' }}>
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
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run) => (
                  <tr key={run.id}>
                    <td className="font-mono text-xs">{run.id.slice(0, 8)}…</td>
                    <td>{run.goal.replace('_', ' ')}</td>
                    <td>{run.algorithm.replace(/_/g, ' ')}</td>
                    <td>
                      <span className={`badge ${STATUS_COLORS[run.status] || 'badge-neutral'}`}>
                        {run.status}
                      </span>
                    </td>
                    <td>{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
