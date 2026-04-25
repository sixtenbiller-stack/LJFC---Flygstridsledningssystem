import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { ScenarioEntry, ScenarioSession, FeedStatus, FeedEvent } from '../types';
import './ScenarioLab.css';

interface Props {
  currentScenarioId: string;
  currentMode: string;
  isPlaying: boolean;
  session: ScenarioSession | null;
  feedStatus?: FeedStatus;
  lastFeedEvent?: FeedEvent | null;
  onScenarioLoaded: () => void;
}

const TEMPLATES = [
  { id: 'swarm_pressure', label: 'Swarm Pressure' },
  { id: 'multi_axis_raid', label: 'Multi-Axis Raid' },
  { id: 'escalating_probe', label: 'Escalating Probe' },
  { id: 'random', label: 'Random' },
];

export function ScenarioLab({
  currentScenarioId, currentMode, isPlaying, session,
  feedStatus, lastFeedEvent, onScenarioLoaded,
}: Props) {
  const [scenarios, setScenarios] = useState<ScenarioEntry[]>([]);
  const [selectedFileId, setSelectedFileId] = useState('scenario_minimal_alpha');
  const [featureFlags, setFeatureFlags] = useState({
    extended_scenarios: false,
    live_mutation: false,
    scenario_generator: false,
  });
  const [mode, setMode] = useState<'replay' | 'live'>('replay');
  const [genTemplate, setGenTemplate] = useState('swarm_pressure');
  const [genSeed, setGenSeed] = useState('');
  const [genDuration, setGenDuration] = useState('300');
  const [generating, setGenerating] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const liveActive = currentMode === 'live';

  const fetchScenarios = useCallback(async () => {
    try {
      const res = await api.getScenarios();
      setScenarios(res.scenarios || []);
      setFeatureFlags({
        extended_scenarios: Boolean(res.feature_flags?.extended_scenarios),
        live_mutation: Boolean(res.feature_flags?.live_mutation),
        scenario_generator: Boolean(res.feature_flags?.scenario_generator),
      });
    } catch { /* skip */ }
  }, []);

  useEffect(() => { fetchScenarios(); }, [fetchScenarios]);

  useEffect(() => {
    if (!currentScenarioId) return;
    const fileId = currentScenarioId.replace(/-/g, '_');
    const match = scenarios.find(s => s.file_id === fileId || s.scenario_id === currentScenarioId);
    if (match) setSelectedFileId(match.file_id);
  }, [currentScenarioId, scenarios]);

  const flash = (msg: string) => {
    setStatusMsg(msg);
    setTimeout(() => setStatusMsg(''), 3000);
  };

  const handleLoad = async () => {
    if (mode === 'replay') {
      const sid = selectedFileId;
      await api.loadScenario(sid);
      flash(`Loaded ${selectedFileId} (replay)`);
    } else {
      await api.startLiveSession(selectedFileId);
      flash(`Live session: ${selectedFileId}`);
    }
    onScenarioLoaded();
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const seed = genSeed ? parseInt(genSeed) : undefined;
      const dur = parseInt(genDuration) || 300;
      const res = await api.generateScenario(genTemplate, seed, dur);
      flash(`Generated: ${res.file_id} (seed ${res.seed})`);
      await fetchScenarios();
      setSelectedFileId(res.file_id);
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateAndLoad = async () => {
    setGenerating(true);
    try {
      const seed = genSeed ? parseInt(genSeed) : undefined;
      const dur = parseInt(genDuration) || 300;
      const res = await api.generateScenario(genTemplate, seed, dur);
      const sid = res.file_id;
      await api.loadScenario(sid);
      flash(`Generated & loaded: ${res.file_id}`);
      await fetchScenarios();
      setSelectedFileId(res.file_id);
      onScenarioLoaded();
    } finally {
      setGenerating(false);
    }
  };

  const handleLiveTick = async (dt: number) => {
    await api.liveTick(dt);
    flash(`Ticked +${dt}s`);
  };

  const handleInject = async (type: string, params?: Record<string, unknown>) => {
    await api.liveInject(type, params);
    flash(`Injected: ${type}`);
  };

  const feedState = feedStatus?.status ?? (isPlaying ? 'running' : session && session.current_time_s > 0 ? 'paused' : 'stopped');

  return (
    <div className="scenario-lab">
      <div className="slab-header">
        <span className="slab-title">Feed status</span>
        <span className={`slab-badge slab-feed-ribbon slab-feed-${feedState}`}>{feedState.toUpperCase()}</span>
      </div>

      {statusMsg && <div className="slab-status">{statusMsg}</div>}

      {session && session.scenario_id && (
        <div className="slab-active-session">
          <div className="slab-active-top">
            <span className="slab-active-name">{feedStatus?.label ?? 'Synthetic Live Feed: Minimal Alpha'}</span>
          </div>
          <div className="slab-feed-grid">
            <span className="slab-k">State</span><span className="slab-v">{feedState}</span>
            <span className="slab-k">Mission clock</span><span className="slab-v">T+{Math.round(feedStatus?.current_time_s ?? session.current_time_s)}s</span>
            <span className="slab-k">Last update</span><span className="slab-v">{lastFeedEvent?.event_type ?? '—'}</span>
            <span className="slab-k">ATO</span><span className="slab-v">{typeof session.scenario_meta?.ato_ref === 'string' ? String(session.scenario_meta.ato_ref) : 'ato_minimal_alpha'}</span>
            <span className="slab-k">Speed</span><span className="slab-v">{(feedStatus?.speed_multiplier ?? session.speed_multiplier) ?? 1}x</span>
          </div>
          {session.description && session.description.length < 200 && (
            <span className="slab-active-desc">{session.description}</span>
          )}
          {featureFlags.extended_scenarios && session.seed != null && (
            <span className="slab-active-meta">Seed: {session.seed}{session.template_name ? ` · Template: ${session.template_name}` : ''}</span>
          )}
          {featureFlags.live_mutation && session.runtime_session_id && (
            <span className="slab-active-meta">Session: {session.runtime_session_id.slice(0, 24)}</span>
          )}
          {session.source_parent_scenario && (
            <span className="slab-active-meta">Source: {session.source_parent_scenario}</span>
          )}
          {session.recommended_demo && (
            <span className="slab-active-demo">{session.recommended_demo.length > 100 ? session.recommended_demo.slice(0, 100) + '…' : session.recommended_demo}</span>
          )}
        </div>
      )}

      {/* Mutation log for live mode */}
      {featureFlags.live_mutation && liveActive && session?.mutation_log && session.mutation_log.length > 0 && (
        <div className="slab-mutation-log">
          <span className="slab-label">Mutation Log</span>
          <div className="slab-mutation-list">
            {session.mutation_log.slice(-5).map((m, i) => (
              <div key={i} className="slab-mutation-item">
                <span className="slab-mut-type">{String(m.type || '?')}</span>
                <span className="slab-mut-time">t={String(m.t_s || '?')}s</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scenario selector */}
      {featureFlags.extended_scenarios && (
      <div className="slab-section">
        <label className="slab-label">Scenario</label>
        <select
          className="slab-select"
          value={selectedFileId}
          onChange={e => setSelectedFileId(e.target.value)}
        >
          {scenarios.map(s => (
            <option key={s.file_id} value={s.file_id}>
              {s.title}{s.jury_demo ? ' ★' : ''}{s.source_type === 'generated' ? ' (gen)' : ''}
            </option>
          ))}
        </select>
        <div className="slab-meta">
          {(() => {
            const s = scenarios.find(x => x.file_id === selectedFileId);
            if (!s) return null;
            return (
              <>
                {s.short_description && <span className="slab-meta-desc">{s.short_description}</span>}
                <span className="slab-meta-stats">
                  {s.track_count ?? '?'} tracks · {s.group_count ?? '?'} groups · {s.duration_s ?? '?'}s
                  {s.extended_fields && ' · extended'}
                </span>
              </>
            );
          })()}
        </div>
      </div>
      )}

      <div className="slab-section slab-feed-controls">
        <label className="slab-label">Feed controls</label>
        <div className="slab-live-row">
          <button className="slab-btn slab-btn-primary" onClick={() => api.control(isPlaying ? 'pause' : 'play').then(onScenarioLoaded)}>
            {isPlaying ? 'Pause' : 'Start'}
          </button>
          <button className="slab-btn" onClick={() => api.control('step').then(onScenarioLoaded)}>Step</button>
          <button className="slab-btn" onClick={() => api.control('reset').then(onScenarioLoaded)}>Reset</button>
        </div>
        <div className="slab-live-row">
          {[0.5, 1, 2].map(speed => (
            <button key={speed} className="slab-btn" onClick={() => api.control('speed', speed)}>
              {speed}x
            </button>
          ))}
        </div>
      </div>

      {/* Mode selector + load */}
      {featureFlags.extended_scenarios && (
      <div className="slab-section slab-row">
        <div className="slab-mode-toggle">
          <button
            className={`slab-mode-btn ${mode === 'replay' ? 'active' : ''}`}
            onClick={() => setMode('replay')}
          >Replay</button>
          <button
            className={`slab-mode-btn ${mode === 'live' ? 'active' : ''}`}
            onClick={() => setMode('live')}
          >Live</button>
        </div>
        <button className="slab-btn slab-btn-primary" onClick={handleLoad}>
          Load
        </button>
      </div>
      )}

      {/* Generator */}
      {featureFlags.scenario_generator && (
      <div className="slab-section">
        <label className="slab-label">Generate Scenario</label>
        <div className="slab-gen-row">
          <select className="slab-select slab-gen-tmpl" value={genTemplate} onChange={e => setGenTemplate(e.target.value)}>
            {TEMPLATES.map(t => (
              <option key={t.id} value={t.id}>{t.label}</option>
            ))}
          </select>
          <input
            className="slab-input"
            type="number"
            placeholder="Seed"
            value={genSeed}
            onChange={e => setGenSeed(e.target.value)}
            style={{ width: 70 }}
          />
          <input
            className="slab-input"
            type="number"
            placeholder="Dur"
            value={genDuration}
            onChange={e => setGenDuration(e.target.value)}
            style={{ width: 60 }}
          />
        </div>
        <div className="slab-gen-actions">
          <button className="slab-btn" onClick={handleGenerate} disabled={generating}>
            {generating ? 'Generating...' : 'Generate'}
          </button>
          <button className="slab-btn slab-btn-accent" onClick={handleGenerateAndLoad} disabled={generating}>
            Generate & Load
          </button>
        </div>
      </div>
      )}

      {/* Live controls */}
      {featureFlags.live_mutation && liveActive && (
        <div className="slab-section slab-live-controls">
          <label className="slab-label">Live Controls</label>
          <div className="slab-live-row">
            <button className="slab-btn" onClick={() => api.liveControl(isPlaying ? 'pause' : 'play')}>
              {isPlaying ? '⏸ Pause' : '▶ Play'}
            </button>
            <button className="slab-btn" onClick={() => handleLiveTick(5)}>+5s</button>
            <button className="slab-btn" onClick={() => handleLiveTick(15)}>+15s</button>
            <button className="slab-btn" onClick={() => api.liveControl('reset').then(onScenarioLoaded)}>Reset</button>
          </div>
          <label className="slab-label" style={{ marginTop: 8 }}>Perturbations</label>
          <div className="slab-inject-grid">
            <button className="slab-inject-btn inject-swarm" onClick={() => handleInject('swarm', { corridor: 'corridor-n', size: 12 })}>
              Inject Swarm
            </button>
            <button className="slab-inject-btn inject-raid" onClick={() => handleInject('second_wave', { corridors: ['corridor-nw', 'corridor-ne'] })}>
              Inject Raid
            </button>
            <button className="slab-inject-btn inject-sensor" onClick={() => handleInject('sensor_degrade', { sensor_id: 'sensor-boreal', severity: 'partial' })}>
              Degrade Sensor
            </button>
            <button className="slab-inject-btn inject-readiness" onClick={() => handleInject('readiness_drop')}>
              Drop Readiness
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
