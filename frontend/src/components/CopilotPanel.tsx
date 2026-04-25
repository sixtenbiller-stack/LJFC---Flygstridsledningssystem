import { useState, useRef, useEffect, useMemo } from 'react';
import type {
  ScenarioState, CourseOfAction, ThreatAlert, ThreatGroup,
  DecisionCard as DecisionCardType, AgentChatMessage, CopilotStatusData,
} from '../types';
import { ALL_COMMANDS, type CommandDef } from '../copilotCommands';
import { DecisionCard } from './DecisionCard';
import './CopilotPanel.css';

interface Props {
  state: ScenarioState;
  coas: CourseOfAction[];
  loading: string;
  copilotStatus: CopilotStatusData | null;
  alerts: ThreatAlert[];
  selectedTrack: string | null;
  groups?: ThreatGroup[];
  selectedGroup?: string | null;
  decisionCard?: DecisionCardType | null;
  onGenerateCoas: () => void;
  onExplain: (coaId: string) => void;
  onSimulate: (coaId: string) => void;
  onApprove: (coaId: string) => void;
  onSendCommand: (input: string) => Promise<AgentChatMessage | null>;
  onGroupApprove?: (groupId: string, responseId: string) => void;
  onGroupDefer?: (groupId: string) => void;
  onGroupOverride?: (groupId: string, responseId: string, reason: string) => void;
}

function evidenceItems(structured: AgentChatMessage['structured'] | undefined) {
  const value = structured?.evidence as unknown;
  if (Array.isArray(value)) {
    return value.map((item, i) => {
      if (item && typeof item === 'object') {
        const obj = item as { label?: unknown; detail?: unknown; cited_id?: unknown };
        return {
          label: String(obj.label || `Evidence ${i + 1}`),
          detail: String(obj.detail || ''),
          cited_id: String(obj.cited_id || `evidence-${i}`),
        };
      }
      return { label: `Evidence ${i + 1}`, detail: String(item), cited_id: `evidence-${i}` };
    });
  }
  if (typeof value === 'string' && value.trim()) {
    return [{ label: 'Assessment', detail: value, cited_id: 'gemma-text' }];
  }
  return [];
}

function actionItems(structured: AgentChatMessage['structured'] | undefined) {
  const value = structured?.next_actions as unknown;
  if (Array.isArray(value)) {
    return value.map((item, i) => {
      if (item && typeof item === 'object') {
        const obj = item as { label?: unknown; command?: unknown };
        return {
          label: String(obj.label || `Action ${i + 1}`),
          command: String(obj.command || '/brief'),
        };
      }
      return { label: String(item), command: '/brief' };
    });
  }
  if (typeof value === 'string' && value.trim()) {
    return [{ label: value.slice(0, 28), command: '/brief' }];
  }
  return [];
}

const QUICK_PROMPTS: Array<{ label: string; cmd: string }> = [
  { label: 'Brief', cmd: '/brief' },
  { label: 'What changed?', cmd: '/what-changed' },
  { label: 'Top threat', cmd: '/top-threat' },
  { label: 'ATO constraints', cmd: '/ato' },
  { label: 'Recommend', cmd: '/recommend' },
  { label: 'Simulate current', cmd: '/simulate top' },
];

