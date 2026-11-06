import { Check, ShieldCheck, X } from 'lucide-react';

export default function ReviewGate({ run, onReview, busy }) {
  if (!run) return null;
  const available = run.status === 'ready_for_review';
  const testsPassed = run.test_result?.exit_code === 0 && !run.test_result?.timed_out;
  return (
    <section className="review-gate">
      <div className="review-summary">
        <span className={`check-mark ${testsPassed ? 'pass' : 'fail'}`}>{testsPassed ? <Check size={15} /> : <X size={15} />}</span>
        <div><strong>{testsPassed ? 'Checks passed' : 'Checks need attention'}</strong><small>{run.test_result?.command?.join(' ') || 'No test command recorded'}</small></div>
      </div>
      {available ? (
        <div className="review-actions">
          <button className="reject-button" onClick={() => onReview('rejected')} disabled={busy}><X size={15} /> Reject</button>
          <button className="approve-button" onClick={() => onReview('approved')} disabled={busy || !testsPassed}><ShieldCheck size={15} /> Approve change</button>
        </div>
      ) : <span className={`decision-label ${run.status}`}>{run.status.replaceAll('_', ' ')}</span>}
    </section>
  );
}
