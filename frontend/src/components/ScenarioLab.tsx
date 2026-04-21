import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { ScenarioEntry, ScenarioSession, TimelineMarker } from '../types';
import './ScenarioLab.css';

interface Props {
  currentScenarioId: string;
  currentMode: string;
  currentOrigin: string;
  isPlaying: boolean;
  speed: number;
  session: ScenarioSession | null;
  markers: TimelineMarker[];
  onScenarioLoaded: () => void;
  onControl: (action: string, speed?: number) => void;
  onReset: () => void;
}

const TEMPLATES = [
  { id: 'swarm_pressure', label: 'Swarm Pressure' },
  { id: 'multi_axis_raid', label: 'Multi-Axis Raid' },
  { id: 'escalating_probe', label: 'Escalating Probe' },
  { id: 'random', label: 'Random' },
];

const ORIGIN_LABELS: Record<string, string> = {
  builtin: 'Builtin',
  generated: 'Generated',
  runtime_copy: 'Runtime Copy',
};

const SPEEDS = [1, 2, 4, 8];

export function ScenarioLab({
  currentScenarioId, currentMode, currentOrigin, isPlaying, speed,
  session, markers, onScenarioLoaded, onControl, onReset
}: Props) {
  const [scenarios, setScenarios] = useState<ScenarioEntry[]>([]);
  const [selectedFileId, setSelectedFileId] = useState('scenario_swarm_beta');
  const [mode, setMode] = useState<'replay' | 'live'>('replay');
  const [genTemplate, setGenTemplate] = useState('swarm_pressure');
  const [genSeed, setGenSeed] = useState('');
  const [genDuration, setGenDuration] = useState('300');
  const [generating, setGenerating] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [expanded, setExpanded] = useState(true);

  const liveActive = currentMode === 'live';

  const fetchScenarios = useCallback(async () => {
    try {
      const res = await api.getScenarios();
      setScenarios(res.scenarios || []);
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
      const sid = selectedFileId.replace(/_/g, '-');
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
      const sid = res.file_id.replace(/_/g, '-');
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

  return (
    <div className="scenario-lab">
      <div className="slab-header">
        <span className="slab-title">⚗ SCENARIO LAB</span>
        <span className={`slab-badge slab-badge-mode mode-${currentMode}`}>{currentMode.toUpperCase()}</span>
        <span className={`slab-badge slab-badge-origin origin-${currentOrigin}`}>{ORIGIN_LABELS[currentOrigin] || currentOrigin.toUpperCase()}</span>
      </div>

      {statusMsg && <div className="slab-status">{statusMsg}</div>}

      {/* Playback Controls */}
      <div className="slab-section">
        <label className="slab-label">Playback Control</label>
        <div className="slab-playback-row">
          <button className="slab-btn" onClick={onReset} title="Reset">⟳ Reset</button>
          {isPlaying ? (
            <button className="slab-btn slab-btn-pause" onClick={() => onControl('pause')}>❚❚ Pause</button>
          ) : (
            <button className="slab-btn slab-btn-play" onClick={() => onControl('play')}>▶ Play</button>
          )}
          <div className="slab-speed-group">
            {SPEEDS.map(s => (
              <button
                key={s}
                className={`slab-speed-btn ${speed === s ? 'active' : ''}`}
                onClick={() => onControl('speed', s)}
              >
                ×{s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Active scenario card */}
      {session && session.scenario_id && (
        <div className="slab-active-session">
          <div className="slab-active-top">
            <span className="slab-active-name">{session.scenario_label}</span>
          </div>
          {session.description && (
            <span className="slab-active-desc">{session.description.length > 120 ? session.description.slice(0, 120) + '…' : session.description}</span>
          )}
          <span className="slab-active-meta">
            {session.track_count} tracks · {session.group_count} groups · {session.duration_s}s
          </span>
          {session.seed != null && (
            <span className="slab-active-meta">Seed: {session.seed}{session.template_name ? ` · Template: ${session.template_name}` : ''}</span>
          )}
        </div>
      )}

      {/* Scenario selector */}
      <div className="slab-section">
        <label className="slab-label">Scenario Selector</label>
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
              </>
            );
          })()}
        </div>
      </div>

      {/* Mode selector + load */}
      <div className="slab-section slab-row">
        <div className="slab-mode-toggle">
          <button
            className={`slab-mode-btn ${mode === 'replay' ? 'active' : ''}`}
            onClick={() => setMode('replay')}
          >Replay</button>
          <button
            className={`slab-mode-btn ${mode === 'live' ? 'active' : ''}`}
            onClick={() => setMode('live')}
          >Live Mode</button>
        </div>
        <button className="slab-btn slab-btn-primary" onClick={handleLoad}>
          Load & Start
        </button>
      </div>

      {/* Generator */}
      <div className="slab-section">
        <label className="slab-label">Scenario Generator</label>
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
            {generating ? 'Generating...' : 'Generate New'}
          </button>
          <button className="slab-btn slab-btn-accent" onClick={handleGenerateAndLoad} disabled={generating}>
            Generate & Load
          </button>
        </div>
      </div>

      {/* Live controls */}
      {liveActive && (
        <div className="slab-section slab-live-controls">
          <label className="slab-label">Autonomous Live Controls</label>
          <div className="slab-live-row">
            <button className="slab-btn" onClick={() => handleLiveTick(5)}>Jump +5s</button>
            <button className="slab-btn" onClick={() => handleLiveTick(15)}>Jump +15s</button>
          </div>
          <label className="slab-label" style={{ marginTop: 8 }}>Dynamic Perturbations</label>
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
