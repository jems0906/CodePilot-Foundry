async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`);
  return body;
}

export const api = {
  runs: () => request('/api/source-runs'),
  evaluations: () => request('/api/evaluations'),
  metrics: () => request('/api/metrics'),
  scenarios: () => request('/api/scenarios'),
  evaluate: (runId, scenarioId) => request('/api/evaluations', {
    method: 'POST', body: JSON.stringify({ run_id: Number(runId), scenario_id: scenarioId }),
  }),
};
