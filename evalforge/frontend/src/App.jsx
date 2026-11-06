import { Activity, ArrowDownToLine, ArrowRight, BadgeCheck, BarChart3, Bot, CircleAlert, Clock3, Gauge, GitCompareArrows, LoaderCircle, RefreshCw, ShieldCheck, Sparkles, Target, Workflow } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from './api.js';

const checkLabels = {
  task_success: 'Task success',
  regression_free: 'Regression-free',
  policy_compliance: 'Policy compliance',
  trace_complete: 'Trace completeness',
};

function ScoreRing({ score }) {
  return <div className="score-ring" style={{ '--score': `${score * 3.6}deg` }}><div><strong>{score}</strong><small>score</small></div></div>;
}

function MetricCard({ label, value, suffix, detail, icon: Icon, tone }) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-top"><span>{label}</span><Icon size={16} /></div>
      <strong className="metric-value">{value}<small>{suffix}</small></strong>
      <span className="metric-detail">{detail}</span>
    </article>
  );
}

export default function App() {
  const [runs, setRuns] = useState([]);
  const [evaluations, setEvaluations] = useState([]);
  const [metrics, setMetrics] = useState({ evaluations: 0, average_score: 0, pass_rate: 0, median_runtime_ms: null, checks: {} });
  const [scenarios, setScenarios] = useState([]);
  const [runId, setRunId] = useState('');
  const [scenarioId, setScenarioId] = useState('unicode-normalization');
  const [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function refresh() {
    const [nextRuns, nextEvaluations, nextMetrics, nextScenarios] = await Promise.all([
      api.runs(), api.evaluations(), api.metrics(), api.scenarios(),
    ]);
    setRuns(nextRuns);
    setEvaluations(nextEvaluations);
    setMetrics(nextMetrics);
    setScenarios(nextScenarios);
    if (!runId && nextRuns.length) setRunId(String(nextRuns[0].id));
    if (selected) {
      const refreshed = nextEvaluations.find((item) => item.id === selected.id);
      if (refreshed) setSelected(refreshed);
    }
  }

  useEffect(() => {
    refresh().catch((cause) => setError(cause.message));
  }, []);

  async function submitEvaluation(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await api.evaluate(runId, scenarioId);
      setSelected(result);
      await refresh();
    } catch (cause) {
      setError(cause.message);
    } finally {
      setBusy(false);
    }
  }

  const passingDimensions = Object.values(metrics.checks || {}).filter((value) => value === 100).length;
  const activeScenario = scenarios.find((scenario) => scenario.id === scenarioId);

  return (
    <div className="shell">
      <header className="topbar">
        <a className="wordmark" href="#overview"><span className="mark"><Workflow size={19} /></span><span>eval<span>forge</span></span></a>
        <div className="topbar-meta"><span className="source-indicator"><i /> CodePilot source connected</span><button className="icon-button" title="Refresh data" onClick={() => refresh().catch((cause) => setError(cause.message))}><RefreshCw size={16} /></button><span className="avatar">EF</span></div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <div className="sidebar-title">EVALUATION LAB</div>
          <a className="nav-item active" href="#overview"><BarChart3 size={16} /> Overview</a>
          <a className="nav-item" href="#history"><Activity size={16} /> Run evaluations <span>{evaluations.length}</span></a>
          <div className="side-divider" />
          <div className="sidebar-title">BENCHMARK</div>
          {scenarios.map((scenario) => <button key={scenario.id} className={`scenario-item ${scenarioId === scenario.id ? 'chosen' : ''}`} onClick={() => setScenarioId(scenario.id)}><Target size={15} /><span>{scenario.name}</span><ArrowRight size={13} /></button>)}
          <div className="sidebar-foot"><div className="connected-card"><span className="connected-icon"><Bot size={16} /></span><div><strong>CodePilot Foundry</strong><small>Run source · local</small></div><i /></div><div className="sidebar-caption">Synthetic task suite <span>v0.1</span></div></div>
        </aside>

        <main className="main" id="overview">
          <div className="heading-row">
            <div><div className="breadcrumbs">EvalForge <ArrowRight size={12} /> Evaluation overview</div><h1>Agent quality, measured.</h1><p>Replay CodePilot runs against a deterministic synthetic benchmark.</p></div>
            <div className="heading-badge"><Sparkles size={14} /> BENCHMARK MODE</div>
          </div>

          {error ? <div className="error-banner"><CircleAlert size={16} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss">×</button></div> : null}

          <section className="metric-grid" aria-label="Aggregate evaluation metrics">
            <MetricCard label="Evaluations" value={String(metrics.evaluations).padStart(2, '0')} suffix="" detail={`${passingDimensions}/4 quality dimensions at 100%`} icon={BarChart3} tone="mint" />
            <MetricCard label="Average score" value={metrics.average_score} suffix="%" detail="Weighted benchmark score" icon={Gauge} tone="white" />
            <MetricCard label="Pass rate" value={metrics.pass_rate} suffix="%" detail="Runs passing all dimensions" icon={BadgeCheck} tone="peach" />
            <MetricCard label="Median runtime" value={metrics.median_runtime_ms == null ? '—' : (metrics.median_runtime_ms / 1000).toFixed(1)} suffix={metrics.median_runtime_ms == null ? '' : 's'} detail="Recorded start to completion" icon={Clock3} tone="white" />
          </section>

          <section className="evaluate-bar">
            <div className="evaluate-intro"><span className="evaluate-icon"><GitCompareArrows size={17} /></span><div><strong>Evaluate a CodePilot run</strong><small>{activeScenario?.description || 'Select a deterministic benchmark.'} Probe variants only change an in-memory copy.</small></div></div>
            <form className="evaluate-form" onSubmit={submitEvaluation}>
              <label className="select-wrap"><span>RUN</span><select aria-label="CodePilot run" value={runId} onChange={(event) => setRunId(event.target.value)} required><option value="" disabled>Select run</option>{runs.map((run) => <option key={run.id} value={run.id}>Run #{String(run.id).padStart(3, '0')} · {run.provider} · {run.status.replaceAll('_', ' ')}</option>)}</select></label>
              <button className="evaluate-button" type="submit" disabled={busy || !runId}>{busy ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}{busy ? 'Scoring…' : 'Evaluate run'}</button>
            </form>
          </section>

          <div className="content-grid">
            <section className="panel history-panel" id="history">
              <div className="panel-head"><div><span className="section-index">01</span><h2>Recent evaluations</h2></div><span className="table-count">{evaluations.length} total</span></div>
              {evaluations.length ? <div className="evaluation-table"><div className="table-labels"><span>RUN / SCENARIO</span><span>SCORE</span><span>RESULT</span><span>RUNTIME</span></div>{evaluations.map((evaluation) => <button className={`evaluation-row ${selected?.id === evaluation.id ? 'selected' : ''}`} key={evaluation.id} onClick={() => setSelected(evaluation)}><span className="run-name"><strong>Run #{String(evaluation.source_run_id).padStart(3, '0')}</strong><small>{evaluation.scenario_name}</small></span><strong className="row-score">{evaluation.score}<small>%</small></strong><span className={`outcome ${evaluation.outcome}`}>{evaluation.outcome === 'pass' ? <BadgeCheck size={13} /> : <CircleAlert size={13} />}{evaluation.outcome === 'pass' ? 'Pass' : 'Review'}</span><span className="runtime-cell">{evaluation.runtime_ms == null ? '—' : `${(evaluation.runtime_ms / 1000).toFixed(1)}s`}</span></button>)}</div> : <div className="empty-history"><span><ArrowDownToLine size={17} /></span><strong>No evaluations yet</strong><p>Choose a saved CodePilot run above to create the first benchmark result.</p></div>}
            </section>

            <section className="panel detail-panel">
              <div className="panel-head"><div><span className="section-index">02</span><h2>Score breakdown</h2></div>{selected ? <span className={`outcome ${selected.outcome}`}>{selected.outcome === 'pass' ? 'PASS' : 'REVIEW'}</span> : null}</div>
              {selected ? <div className="score-detail">
                <div className="score-hero"><ScoreRing score={selected.score} /><div><span className="scenario-label">{selected.scenario_name}</span><strong>Run #{String(selected.source_run_id).padStart(3, '0')}</strong><small>{selected.probe_type === 'baseline' ? 'Recorded run data' : 'Generated probe · source run unchanged'}</small><small>{selected.event_count} recorded events · {selected.runtime_ms == null ? 'runtime unavailable' : `${(selected.runtime_ms / 1000).toFixed(2)}s elapsed`}</small></div></div>
                <div className="dimension-list">{Object.entries(selected.checks).map(([name, check]) => <div className="dimension" key={name}><div className="dimension-label"><span>{checkLabels[name]}</span><strong>{check.passed ? 'Pass' : 'Needs work'}</strong></div><div className="dimension-track"><span className={check.passed ? 'passed' : 'failed'} style={{ width: `${check.passed ? 100 : 0}%` }} /></div><small>Weight {Math.round(check.weight * 100)}%</small></div>)}</div>
              </div> : <div className="empty-detail"><span className="empty-mark"><GitCompareArrows size={20} /></span><strong>Select an evaluation</strong><p>Results include correctness, regression, policy, and trace checks.</p></div>}
            </section>
          </div>
          <footer className="footer"><span><ShieldCheck size={13} /> Synthetic data only</span><span>EvalForge <b>0.1.0</b> <i /> CodePilot event contract</span></footer>
        </main>
      </div>
    </div>
  );
}
