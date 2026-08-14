/**
 * Run History page — filterable table of all optimization runs.
 * Clicking a run row expands detail: metrics, assignments, exceptions, rollback.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
      {status === 'running' && <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: m.color, animation: 'pulse 1s infinite' }} />}
      {m.label}
    </span>
  );
}

function MetricCard({ label, value, color }) {
  return (
    <div style={{ background: 'var(--color-bg)', borderRadius: 8, padding: '12px 16px', flex: 1 }}>
      <div style={{ fontSize: 11, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 800, color: color || 'var(--color-text)' }}>{value ?? '—'}</div>
    </div>
  );
}

function RunDetailPanel({ run, onClose }) {
  const queryClient = useQueryClient();
  const { data: assignments = [] } = useQuery({
    queryKey: ['assignments', run.id],
    queryFn: () => runsApi.assignments(run.id),
    enabled: run.status === 'completed' || run.status === 'completed_with_exceptions',
  });
  const { data: exceptions = [], refetch: refetchExceptions } = useQuery({
    queryKey: ['exceptions', run.id],
    queryFn: () => runsApi.exceptions(run.id),
    enabled: run.status === 'completed' || run.status === 'completed_with_exceptions',
  });
  const { mutate: rollback, isPending: rolling } = useMutation({
    mutationFn: () => runsApi.rollback(run.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['runs'] }),
  });
  const { mutate: resolveExc, variables: resolvingId } = useMutation({
    mutationFn: (excId) => runsApi.resolveException(run.id, excId),
    onSuccess: () => {
      refetchExceptions();
      queryClient.invalidateQueries({ queryKey: ['runs'] });
    },
  });

  const m = run.summary_metrics || {};
  const openExceptions = exceptions.filter(e => e.status !== 'resolved');
  const resolvedCount = exceptions.length - openExceptions.length;

  return (
    <div style={{ background: 'var(--color-bg)', border: '1px solid var(--color-border-subtle)', borderRadius: 10, padding: 20, marginTop: 4 }}>
      {/* Metrics */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <MetricCard label="Assignments" value={m.assignments ?? assignments.length} color="var(--color-primary-light)" />
        <MetricCard label="Open Exceptions" value={openExceptions.length} color={openExceptions.length > 0 ? 'var(--color-warning)' : 'var(--color-success)'} />
        <MetricCard label="Resolved" value={resolvedCount} color="var(--color-success)" />
        <MetricCard label="Fill Rate" value={m.fill_rate_pct != null ? `${m.fill_rate_pct}%` : null} color="var(--color-success)" />
      </div>

      {/* Exceptions list with resolve button */}
      {exceptions.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>⚠ Exceptions ({exceptions.length})</span>
            {resolvedCount > 0 && (
              <span style={{ fontSize: 11, color: '#10b981', background: 'rgba(16,185,129,.1)', padding: '2px 8px', borderRadius: 10 }}>
                {resolvedCount} resolved
              </span>
            )}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 220, overflowY: 'auto' }}>
            {exceptions.slice(0, 15).map(exc => (
              <div key={exc.id} style={{
                background: exc.status === 'resolved' ? 'rgba(16,185,129,.05)' : 'rgba(245,158,11,.07)',
                border: `1px solid ${exc.status === 'resolved' ? 'rgba(16,185,129,.2)' : 'rgba(245,158,11,.2)'}`,
                borderRadius: 6, padding: '8px 12px', fontSize: 12,
                display: 'flex', alignItems: 'center', gap: 10,
              }}>
                <div style={{ flex: 1 }}>
                  <span style={{ color: exc.status === 'resolved' ? '#10b981' : '#f59e0b', fontWeight: 600 }}>
                    {exc.reason_code}
                  </span>
                  <span style={{ color: 'var(--color-text-muted)', marginLeft: 8 }}>{exc.reason_detail}</span>
                </div>
                {exc.status === 'resolved' ? (
                  <span style={{ color: '#10b981', fontSize: 11, whiteSpace: 'nowrap' }}>✓ Resolved</span>
                ) : (
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ fontSize: 11, padding: '2px 10px', whiteSpace: 'nowrap', color: '#10b981', borderColor: 'rgba(16,185,129,.3)' }}
                    onClick={() => resolveExc(exc.id)}
                    disabled={resolvingId === exc.id}
                  >
                    {resolvingId === exc.id ? '…' : '✓ Resolve'}
                  </button>
                )}
              </div>
            ))}
            {exceptions.length > 15 && <div style={{ color: 'var(--color-text-muted)', fontSize: 12, textAlign: 'center' }}>…and {exceptions.length - 15} more</div>}
          </div>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <Link to="/twin">
          <button className="btn btn-primary btn-sm">View in 3D Twin</button>
        </Link>
        <a href={runsApi.exportCsv(run.id)} download>
          <button className="btn btn-ghost btn-sm">⬇ Export CSV</button>
        </a>
        {(run.status === 'completed' || run.status === 'completed_with_exceptions') && (
          <button
            className="btn btn-ghost btn-sm"
            style={{ color: 'var(--color-danger)', marginLeft: 'auto' }}
            onClick={() => rollback()}
            disabled={rolling}
          >
            {rolling ? 'Rolling back…' : '↩ Rollback'}
          </button>
        )}
      </div>
    </div>
  );
}

