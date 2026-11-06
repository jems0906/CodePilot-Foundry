import { FileCode2 } from 'lucide-react';

export default function DiffViewer({ diff }) {
  const lines = diff ? diff.replace(/\n$/, '').split('\n') : [];
  return (
    <section className="panel diff-panel">
      <div className="panel-title">
        <div><FileCode2 size={16} /><h2>Proposed diff</h2></div>
        <span className="file-label">src / text_utils.py</span>
      </div>
      {lines.length ? (
        <pre className="diff-code" aria-label="Proposed code diff">
          {lines.map((line, index) => {
            const type = line.startsWith('+') && !line.startsWith('+++') ? 'added' : line.startsWith('-') && !line.startsWith('---') ? 'removed' : line.startsWith('@@') ? 'hunk' : '';
            return <span className={`diff-line ${type}`} key={`${index}-${line}`}>{line || ' '}</span>;
          })}
        </pre>
      ) : <div className="empty-state">Select a completed run to inspect its proposal.</div>}
    </section>
  );
}
