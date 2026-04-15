const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  getState: (includeGeo = false) =>
    request<any>(`/state?include_geo=${includeGeo}`),

  getAlerts: () => request<any[]>('/alerts'),

  getCoas: () => request<any>('/coas'),

  getDecisions: () => request<any[]>('/decisions'),

  loadScenario: (scenarioId = 'scenario-alpha') =>
    request<any>('/scenario/load', {
      method: 'POST',
      body: JSON.stringify({ scenario_id: scenarioId }),
    }),

  control: (action: string, speed?: number) =>
    request<any>('/scenario/control', {
      method: 'POST',
      body: JSON.stringify({ action, speed }),
    }),

  generateCoas: (wave?: number) =>
    request<any>('/agent/coas', {
      method: 'POST',
      body: JSON.stringify({ wave }),
    }),

  explain: (coaId: string, question = 'Why is this ranked first?') =>
    request<any>('/agent/explain', {
      method: 'POST',
      body: JSON.stringify({ coa_id: coaId, question }),
    }),

  simulate: (coaId: string, seed = 42) =>
    request<any>('/agent/simulate', {
      method: 'POST',
      body: JSON.stringify({ coa_id: coaId, seed }),
    }),

  approve: (coaId: string, note = '') =>
    request<any>('/decision/approve', {
      method: 'POST',
      body: JSON.stringify({ coa_id: coaId, operator_note: note }),
    }),

  getFeed: (sinceId?: string) =>
    request<any[]>(`/copilot/feed${sinceId ? `?since_id=${sinceId}` : ''}`),

  sendCommand: (input: string, sourceStateId?: string) =>
    request<any>('/copilot/command', {
      method: 'POST',
      body: JSON.stringify({ input, source_state_id: sourceStateId }),
    }),

  getCopilotStatus: () => request<any>('/copilot/status'),
};
