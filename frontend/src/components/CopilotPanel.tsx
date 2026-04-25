import { useState, useRef, useEffect, useMemo } from 'react';
import type {
  ScenarioState, CourseOfAction, ExplanationData, SimulationResult,
  AuditRecord, FeedItem, CopilotResponse, ThreatAlert, ThreatGroup,
  DecisionCard as DecisionCardType,
} from '../types';
import { ALL_COMMANDS, type CommandDef } from '../copilotCommands';
import './CopilotPanel.css';

interface Props {
  state: ScenarioState;
  coas: CourseOfAction[];
  coaWave: number;
  explanation: ExplanationData | null;
  simResult: SimulationResult | null;
  decisions: AuditRecord[];
  loading: string;
  feedItems: FeedItem[];
  copilotStatus: { provider: string; model: string } | null;
  alerts: ThreatAlert[];
  selectedTrack: string | null;
  groups?: ThreatGroup[];
  selectedGroup?: string | null;
  decisionCard?: DecisionCardType | null;
  scenarioMode?: string;
  scenarioOrigin?: string;
  onGenerateCoas: () => void;
  onExplain: (coaId: string) => void;
  onSimulate: (coaId: string) => void;
  onApprove: (coaId: string) => void;
  onSendCommand: (input: string) => Promise<CopilotResponse | null>;
}

function ribbonCommands(args: {
  alertCount: number;
  coaCount: number;
  wave: number;
  decisionCount: number;
}): Array<{ cmd: string; label: string }> {
  const { alertCount, coaCount, wave, decisionCount } = args;
  if (alertCount === 0) {
    return [
      { cmd: '/brief', label: 'Brief' },
      { cmd: '/summary', label: 'Summary' },
      { cmd: '/commands', label: 'Commands' },
    ];
  }
  if (decisionCount > 0 && coaCount > 0) {
    return [
      { cmd: '/decision-log', label: 'Decision log' },
      { cmd: '/brief', label: 'Brief' },
      { cmd: '/state-id', label: 'State ID' },
      { cmd: '/simulate top', label: 'Simulate' },
    ];
  }
  if (wave >= 2 && coaCount > 0) {
    return [
      { cmd: '/what-changed', label: 'What changed' },
      { cmd: '/replan', label: 'Replan' },
      { cmd: '/recommend', label: 'Recommend' },
      { cmd: '/simulate top', label: 'Simulate' },
    ];
  }
  if (coaCount > 0) {
    return [
      { cmd: '/compare top2', label: 'Compare' },
      { cmd: '/why top', label: 'Why top' },
      { cmd: '/simulate top', label: 'Simulate' },
      { cmd: '/show-readiness', label: 'Readiness' },
    ];
  }
  return [
    { cmd: '/top-threats', label: 'Top threats' },
    { cmd: '/most-dangerous', label: 'Most dangerous' },
    { cmd: '/generate-coas', label: 'Generate COAs' },
    { cmd: '/brief', label: 'Brief' },
  ];
}

type View = 'feed' | 'plans' | 'compare' | 'explain' | 'simulate' | 'audit';

