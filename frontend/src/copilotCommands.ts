/** Visible command catalog for ribbon + autocomplete — grouped by intent */

export type CommandCategory =
  | 'Situation'
  | 'Threats'
  | 'Groups'
  | 'Responses'
  | 'Planning'
  | 'Compare / Explain'
  | 'Simulation'
  | 'Authority / Policy'
  | 'Focus / Navigation'
  | 'Decision / Audit'
  | 'Help';

export interface CommandDef {
  cmd: string;
  label: string;
  category: CommandCategory;
}

export const ALL_COMMANDS: CommandDef[] = [
  // Situation
  { cmd: '/brief', label: 'Commander brief', category: 'Situation' },
  { cmd: '/summary', label: 'Situation summary', category: 'Situation' },
  { cmd: '/what-changed', label: 'What changed', category: 'Situation' },
  { cmd: '/show-readiness', label: 'Readiness', category: 'Situation' },

  // Threats (per-track)
  { cmd: '/top-threats', label: 'Top threats', category: 'Threats' },
  { cmd: '/most-dangerous', label: 'Most dangerous track', category: 'Threats' },
  { cmd: '/focus trk-h01', label: 'Focus track', category: 'Threats' },

  // Groups
  { cmd: '/groups', label: 'List threat groups', category: 'Groups' },
  { cmd: '/group top', label: 'Top group detail', category: 'Groups' },
  { cmd: '/most-dangerous-group', label: 'Most dangerous group', category: 'Groups' },
  { cmd: '/assess top', label: 'Assess top group', category: 'Groups' },
  { cmd: '/why-group top', label: 'Why this classification?', category: 'Groups' },
  { cmd: '/uncertainty top', label: 'Uncertainty flags', category: 'Groups' },

  // Responses
  { cmd: '/responses top', label: 'Response options', category: 'Responses' },
  { cmd: '/why-response top', label: 'Why top response?', category: 'Responses' },
  { cmd: '/compare-responses top', label: 'Compare responses', category: 'Responses' },

  // Planning
  { cmd: '/generate-coas', label: 'Generate COAs', category: 'Planning' },
  { cmd: '/generate-detailed-coas top', label: 'Detailed COAs for group', category: 'Planning' },
  { cmd: '/recommend', label: 'Recommend', category: 'Planning' },
  { cmd: '/replan', label: 'Re-plan', category: 'Planning' },
  { cmd: '/ato', label: 'Synthetic ATO / mission', category: 'Planning' },
  { cmd: '/mission', label: 'Mission constraints', category: 'Planning' },
  { cmd: '/constraints', label: 'Constraints', category: 'Planning' },
  { cmd: '/intent', label: 'Commander intent', category: 'Planning' },

  // Compare / Explain
  { cmd: '/compare top2', label: 'Compare top 2 COAs', category: 'Compare / Explain' },
  { cmd: '/why top', label: 'Why top plan?', category: 'Compare / Explain' },

  // Simulation
  { cmd: '/simulate top', label: 'Simulate top COA', category: 'Simulation' },
  { cmd: '/simulate-response top', label: 'Simulate top response', category: 'Simulation' },

  // Authority / Policy
  { cmd: '/authority top', label: 'Authority check', category: 'Authority / Policy' },
  { cmd: '/policy protect_capital_first', label: 'Policy', category: 'Authority / Policy' },
  { cmd: '/reserve 2', label: 'Reserve pairs', category: 'Authority / Policy' },
  { cmd: '/approval', label: 'Approval authority (ATO)', category: 'Authority / Policy' },

  // Scenario / Mode
  { cmd: '/scenario', label: 'Active scenario info', category: 'Situation' },
  { cmd: '/mode', label: 'Current mode', category: 'Situation' },
  { cmd: '/live-status', label: 'Live session status', category: 'Situation' },
  { cmd: '/mutations', label: 'Live mutation log', category: 'Situation' },

  // Focus / Navigation
  { cmd: '/jump first-contact', label: 'Jump first contact', category: 'Focus / Navigation' },
  { cmd: '/jump first-group', label: 'Jump first group', category: 'Focus / Navigation' },
  { cmd: '/jump first-decision', label: 'Jump first decision', category: 'Focus / Navigation' },
  { cmd: '/jump second-wave', label: 'Jump second wave', category: 'Focus / Navigation' },
  { cmd: '/focus arktholm', label: 'Focus Arktholm', category: 'Focus / Navigation' },
  { cmd: '/fit-theater', label: 'Fit map', category: 'Focus / Navigation' },
  { cmd: '/follow top-threat', label: 'Follow threat', category: 'Focus / Navigation' },

  // Decision / Audit
  { cmd: '/approve top', label: 'Approve (use button)', category: 'Decision / Audit' },
  { cmd: '/defer top', label: 'Defer decision', category: 'Decision / Audit' },
  { cmd: '/override top', label: 'Override with reason', category: 'Decision / Audit' },
  { cmd: '/decision-log', label: 'Decision log', category: 'Decision / Audit' },
  { cmd: '/after-action', label: 'After-action log', category: 'Decision / Audit' },
  { cmd: '/state-id', label: 'Snapshot ID', category: 'Decision / Audit' },

  // Help
  { cmd: '/help', label: 'Help', category: 'Help' },
  { cmd: '/commands', label: 'All commands', category: 'Help' },
];

export function filterCommands(query: string): CommandDef[] {
  const q = query.slice(1).toLowerCase();
  if (!q) return ALL_COMMANDS;
  return ALL_COMMANDS.filter(
    c => c.cmd.toLowerCase().includes(q) || c.label.toLowerCase().includes(q),
  ).slice(0, 24);
}
