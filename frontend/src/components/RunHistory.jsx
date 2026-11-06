import { Check, CircleDot, Clock3, X } from 'lucide-react';

const statusIcon = {
  approved: <Check size={13} />,
  rejected: <X size={13} />,
  ready_for_review: <CircleDot size={13} />,
  running: <Clock3 size={13} />,
};

export default function RunHistory({ runs, selectedId, onSelect }) {
  if (!runs.length) return <p className="empty-small">Runs will appear here.</p>;
  return (
    <div className="run-list">
      {runs.map((run) => (
        <button className={`run-row ${selectedId === run.id ? 'selected' : ''}`} key={run.id} onClick={() => onSelect(run)}>
          <span className={`run-status ${run.status}`}>{statusIcon[run.status] || <Clock3 size={13} />}</span>
          <span className="run-copy">
            <strong>Run #{String(run.id).padStart(3, '0')}</strong>
            <small>{run.test_result?.exit_code === 0 ? 'Checks passed' : run.status === 'failed' ? 'Run failed' : 'Awaiting review'}</small>
          </span>
          <time>{new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>
        </button>
      ))}
    </div>
  );
}