export function CopilotPanel({
  state, coas, coaWave, explanation, simResult, decisions, loading,
  feedItems, copilotStatus, alerts, selectedTrack,
  groups = [], selectedGroup, decisionCard, scenarioMode, scenarioOrigin,
  onGenerateCoas, onExplain, onSimulate, onApprove, onSendCommand,
}: Props) {
  const [view, setView] = useState<View>('feed');
  const [compareIds, setCompareIds] = useState<[string, string] | null>(null);
  const [selectedCoa, setSelectedCoa] = useState<string | null>(null);
  const [inputText, setInputText] = useState('');
  const [commandLoading, setCommandLoading] = useState(false);
  const [commandResponse, setCommandResponse] = useState<CopilotResponse | null>(null);
  const [quickActions, setQuickActions] = useState<string[]>([]);
  const [slashHighlight, setSlashHighlight] = useState(0);
  const [inputFocused, setInputFocused] = useState(false);
  const feedEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const topThreat = alerts[0];
  const topCoa = coas[0];
  const ribbon = useMemo(
    () => ribbonCommands({
      alertCount: alerts.length,
      coaCount: coas.length,
      wave: state.wave,
      decisionCount: decisions.length,
    }),
    [alerts.length, coas.length, state.wave, decisions.length],
  );

  const mergedSlashCommands = useMemo((): CommandDef[] => {
    const dyn: CommandDef[] = [];
    if (topThreat) {
      dyn.push({ cmd: `/focus ${topThreat.track_id}`, label: 'Focus top track', category: 'Threats' });
    }
    if (selectedTrack) {
      dyn.push({ cmd: `/focus ${selectedTrack}`, label: 'Focus selected track', category: 'Focus / Navigation' });
    }
    if (topCoa) {
      dyn.push(
        { cmd: `/why ${topCoa.coa_id}`, label: 'Why this COA', category: 'Compare / Explain' },
        { cmd: `/simulate ${topCoa.coa_id}`, label: 'Simulate this COA', category: 'Simulation' },
      );
    }
    const seen = new Set<string>();
    const out: CommandDef[] = [];
    for (const c of [...dyn, ...ALL_COMMANDS]) {
      if (seen.has(c.cmd)) continue;
      seen.add(c.cmd);
      out.push(c);
    }
    return out;
  }, [topThreat, selectedTrack, topCoa]);

  const filteredSlash = useMemo(() => {
    if (!inputText.startsWith('/')) return [];
    const q = inputText.slice(1).toLowerCase();
    if (!q) return mergedSlashCommands.slice(0, 48);
    return mergedSlashCommands.filter(
      c => c.cmd.toLowerCase().includes(q) || c.label.toLowerCase().includes(q),
    ).slice(0, 48);
  }, [inputText, mergedSlashCommands]);

  const slashMenuOpen = inputFocused && inputText.startsWith('/') && filteredSlash.length > 0;

  useEffect(() => {
    setSlashHighlight(0);
  }, [inputText, filteredSlash.length]);

  useEffect(() => {
    if (view === 'feed' && feedEndRef.current) {
      feedEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [feedItems.length, view]);

  useEffect(() => {
    if (feedItems.length > 0) {
      const latest = feedItems[feedItems.length - 1];
      if (latest.suggested_actions.length > 0) {
        setQuickActions(latest.suggested_actions);
      }
    }
  }, [feedItems]);

  const handleGenerate = () => {
    onGenerateCoas();
    setView('plans');
    setSelectedCoa(null);
    setCommandResponse(null);
  };

  const handleCompare = () => {
    if (coas.length >= 2) {
      setCompareIds([coas[0].coa_id, coas[1].coa_id]);
      setView('compare');
    }
  };

  const handleExplain = (coaId: string) => {
    onExplain(coaId);
    setView('explain');
  };

  const handleSimulate = (coaId: string) => {
    onSimulate(coaId);
    setView('simulate');
  };

  const handleApprove = (coaId: string) => {
    onApprove(coaId);
    setView('audit');
  };

  const [localUserMessages, setLocalUserMessages] = useState<FeedItem[]>([]);

  const handleSendCommand = async (text?: string) => {
    const cmd = text || inputText.trim();
    if (!cmd) return;
    setCommandLoading(true);
    setInputText('');
    
    // Optimistically add user command to local feed for immediate feedback
    const userMsg: FeedItem = {
      id: `local-${Date.now()}`,
      timestamp: new Date().toISOString(),
      category: 'operator_command',
      severity: 'info',
      title: '',
      body: cmd,
      related_ids: [] as string[],
      suggested_actions: [] as string[],
      source_state_id: state.source_state_id || 'local'
    };
    setLocalUserMessages(prev => [...prev, userMsg]);

    try {
      const resp = await onSendCommand(cmd);
      if (resp) {
        setCommandResponse(resp);
        if (resp.suggested_actions?.length) {
          setQuickActions(resp.suggested_actions);
        }
        if (resp.type === 'coas') {
          setView('plans');
        }
      }
    } finally {
      setCommandLoading(false);
    }
  };

  const pickSlashCommand = (cmd: string) => {
    setInputText(`${cmd} `);
    setSlashHighlight(0);
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (slashMenuOpen) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSlashHighlight(i => Math.min(i + 1, filteredSlash.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSlashHighlight(i => Math.max(i - 1, 0));
        return;
      }
      if (e.key === 'Enter' && !e.shiftKey && filteredSlash[slashHighlight]) {
        e.preventDefault();
        void handleSendCommand(filteredSlash[slashHighlight].cmd);
        return;
      }
      if (e.key === 'Tab' && filteredSlash[slashHighlight]) {
        e.preventDefault();
        pickSlashCommand(filteredSlash[slashHighlight].cmd);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setInputText('');
        return;
      }
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSendCommand();
    }
  };

  const handleQuickAction = (action: string) => {
    const cmdMap: Record<string, string> = {
      'Generate COAs': '/generate-coas',
      'Re-plan': '/replan',
      'Compare top 2': '/compare top2',
      'Why this plan?': '/why top',
      'Simulate top plan': '/simulate top',
      'Approve selected plan': '/approve',
    };
    const cmd = cmdMap[action] || action;
    void handleSendCommand(cmd);
  };

  return (
    <div className="copilot-panel">

      <div className="copilot-sticky" aria-label="Situation summary">
        <div className="copilot-sticky-row">
          <div className="copilot-sticky-cell">
            <span className="csk-label">Scenario</span>
            <span className="csk-value">{state.scenario_name}</span>
          </div>
          <div className="copilot-sticky-cell">
            <span className="csk-label">Top threat</span>
            <span className="csk-value">{topThreat?.track_id ?? '—'}</span>
          </div>
          <div className="copilot-sticky-cell">
            <span className="csk-label">Top recommendation</span>
            <span className="csk-value">{topCoa?.title ?? '—'}</span>
          </div>
        </div>
      </div>

      <div className="copilot-content">
        <FeedView
          items={feedItems}
          localItems={localUserMessages}
          commandResponse={commandResponse}
          feedEndRef={feedEndRef}
        />
        
        {/* We keep the visibility of other views if needed by internal state, 
            but the user requested to remove everything below except the send message window.
            However, usually we want to see the feed by default now. */}
      </div>

      {/* Feed / backend suggested quick actions */}
      {quickActions.length > 0 && (
        <div className="quick-actions">
          {quickActions.map((action, i) => (
            <button
              key={i}
              type="button"
              className="quick-action-chip"
              onClick={() => handleQuickAction(action)}
              disabled={commandLoading}
            >
              {action}
            </button>
          ))}
        </div>
      )}

      <div className="copilot-command-ribbon" aria-label="Context commands">
        <span className="cc-ribbon-label">Quick</span>
        <div className="cc-ribbon-chips">
          {ribbon.map(r => (
            <button
              key={r.cmd}
              type="button"
              className="cc-ribbon-chip"
              onClick={() => void handleSendCommand(r.cmd)}
              disabled={commandLoading}
              title={r.cmd}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Command input + slash autocomplete */}
      <div className="copilot-input-wrap">
        <div className="copilot-input-area">
          <input
            ref={inputRef}
            type="text"
            className="copilot-input"
            placeholder={commandLoading ? 'Processing...' : 'Ask or command...'}
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setInputFocused(true)}
            onBlur={() => {
              window.setTimeout(() => setInputFocused(false), 180);
            }}
            disabled={commandLoading}
            autoComplete="off"
            spellCheck={false}
            aria-expanded={slashMenuOpen}
            aria-controls="slash-suggest"
          />
          <button
            type="button"
            className="copilot-send-btn"
            onClick={() => void handleSendCommand()}
            disabled={commandLoading || !inputText.trim()}
          >
            <span className="arrow">↑</span>
          </button>
        </div>

        {slashMenuOpen && (
          <div id="slash-suggest" className="slash-suggest" role="listbox">
            {filteredSlash.map((c, i) => (
              <div key={c.cmd}>
                {(i === 0 || filteredSlash[i - 1].category !== c.category) && (
                  <div className="slash-cat" role="presentation">
                    {c.category}
                  </div>
                )}
                <button
                  type="button"
                  role="option"
                  aria-selected={i === slashHighlight}
                  className={`slash-row ${i === slashHighlight ? 'active' : ''}`}
                  onMouseDown={e => {
                    e.preventDefault();
                    void handleSendCommand(c.cmd);
                  }}
                  onMouseEnter={() => setSlashHighlight(i)}
                >
                  <span className="slash-cmd">{c.cmd}</span>
                  <span className="slash-hint">{c.label}</span>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function FeedView({
  items, localItems, commandResponse, feedEndRef,
}: {
  items: FeedItem[];
  localItems: FeedItem[];
  commandResponse: CopilotResponse | null;
  feedEndRef: React.RefObject<HTMLDivElement | null>;
}) {
  // Merge and sort items by timestamp
  const allItems = useMemo(() => {
    const combined = [...items, ...localItems];
    // Deduplicate if a local message was eventually received via polling
    const seenBodies = new Set<string>();
    const filtered = combined.filter(it => {
      if (it.category !== 'operator_command') return true;
      const key = `${it.body}-${new Date(it.timestamp).setSeconds(0,0)}`;
      if (seenBodies.has(key)) return false;
      seenBodies.add(key);
      return true;
    });
    return filtered.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  }, [items, localItems]);

  if (allItems.length === 0 && !commandResponse) {
    return (
      <div className="copilot-hint">
        Chief of Staff is monitoring the scenario. Updates will appear here when something material changes.
        <div className="copilot-hint-sub">
          Try <span className="copilot-hint-cmd">/brief</span>, <span className="copilot-hint-cmd">/commands</span>, or the Quick ribbon below. Start playback to populate threats.
        </div>
      </div>
    );
  }

  return (
    <div className="feed-view">
      {commandResponse && (
        <div className="feed-item command-response role-copilot">
          <div className="feed-body">{commandResponse.message}</div>
        </div>
      )}

      {allItems.map(item => {
        const isUser = item.category === 'operator_command';
        return (
          <div key={item.id} className={`feed-item severity-${item.severity} role-${isUser ? 'user' : 'system'}`}>
            {!isUser && (
              <div className="feed-item-header">
                <span className={`feed-severity ${item.severity}`}>{item.severity === 'critical' ? '●' : item.severity === 'warning' ? '▲' : '◆'}</span>
                <span className="feed-category">{item.category.replace(/_/g, ' ')}</span>
                <span className="feed-time">{new Date(item.timestamp).toLocaleTimeString()}</span>
              </div>
            )}
            {!isUser && item.title && <div className="feed-title">{item.title}</div>}
            <div className="feed-body">{item.body}</div>
            {!isUser && item.related_ids.length > 0 && (
              <div className="feed-related">
                {item.related_ids.map(id => (
                  <span key={id} className="feed-tag">{id}</span>
                ))}
              </div>
            )}
          </div>
        );
      })}

      <div ref={feedEndRef} />
    </div>
  );
}

function CoaCard({
  coa, isSelected, onSelect, onExplain, onSimulate, onApprove, loading,
}: {
  coa: CourseOfAction;
  isSelected: boolean;
  onSelect: () => void;
  onExplain: () => void;
  onSimulate: () => void;
  onApprove: () => void;
  loading: string;
}) {
  const riskClass = coa.risk_level === 'high' ? 'risk-high'
    : coa.risk_level === 'low' ? 'risk-low' : 'risk-medium';

  return (
    <div className={`coa-card ${isSelected ? 'expanded' : ''}`} onClick={onSelect}>
      <div className="coa-rank">#{coa.rank}</div>
      <div className="coa-title">{coa.title}</div>
      <div className="coa-summary">{coa.summary}</div>

      <div className="coa-metrics">
        <div className="coa-metric">
          <span className="metric-label">Readiness Cost</span>
          <span className="metric-value">{coa.readiness_cost_pct.toFixed(1)}%</span>
        </div>
        <div className="coa-metric">
          <span className="metric-label">Risk</span>
          <span className={`metric-value ${riskClass}`}>{coa.risk_level}</span>
        </div>
        <div className="coa-metric">
          <span className="metric-label">Assets</span>
          <span className="metric-value">{coa.actions.length}</span>
        </div>
      </div>

      {isSelected && (
        <div className="coa-expanded" onClick={(e) => e.stopPropagation()}>
          <div className="coa-section">
            <div className="section-label">Reserve Posture</div>
            <div className="section-text">{coa.reserve_posture}</div>
          </div>
          <div className="coa-section">
            <div className="section-label">Expected Outcome</div>
            <div className="section-text">{coa.estimated_outcome}</div>
          </div>
          <div className="coa-section">
            <div className="section-label">Actions</div>
            {coa.actions.map((a, i) => (
              <div key={i} className="coa-action">
                <span className="action-asset">{a.asset_id}</span>
                <span className="action-type">{a.action_type}</span>
                {a.target_track_ids.length > 0 && (
                  <span className="action-targets">→ {a.target_track_ids.join(', ')}</span>
                )}
              </div>
            ))}
          </div>
          <div className="coa-section">
            <div className="section-label">Assumptions</div>
            <ul className="assumptions-list">
              {coa.assumptions.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          </div>
          {coa.source_state_id && (
            <div className="coa-lineage">Snapshot: {coa.source_state_id}</div>
          )}
          <div className="coa-actions-bar">
            <button onClick={onExplain} disabled={loading === 'explain'}>
              {loading === 'explain' ? '...' : 'Why?'}
            </button>
            <button onClick={onSimulate} disabled={loading === 'simulate'}>
              {loading === 'simulate' ? '...' : 'Simulate'}
            </button>
            <button className="primary" onClick={onApprove} disabled={loading === 'approve'}>
              {loading === 'approve' ? '...' : 'Approve'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function CompareView({ coas, ids }: { coas: CourseOfAction[]; ids: [string, string] }) {
  const [a, b] = ids.map(id => coas.find(c => c.coa_id === id)!).filter(Boolean);
  if (!a || !b) return <div className="copilot-hint">Select two COAs to compare.</div>;

  const fields: Array<{ label: string; getA: string; getB: string }> = [
    { label: 'Readiness Cost', getA: `${a.readiness_cost_pct}%`, getB: `${b.readiness_cost_pct}%` },
    { label: 'Risk Level', getA: a.risk_level, getB: b.risk_level },
    { label: 'Assets Committed', getA: `${a.actions.length}`, getB: `${b.actions.length}` },
    { label: 'Protected', getA: a.protected_objectives.join(', '), getB: b.protected_objectives.join(', ') },
  ];

  return (
    <div className="compare-view">
      <div className="compare-header">
        <div className="compare-col-header">{a.title}</div>
        <div className="compare-col-header">{b.title}</div>
      </div>
      {fields.map(f => (
        <div key={f.label} className="compare-row">
          <div className="compare-label">{f.label}</div>
          <div className="compare-val">{f.getA}</div>
          <div className="compare-val">{f.getB}</div>
        </div>
      ))}
      <div className="compare-section">
        <div className="compare-section-title">Reserve Posture</div>
        <div className="compare-two-col">
          <div className="compare-text">{a.reserve_posture}</div>
          <div className="compare-text">{b.reserve_posture}</div>
        </div>
      </div>
      <div className="compare-section">
        <div className="compare-section-title">Rationale</div>
        <div className="compare-two-col">
          <div className="compare-text">{a.rationale}</div>
          <div className="compare-text">{b.rationale}</div>
        </div>
      </div>
    </div>
  );
}

function ExplainView({ data }: { data: ExplanationData | null }) {
  if (!data) return <div className="copilot-hint">Select a COA and click "Why?" to see the explanation.</div>;

  return (
    <div className="explain-view">
      <div className="explain-header">
        <span className="explain-q">"{data.question_received}"</span>
        <span className="explain-confidence">Confidence: {data.explanation.recommendation_confidence}</span>
      </div>

      <div className="explain-narration">{data.narration}</div>

      <div className="explain-section-title">Primary Factors</div>
      {data.explanation.primary_factors.map((f, i) => (
        <div key={i} className="explain-factor">
          <div className="factor-name">{f.factor}</div>
          <div className="factor-detail">{f.detail}</div>
          {f.data_citation && <div className="factor-citation">{f.data_citation}</div>}
        </div>
      ))}

      <div className="explain-section-title">Trade-offs</div>
      <div className="explain-text">{data.explanation.trade_off_summary}</div>

      {data.explanation.uncertainty_notes.length > 0 && (
        <>
          <div className="explain-section-title">Uncertainties</div>
          <ul className="explain-list">
            {data.explanation.uncertainty_notes.map((n, i) => <li key={i}>{n}</li>)}
          </ul>
        </>
      )}

      {data.source_state_id && <div className="explain-lineage">Snapshot: {data.source_state_id}</div>}
    </div>
  );
}

function SimulateView({ result }: { result: SimulationResult | null }) {
  if (!result) return <div className="copilot-hint">Select a COA and click "Simulate" to run a what-if analysis.</div>;

  return (
    <div className="sim-view">
      <div className="sim-header">
        <span className="sim-title">Simulation: {result.coa_id}</span>
        <span className="sim-seed">Seed: {result.seed}</span>
      </div>

      <div className="sim-score">
        <div className="score-ring" style={{ '--score': result.outcome_score } as any}>
          <span className="score-value">{(result.outcome_score * 100).toFixed(0)}%</span>
        </div>
        <span className="score-label">Outcome Score</span>
      </div>

      <div className="sim-metrics">
        <div className="sim-metric good">
          <span className="sm-value">{result.threats_intercepted}</span>
          <span className="sm-label">Intercepted</span>
        </div>
        <div className={`sim-metric ${result.threats_missed > 0 ? 'bad' : 'good'}`}>
          <span className="sm-value">{result.threats_missed}</span>
          <span className="sm-label">Missed</span>
        </div>
        <div className={`sim-metric ${result.zone_breaches > 0 ? 'bad' : 'good'}`}>
          <span className="sm-value">{result.zone_breaches}</span>
          <span className="sm-label">Breaches</span>
        </div>
        <div className="sim-metric">
          <span className="sm-value">{result.readiness_remaining_pct.toFixed(0)}%</span>
          <span className="sm-label">Readiness</span>
        </div>
      </div>

      <div className="sim-narration">{result.narration}</div>

      <div className="sim-timeline-title">Timeline</div>
      <div className="sim-timeline">
        {result.timeline.map((e, i) => (
          <div key={i} className={`sim-event event-${e.event.toLowerCase().includes('breach') ? 'bad' : e.event.toLowerCase().includes('intercept') || e.event.toLowerCase().includes('result') ? 'result' : 'normal'}`}>
            <span className="se-time">T+{e.t_s.toFixed(0)}s</span>
            <span className="se-detail">{e.detail}</span>
          </div>
        ))}
      </div>

      {result.source_state_id && <div className="sim-lineage">Snapshot: {result.source_state_id}</div>}
    </div>
  );
}

function AuditView({ decisions }: { decisions: AuditRecord[] }) {
  if (decisions.length === 0) {
    return <div className="copilot-hint">No decisions recorded yet. Approve a COA to create an audit entry.</div>;
  }

  return (
    <div className="audit-view">
      <div className="audit-title">DECISION AUDIT LOG</div>
      {decisions.map(d => (
        <div key={d.decision_id} className="audit-record">
          <div className="audit-record-header">
            <span className="audit-id">{d.decision_id}</span>
            <span className="audit-wave">Wave {d.wave}</span>
          </div>
          <div className="audit-field">
            <span className="af-label">COA</span>
            <span className="af-value">{d.coa_id}</span>
          </div>
          <div className="audit-field">
            <span className="af-label">Time</span>
            <span className="af-value">{new Date(d.timestamp).toLocaleTimeString()}</span>
          </div>
          <div className="audit-field">
            <span className="af-label">Readiness</span>
            <span className="af-value">{d.readiness_remaining_pct.toFixed(1)}%</span>
          </div>
          <div className="audit-field">
            <span className="af-label">Snapshot</span>
            <span className="af-value lineage">{d.source_state_id}</span>
          </div>
          {d.operator_note && (
            <div className="audit-note">{d.operator_note}</div>
          )}
        </div>
      ))}
    </div>
  );
}
