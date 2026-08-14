import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { runsApi } from '../api/runs';

const STATUS_BADGE = {
  queued: 'badge-neutral',
  running: 'badge-warning',
  completed: 'badge-success',
  completed_with_exceptions: 'badge-warning',
  failed: 'badge-danger',
};

export default function RunHistoryPage() {
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: runsApi.list,
    refetchInterval: 5000,
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Run History</h2>
          <p>{runs.length} optimization run{runs.length !== 1 ? 's' : ''}</p>
        </div>
        <Link to="/runs/new">
          <button className="btn btn-primary">+ New Run</button>
        </Link>
      </div>

      <div className="card">
        <div className="table-wrapper">
          {isLoading ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading…</div>
          ) : runs.length === 0 ? (
            <div className="empty-state">
              <h3>No runs yet</h3>
              <p>Trigger an optimization run to see results here.</p>
              <Link to="/runs/new"><button className="btn btn-primary btn-sm">Start a run</button></Link>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Goal</th>
                  <th>Algorithm</th>
                  <th>Scope</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id}>
                    <td className="font-mono text-xs">{run.id.slice(0, 8)}…</td>
                    <td>{run.goal.replace('_', ' ')}</td>
                    <td>{run.algorithm.replace(/_/g, ' ')}</td>
                    <td>{run.scope}</td>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className={`status-dot ${run.status}`} />
                        <span className={`badge ${STATUS_BADGE[run.status] || 'badge-neutral'}`}>{run.status}</span>
                      </span>
                    </td>
                    <td>{new Date(run.created_at).toLocaleString()}</td>
                    <td>
                      <Link to={`/twin?run=${run.id}`} style={{ color: 'var(--color-primary-light)', fontSize: 12 }}>View in 3D →</Link>
                    </td>
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
