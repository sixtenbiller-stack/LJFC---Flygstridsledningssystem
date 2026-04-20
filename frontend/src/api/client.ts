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

  // Threat Groups & Responses
  getGroups: () => request<any[]>('/groups'),

  getGroupResponses: (groupId: string) =>
    request<any[]>(`/groups/${groupId}/responses`),

  getDecisionCard: (groupId: string) =>
    request<any>(`/groups/${groupId}/decision-card`),

  approveGroupResponse: (groupId: string, responseId: string, action = 'approve', overrideReason = '') =>
    request<any>(`/groups/${groupId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ response_id: responseId, action, override_reason: overrideReason }),
    }),

  getAfterAction: () => request<any[]>('/after-action'),

  // Scenario Registry & Runtime
  getScenarios: () => request<any>('/scenarios'),

  getScenarioMode: () => request<any>('/scenario/mode'),

  getSession: () => request<any>('/scenario/session'),

  getMarkers: () => request<any[]>('/scenario/markers'),

  jumpTo: (target: string) =>
    request<any>('/scenario/jump', {
      method: 'POST',
      body: JSON.stringify({ target }),
    }),

  seekTo: (time_s: number) =>
    request<any>('/scenario/seek', {
      method: 'POST',
      body: JSON.stringify({ time_s }),
    }),

  generateScenario: (template: string, seed?: number, duration_s?: number) =>
    request<any>('/scenario/generate', {
      method: 'POST',
      body: JSON.stringify({ template, seed, duration_s }),
    }),

  startLiveSession: (fileId: string, seed?: number) =>
    request<any>('/scenario/live/start', {
      method: 'POST',
      body: JSON.stringify({ file_id: fileId, seed }),
    }),

  liveControl: (action: string, speed?: number) =>
    request<any>('/scenario/live/control', {
      method: 'POST',
      body: JSON.stringify({ action, speed, value: speed }),
    }),

  liveTick: (dtS = 5) =>
    request<any>('/scenario/live/tick', {
      method: 'POST',
      body: JSON.stringify({ dt_s: dtS }),
    }),

  liveInject: (type: string, params?: Record<string, unknown>) =>
    request<any>('/scenario/live/inject', {
      method: 'POST',
      body: JSON.stringify({ type, params }),
    }),

  getLiveState: () => request<any>('/scenario/live/state'),
};
