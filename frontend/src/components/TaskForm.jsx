import { ArrowUpRight, LoaderCircle, Sparkles } from 'lucide-react';
import { useState } from 'react';

export default function TaskForm({ onRun, busy }) {
  const [title, setTitle] = useState('Normalize Unicode labels');
  const [description, setDescription] = useState('Use Unicode-aware case folding for labels and tags in the synthetic codebase.');

  function submit(event) {
    event.preventDefault();
    onRun({ title, description });
  }

  return (
    <form className="task-form" onSubmit={submit}>
      <div className="form-heading">
        <div className="eyebrow"><Sparkles size={14} /> New agent task</div>
        <span className="provider-pill"><span /> Mock provider</span>
      </div>
      <label htmlFor="task-title">Task name</label>
      <input id="task-title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={120} required />
      <label htmlFor="task-description">What should change?</label>
      <textarea id="task-description" value={description} onChange={(event) => setDescription(event.target.value)} rows="3" maxLength={2000} required />
      <div className="form-footer">
        <span className="subtle-note">Target: <code>target_codebase</code></span>
        <button className="primary-button" type="submit" disabled={busy || title.trim().length < 3 || description.trim().length < 10}>
          {busy ? <LoaderCircle className="spin" size={16} /> : <ArrowUpRight size={16} />}
          {busy ? 'Running…' : 'Create & run'}
        </button>
      </div>
    </form>
  );
}
