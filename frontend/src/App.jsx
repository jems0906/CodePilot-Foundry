import { Activity, AlertTriangle, Bot, ChevronRight, CircleCheck, FolderGit2, GitBranch, Layers3, RefreshCw, Shield, Workflow } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from './api.js';
import DiffViewer from './components/DiffViewer.jsx';
import EventTimeline from './components/EventTimeline.jsx';
import ReviewGate from './components/ReviewGate.jsx';
import RunHistory from './components/RunHistory.jsx';
import TaskForm from './components/TaskForm.jsx';

const files = ['src/text_utils.py', 'tests/test_text_utils.py', 'pytest.ini'];

export default function App() {
  const [runs, setRuns] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [events, setEvents] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function refresh() {
    const [nextTasks, nextRuns] = await Promise.all([api.tasks(), api.runs()]);
    setTasks(nextTasks);
    setRuns(nextRuns);
    if (!selectedRun && nextRuns.length) setSelectedRun(nextRuns[0]);
  }

  useEffect(() => {
    refresh().catch((cause) => setError(cause.message));
  }, []);

  useEffect(() => {
    if (!selectedRun) {
      setEvents([]);
      return;
    }
    api.events(selectedRun.id).then(setEvents).catch((cause) => setError(cause.message));
  }, [selectedRun?.id]);

  async function handleRun(taskInput) {
    setBusy(true);
    setError('');
    try {
      const task = await api.createTask(taskInput);
      setTasks((current) => [task, ...current]);
      const run = await api.run(task.id);
      setSelectedRun(run);
      const [nextRuns, nextEvents] = await Promise.all([api.runs(), api.events(run.id)]);
      setRuns(nextRuns);
      setEvents(nextEvents);
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleReview(decision) {
    if (!selectedRun) return;
    setBusy(true);
    setError('');
    try {
      const review = await api.review(selectedRun.id, decision);
      setSelectedRun((current) => ({ ...current, status: review.decision }));
      const [nextRuns, nextEvents] = await Promise.all([api.runs(), api.events(selectedRun.id)]);
      setRuns(nextRuns);
      setEvents(nextEvents);
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBusy(false);
    }
  }

  const passedRuns = runs.filter((run) => run.test_result?.exit_code === 0).length;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#workspace" aria-label="CodePilot Foundry home">
          <span className="brand-mark"><Workflow size={19} strokeWidth={2.2} /></span>
          <span>codepilot<span className="brand-light">foundry</span></span>
        </a>
        <div className="topbar-right">
          <span className="workspace-chip"><span className="status-dot" /> Synthetic workspace</span>
          <button className="icon-button" title="Refresh workspace" onClick={() => refresh().catch((cause) => setError(cause.message))}><RefreshCw size={16} /></button>
          <span className="avatar">CF</span>
        </div>
      </header>

      <div className="work-area">
        <aside className="sidebar">
          <div className="workspace-label"><FolderGit2 size={15} /><span>WORKSPACE</span><ChevronRight size={13} /></div>
          <div className="repo-card"><div className="repo-icon"><Layers3 size={16} /></div><div><strong>target_codebase</strong><small>Local synthetic repo</small></div><span className="branch-mark"><GitBranch size={13} /></span></div>
          <div className="side-section-label">SOURCE TREE</div>
          <div className="file-tree">
            <div className="tree-folder"><ChevronRight size={13} /> <span>src</span></div>
            <div className="tree-file active"><span className="python-mark">py</span>text_utils.py</div>
            <div className="tree-folder"><ChevronRight size={13} /> <span>tests</span></div>
            <div className="tree-file"><span className="python-mark">py</span>test_text_utils.py</div>
            <div className="tree-file"><span className="config-mark">≡</span>pytest.ini</div>
          </div>
          <div className="sidebar-bottom">
            <div className="side-section-label">RUN HEALTH</div>
            <div className="health-row"><CircleCheck size={15} /><span>Passing checks</span><strong>{passedRuns}</strong></div>
            <div className="health-row muted"><Activity size={15} /><span>Recorded actions</span><strong>{events.length}</strong></div>
            <div className="sandbox-badge"><Shield size={15} /><span>Sandbox policy active</span><span className="live-dot" /></div>
          </div>
        </aside>

        <main className="main-content" id="workspace">
          <div className="page-heading">
            <div>
              <div className="breadcrumbs">Foundry <ChevronRight size={13} /> Workspace</div>
              <h1>Agent workspace</h1>
              <p>Changes stay in review until you approve them.</p>
            </div>
            <div className="agent-status"><span className="agent-glyph"><Bot size={17} /></span><span><strong>Mock agent</strong><small>Deterministic · offline</small></span><span className="online-dot" /></div>
          </div>

          {error ? <div className="error-banner"><AlertTriangle size={16} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error">×</button></div> : null}

          <div className="overview-strip">
            <div><span className="metric-label">TASKS</span><strong>{tasks.length.toString().padStart(2, '0')}</strong></div>
            <div><span className="metric-label">AGENT RUNS</span><strong>{runs.length.toString().padStart(2, '0')}</strong></div>
            <div><span className="metric-label">LATEST STATUS</span><strong className="metric-status">{selectedRun?.status?.replaceAll('_', ' ') || 'Ready'}</strong></div>
            <div className="strip-accent"><span>RUN LOG</span><Activity size={18} /></div>
          </div>

          <div className="workspace-grid">
            <section className="left-column">
              <TaskForm onRun={handleRun} busy={busy} />
              <section className="panel history-panel">
                <div className="panel-title"><div><Activity size={16} /><h2>Run history</h2></div><span className="count-badge">{runs.length}</span></div>
                <RunHistory runs={runs} selectedId={selectedRun?.id} onSelect={setSelectedRun} />
              </section>
            </section>

            <section className="right-column">
              <div className="run-heading">
                <div><span className="eyebrow">{selectedRun ? `RUN #${String(selectedRun.id).padStart(3, '0')}` : 'NO RUN SELECTED'}</span><h2>{selectedRun ? tasks.find((task) => task.id === selectedRun.task_id)?.title || 'Agent proposal' : 'Review a proposed change'}</h2></div>
                {selectedRun ? <span className={`run-tag ${selectedRun.status}`}>{selectedRun.status.replaceAll('_', ' ')}</span> : null}
              </div>
              <DiffViewer diff={selectedRun?.diff || ''} />
              <ReviewGate run={selectedRun} onReview={handleReview} busy={busy} />
              <section className="panel activity-panel">
                <div className="panel-title"><div><Activity size={16} /><h2>Action history</h2></div><span className="history-caption">IMMUTABLE EVENT LOG</span></div>
                <EventTimeline events={events} />
              </section>
              {selectedRun?.self_review ? <section className="agent-note"><span className="agent-glyph small"><Bot size={14} /></span><div><strong>Agent self-review</strong><p>{selectedRun.self_review}</p></div></section> : null}
            </section>
          </div>
          <footer className="page-footer"><span><Shield size={13} /> Synthetic code only</span><span>CodePilot Foundry <b>0.1.0</b></span></footer>
        </main>
      </div>
    </div>
  );
}