export function CopilotPanel({
  state, coas, loading, copilotStatus, alerts, selectedTrack,
  groups = [], selectedGroup, decisionCard,
  onGenerateCoas, onExplain, onSimulate, onApprove, onSendCommand,
  onGroupApprove, onGroupDefer, onGroupOverride,
}: Props) {
  const [inputText, setInputText] = useState('');
  const [commandLoading, setCommandLoading] = useState(false);
  const [commandResponse, setCommandResponse] = useState<AgentChatMessage | null>(null);
  const [chatLog, setChatLog] = useState<AgentChatMessage[]>([]);
  const [slashHighlight, setSlashHighlight] = useState(0);
  const [inputFocused, setInputFocused] = useState(false);
  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const topThreat = alerts[0];
  const topCoa = coas[0];
  const activeGroup = groups.find(g => g.group_id === selectedGroup) || groups[0];
  const ai = state.ai_provider_status || copilotStatus?.ai_status;
  const ato = state.ato_context;

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
    if (!q) return mergedSlashCommands.slice(0, 40);
    return mergedSlashCommands.filter(
      c => c.cmd.toLowerCase().includes(q) || c.label.toLowerCase().includes(q),
    ).slice(0, 40);
  }, [inputText, mergedSlashCommands]);

  const slashMenuOpen = inputFocused && inputText.startsWith('/') && filteredSlash.length > 0;

  useEffect(() => {
    setSlashHighlight(0);
  }, [inputText, filteredSlash.length]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatLog.length, commandLoading]);

  const providerLabel = copilotStatus?.provider === 'ollama' || ai?.provider === 'ollama'
    ? 'Local Gemma'
    : copilotStatus?.provider === 'gemini' || ai?.provider === 'gemini'
      ? 'Gemini'
      : 'Fallback';

  const modelLine = `${ai?.provider || copilotStatus?.provider || '—'} · ${ai?.model || copilotStatus?.model || '—'}`;

  const statusLabel = commandLoading
    ? 'LOCAL GEMMA THINKING'
    : (ai?.label || copilotStatus?.ai_status?.label || 'TEMPLATE FALLBACK');

  const statusClass = commandLoading ? 'thinking' : (ai?.status || copilotStatus?.ai_status?.status || 'fallback');

  const contextLine = [
    activeGroup?.group_id && `Grp ${activeGroup.group_id}`,
    selectedTrack && `Trk ${selectedTrack}`,
    state.source_state_id?.replace(/^snap-/, '').slice(0, 20),
  ].filter(Boolean).join(' · ') || '—';

  const handleSendCommand = async (text?: string) => {
    const cmd = text || inputText.trim();
    if (!cmd) return;
    const ts = new Date().toISOString();
    const opMsg: AgentChatMessage = {
      role: 'operator',
      message: cmd,
      timestamp: ts,
      source_state_id: state.source_state_id,
    };
    setChatLog(prev => [...prev, opMsg].slice(-40));
    setInputText('');
    setCommandLoading(true);
    try {
      const resp = await onSendCommand(cmd);
      if (resp) {
        setCommandResponse(resp);
        setChatLog(prev => [...prev, resp].slice(-40));
      } else {
        const err: AgentChatMessage = {
          role: 'assistant',
          timestamp: new Date().toISOString(),
          source_state_id: state.source_state_id,
          status: 'error',
          message: 'No response from Chief of Staff endpoint.',
          display_text: 'No response from Chief of Staff endpoint.',
          provider: 'system',
          model: '',
          parse_status: 'error',
        };
        setCommandResponse(err);
        setChatLog(prev => [...prev, err].slice(-40));
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Request failed';
      const err: AgentChatMessage = {
        role: 'assistant',
        timestamp: new Date().toISOString(),
        source_state_id: state.source_state_id,
        status: 'error',
        message: msg,
        display_text: msg,
        provider: 'system',
        model: '',
        parse_status: 'error',
      };
      setCommandResponse(err);
      setChatLog(prev => [...prev, err].slice(-40));
    } finally {
      setCommandLoading(false);
    }
  };

  const pickSlashCommand = (cmd: string) => {
    setInputText(`${cmd} `);
    setSlashHighlight(0);
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
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

  const hasDecisionCard = Boolean(decisionCard && selectedGroup && onGroupApprove && onGroupDefer && onGroupOverride);

  return (
    <div className="cos-console">
      <header className="cos-header-block">
        <div className="cos-header-top">
          <h1 className="cos-product-title">Chief of Staff</h1>
          <span className="cos-provider-badge">{providerLabel}</span>
        </div>
        <div className="cos-model-line">{modelLine}</div>
        <div className={`cos-status-pill cos-status-${statusClass}`}>{statusLabel}</div>
        <div className="cos-context-line" title={state.source_state_id}>Context: {contextLine}</div>
      </header>

      <div className="cos-main-scroll">
        <LatestAssessmentCard
          response={commandResponse}
          thinking={commandLoading}
          sourceStateId={state.source_state_id}
          onAction={(cmd) => void handleSendCommand(cmd)}
        />

        <section className="cos-decision-block" aria-label="Decision support">
          <h2 className="cos-section-label">Decision support</h2>

          {decisionCard?.recommended_response && (
            <div className="cos-top-rec">
              <span className="cos-quiet-label">Top recommendation</span>
              <p className="cos-rec-title">{decisionCard.recommended_response.title}</p>
              <p className="cos-rec-summary">{decisionCard.recommended_response.summary}</p>
            </div>
          )}
          {!decisionCard && (
            <div className="cos-quiet-empty">
              {topCoa
                ? <>Ranked response plan: <strong>{topCoa.title}</strong></>
                : state.coa_trigger_pending
                  ? 'Recommendation trigger active — generate COAs for ranked options.'
                  : 'Monitoring — no ranked plan until feed develops the threat picture.'}
            </div>
          )}

          <div className="cos-ato-panel">
            <h3 className="cos-ato-heading">ATO / mission constraints</h3>
            <div className="cos-ato-name">{ato?.ato_id ?? 'ato_minimal_alpha'}</div>
            <p className="cos-ato-intent">{ato?.commander_intent ?? '—'}</p>
            <dl className="cos-ato-dl">
              <dt>Primary defended</dt>
              <dd>{(ato?.primary_defended_object_ids ?? ['city-arktholm']).join(', ')}</dd>
              <dt>Reserve</dt>
              <dd>{JSON.stringify(ato?.reserve_policy ?? { min_fighter_reserve: 1 })}</dd>
              <dt>Approval</dt>
              <dd>{ato?.approval_required ? `Required · ${ato?.approval_role ?? '—'}` : '—'}</dd>
            </dl>
          </div>

          <div className="cos-action-row">
            <button type="button" className="cos-btn cos-btn-primary" onClick={onGenerateCoas} disabled={loading === 'coas'}>
              {loading === 'coas' ? 'Generating…' : 'Generate COAs'}
            </button>
            <button type="button" className="cos-btn" onClick={() => topCoa && onExplain(topCoa.coa_id)} disabled={!topCoa || loading === 'explain'}>
              Why this plan?
            </button>
            <button type="button" className="cos-btn" onClick={() => topCoa && onSimulate(topCoa.coa_id)} disabled={!topCoa || loading === 'simulate'}>
              Run what-if simulation
            </button>
            <button type="button" className="cos-btn cos-btn-warn" onClick={() => topCoa && onApprove(topCoa.coa_id)} disabled={!topCoa || loading === 'approve'}>
              Approve
            </button>
          </div>

          {hasDecisionCard && decisionCard && (
            <div className="cos-decision-embed">
              <DecisionCard
                card={decisionCard}
                onApprove={onGroupApprove!}
                onDefer={onGroupDefer!}
                onOverride={onGroupOverride!}
                onGenerateCoas={onGenerateCoas}
                onSimulate={onSimulate}
                loading={loading}
              />
            </div>
          )}
        </section>

        <section className="cos-transcript-section" aria-label="Conversation log">
          <h2 className="cos-section-label">Command log</h2>
          <ChatTranscript messages={chatLog} thinking={commandLoading} transcriptEndRef={transcriptEndRef} />
        </section>
      </div>

      <footer className="cos-chat-footer">
        <div className="cos-quick-row">
          {QUICK_PROMPTS.map(q => (
            <button
              key={q.cmd}
              type="button"
              className="cos-quick-chip"
              disabled={commandLoading}
              onClick={() => void handleSendCommand(q.cmd)}
            >
              {q.label}
            </button>
          ))}
        </div>

        <div className="cos-input-wrap">
          <div className="cos-input-area">
            <textarea
              ref={inputRef}
              className="cos-input"
              placeholder={commandLoading ? 'Chief of Staff is responding…' : 'Ask Chief of Staff about the current threat situation…'}
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setInputFocused(true)}
              onBlur={() => { window.setTimeout(() => setInputFocused(false), 160); }}
              disabled={commandLoading}
              autoComplete="off"
              spellCheck={false}
              aria-expanded={slashMenuOpen}
              aria-controls="slash-suggest-cos"
              rows={2}
            />
            <button
              type="button"
              className="cos-send"
              onClick={() => void handleSendCommand()}
              disabled={commandLoading || !inputText.trim()}
            >
              Send
            </button>
          </div>

          {slashMenuOpen && (
            <div id="slash-suggest-cos" className="slash-suggest" role="listbox">
              {filteredSlash.map((c, i) => (
                <div key={c.cmd}>
                  {(i === 0 || filteredSlash[i - 1].category !== c.category) && (
                    <div className="slash-cat" role="presentation">{c.category}</div>
                  )}
                  <button
                    type="button"
                    role="option"
                    aria-selected={i === slashHighlight}
                    className={`slash-row ${i === slashHighlight ? 'active' : ''}`}
                    onMouseDown={e => { e.preventDefault(); void handleSendCommand(c.cmd); }}
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
      </footer>
    </div>
  );
}

function LatestAssessmentCard({
  response, thinking, sourceStateId, onAction,
}: {
  response: AgentChatMessage | null;
  thinking: boolean;
  sourceStateId: string;
  onAction: (cmd: string) => void;
}) {
  const structured = response?.structured;
  const evidence = evidenceItems(structured);
  const actions = actionItems(structured);
  const rawFallback = !structured && (response?.display_text || response?.message);

  if (thinking) {
    return (
      <section className="cos-assessment cos-assessment-thinking">
        <h2 className="cos-section-label">Latest assessment</h2>
        <p className="cos-bluf">Chief of Staff is analyzing current state…</p>
        <p className="cos-assessment-muted">Querying local Ollama. Deterministic state remains authoritative.</p>
      </section>
    );
  }

  if (!response || (!structured && !rawFallback)) {
    return (
      <section className="cos-assessment cos-assessment-empty">
        <h2 className="cos-section-label">Latest assessment</h2>
        <p className="cos-bluf cos-bluf-muted">No assessment yet.</p>
        <p className="cos-assessment-muted">Start the feed or ask Chief of Staff for a brief. State: {sourceStateId}</p>
      </section>
    );
  }

  if (rawFallback && !structured) {
    return (
      <section className="cos-assessment cos-assessment-raw">
        <div className="cos-assessment-head">
          <h2 className="cos-section-label">Latest assessment</h2>
          <span className="cos-assessment-meta">{response.provider} · {response.model} · {response.parse_status || response.status || 'text'}</span>
        </div>
        <pre className="cos-raw-text">{String(rawFallback)}</pre>
        <div className="cos-assessment-lineage">State {response.source_state_id}</div>
      </section>
    );
  }

  return (
    <section className="cos-assessment">
      <div className="cos-assessment-head">
        <h2 className="cos-section-label">Latest assessment</h2>
        <span className="cos-assessment-meta">
          {response.provider} · {response.model}
          {response.parse_status ? ` · ${response.parse_status}` : ''}
          {response.fallback_used ? ' · fallback' : ''}
        </span>
      </div>
      <p className="cos-bluf">{structured!.bluf}</p>
      <div className="cos-assessment-body">
        <span className="cos-quiet-label">Current situation</span>
        <p>{structured!.situation}</p>
      </div>
      {evidence.length > 0 && (
        <div className="cos-evidence-block">
          <span className="cos-quiet-label">Evidence</span>
          <ul>
            {evidence.slice(0, 6).map((e, i) => (
              <li key={`${e.cited_id}-${i}`}><strong>{e.label}:</strong> {e.detail}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="cos-recommendation-block">
        <span className="cos-quiet-label">Recommendation</span>
        <p>{structured!.recommendation}</p>
      </div>
      {actions.some(a => a.command.startsWith('/')) && (
        <div className="cos-assessment-actions">
          {actions.filter(a => a.command.startsWith('/')).slice(0, 4).map(a => (
            <button key={a.command} type="button" className="cos-action-pill" onClick={() => onAction(a.command)}>
              {a.label}
            </button>
          ))}
        </div>
      )}
      <div className="cos-assessment-lineage">State {response.source_state_id}</div>
    </section>
  );
}

function ChatTranscript({
  messages, thinking, transcriptEndRef,
}: {
  messages: AgentChatMessage[];
  thinking: boolean;
  transcriptEndRef: React.RefObject<HTMLDivElement | null>;
}) {
  if (messages.length === 0 && !thinking) {
    return <div className="cos-transcript-empty">No messages yet — use quick prompts or type below.</div>;
  }
  return (
    <div className="cos-transcript">
      {messages.map((m, i) => (
        <div key={`${m.timestamp}-${i}`} className={`cos-msg cos-msg-${m.role}`}>
          <div className="cos-msg-meta">
            {m.role === 'operator' ? (
              <span>Operator</span>
            ) : (
              <span>{m.provider || 'AI'} · {m.model || '—'}{m.status ? ` · ${m.status}` : ''}</span>
            )}
            <time dateTime={m.timestamp}>{new Date(m.timestamp).toLocaleTimeString()}</time>
          </div>
          {m.role === 'operator' ? (
            <div className="cos-msg-body">{m.message}</div>
          ) : (
            <div className="cos-msg-body">
              {m.structured?.bluf || m.display_text || m.message}
              {m.source_state_id && (
                <div className="cos-msg-state">State: {m.source_state_id}</div>
              )}
              {m.parse_status === 'error' || m.status === 'error' ? (
                <div className="cos-msg-err">Error — check Ollama or network. Fallback may apply.</div>
              ) : null}
            </div>
          )}
        </div>
      ))}
      {thinking && (
        <div className="cos-msg cos-msg-assistant cos-msg-pending">
          <div className="cos-msg-body">Chief of Staff responding…</div>
        </div>
      )}
      <div ref={transcriptEndRef} />
    </div>
  );
}
