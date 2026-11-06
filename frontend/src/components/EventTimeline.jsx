import { Check, Circle, FileSearch, GitPullRequest, Play, Sparkles } from 'lucide-react';

const icons = {
  run_started: Play,
  plan_generated: Sparkles,
  file_read: FileSearch,
  change_proposed: GitPullRequest,
  command_executed: Play,
  self_reviewed: Check,
  run_ready_for_review: Check,
  review_submitted: Check,
};

export default function EventTimeline({ events }) {
  if (!events.length) return <div className="empty-state compact">Action history appears after a run.</div>;
  return (
    <ol className="event-list">
      {events.map((event) => {
        const Icon = icons[event.type] || Circle;
        return (
          <li key={event.id}>
            <span className="event-icon"><Icon size={13} /></span>
            <div className="event-body">
              <div><strong>{event.type.replaceAll('_', ' ')}</strong><time>{new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time></div>
              {event.type === 'command_executed' ? <p>{event.payload.command?.join(' ')} · exit {event.payload.exit_code ?? 'timeout'}</p> : null}
              {event.payload.sandbox_policy ? <p>{event.payload.sandbox_policy.containerized ? 'Isolated container' : 'Local process'} · network {event.payload.sandbox_policy.network_mode} · {event.payload.sandbox_policy.read_only_rootfs ? 'read-only rootfs' : 'writable rootfs'} · UID {event.payload.sandbox_policy.user} · {event.payload.sandbox_policy.memory_limit} memory · {event.payload.sandbox_policy.cpu_limit}</p> : null}
              {event.type === 'file_read' ? <p>{event.payload.path} · {event.payload.sha256?.slice(0, 10)}</p> : null}
              {event.type === 'review_submitted' ? <p>{event.payload.decision}: {event.payload.note || 'No note'}</p> : null}
              {event.type === 'plan_generated' ? <p>{event.payload.steps?.join('  /  ')}</p> : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
