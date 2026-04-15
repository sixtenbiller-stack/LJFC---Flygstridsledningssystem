/** Visible command catalog for ribbon + autocomplete — grouped by intent */

export type CommandCategory =
  | 'Situation'
  | 'Threats'
  | 'Planning'
  | 'Compare / Explain'
  | 'Simulation'
  | 'Policy / Constraints'
  | 'Focus / Navigation'
  | 'Decision / Audit'
  | 'Help';

export interface CommandDef {
  cmd: string;
  label: string;
  category: CommandCategory;
}

export const ALL_COMMANDS: CommandDef[] = [
  { cmd: '/brief', label: 'Commander brief', category: 'Situation' },
  { cmd: '/summary', label: 'Situation summary', category: 'Situation' },
  { cmd: '/what-changed', label: 'What changed', category: 'Situation' },
  { cmd: '/top-threats', label: 'Top threats', category: 'Threats' },
  { cmd: '/show-readiness', label: 'Readiness', category: 'Situation' },
  { cmd: '/focus trk-h01', label: 'Focus track', category: 'Threats' },
  { cmd: '/most-dangerous', label: 'Most dangerous', category: 'Threats' },
  { cmd: '/generate-coas', label: 'Generate COAs', category: 'Planning' },
  { cmd: '/recommend', label: 'Recommend', category: 'Planning' },
  { cmd: '/replan', label: 'Re-plan', category: 'Planning' },
  { cmd: '/compare top2', label: 'Compare top 2', category: 'Compare / Explain' },
  { cmd: '/why top', label: 'Why top plan', category: 'Compare / Explain' },
  { cmd: '/simulate top', label: 'Simulate top', category: 'Simulation' },
  { cmd: '/simulate coa-1', label: 'Simulate COA', category: 'Simulation' },
  { cmd: '/policy protect_capital_first', label: 'Policy', category: 'Policy / Constraints' },
  { cmd: '/reserve 2', label: 'Reserve pairs', category: 'Policy / Constraints' },
  { cmd: '/focus arktholm', label: 'Focus Arktholm', category: 'Focus / Navigation' },
  { cmd: '/fit-theater', label: 'Fit map', category: 'Focus / Navigation' },
  { cmd: '/follow top-threat', label: 'Follow threat', category: 'Focus / Navigation' },
  { cmd: '/approve coa-1', label: 'Approve (use button)', category: 'Decision / Audit' },
  { cmd: '/decision-log', label: 'Decision log', category: 'Decision / Audit' },
  { cmd: '/state-id', label: 'Snapshot ID', category: 'Decision / Audit' },
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
