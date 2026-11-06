const API_ROOT = import.meta.env.VITE_API_URL || '';

async function request(path, options = {}) {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

export const api = {
  tasks: () => request('/api/tasks'),
  createTask: (task) => request('/api/tasks', { method: 'POST', body: JSON.stringify(task) }),
  runs: () => request('/api/runs'),
  run: (taskId) => request('/api/runs', { method: 'POST', body: JSON.stringify({ task_id: taskId }) }),
  events: (runId) => request(`/api/runs/${runId}/events`),
  review: (runId, decision, note = '') => request(`/api/reviews/${runId}`, {
    method: 'POST', body: JSON.stringify({ decision, note }),
  }),
};