export default function RunHistoryPage() {
  const [goalFilter, setGoalFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [expanded, setExpanded] = useState(null);

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: runsApi.list,
    refetchInterval: 5000,
  });

  const filtered = runs.filter(r =>
    (!goalFilter || r.goal === goalFilter) &&
    (!statusFilter || r.status === statusFilter)
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Run History</h2>
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>All optimization runs — click a row to expand details.</p>
        </div>
        <Link to="/runs/new">
          <button className="btn btn-primary">+ New Run</button>
        </Link>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <select
          className="form-input"
          style={{ width: 'auto', padding: '7px 12px' }}
          value={goalFilter}
          onChange={e => setGoalFilter(e.target.value)}
        >
          <option value="">All goals</option>
          <option value="space_efficiency">Space Efficiency</option>
          <option value="picking_efficiency">Picking Efficiency</option>
        </select>
        <select
          className="form-input"
          style={{ width: 'auto', padding: '7px 12px' }}
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          {Object.entries(STATUS_META).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <span style={{ marginLeft: 'auto', color: 'var(--color-text-muted)', fontSize: 13, alignSelf: 'center' }}>
          {filtered.length} run{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="card">
        {isLoading ? (
          <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-muted)' }}>Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <h3>No runs found</h3>
            <p>Adjust your filters or start a new optimization run.</p>
            <Link to="/runs/new"><button className="btn btn-primary btn-sm">Start a run</button></Link>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 32 }}></th>
                  <th>Run ID</th>
                  <th>Goal</th>
                  <th>Algorithm</th>
                  <th>Scope</th>
                  <th>Status</th>
                  <th>Fill Rate</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(run => (
                  <>
                    <tr
                      key={run.id}
                      onClick={() => setExpanded(expanded === run.id ? null : run.id)}
                      style={{ cursor: 'pointer', transition: 'background 0.1s' }}
                    >
                      <td style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>
                        {expanded === run.id ? '▼' : '▶'}
                      </td>
                      <td className="font-mono" style={{ fontSize: 12 }}>{run.id.slice(0, 8)}…</td>
                      <td>{run.goal.replace(/_/g, ' ')}</td>
                      <td style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>{run.algorithm.replace(/_/g, ' ')}</td>
                      <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{run.scope}</td>
                      <td><StatusBadge status={run.status} /></td>
                      <td style={{ fontVariantNumeric: 'tabular-nums', fontSize: 13 }}>
                        {run.summary_metrics?.fill_rate_pct != null ? `${run.summary_metrics.fill_rate_pct}%` : '—'}
                      </td>
                      <td style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>
                        {new Date(run.created_at).toLocaleString()}
                      </td>
                    </tr>
                    {expanded === run.id && (
                      <tr key={`${run.id}-detail`}>
                        <td colSpan={8} style={{ padding: '0 12px 12px' }}>
                          <RunDetailPanel run={run} onClose={() => setExpanded(null)} />
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
