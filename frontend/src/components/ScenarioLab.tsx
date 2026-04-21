import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { ScenarioEntry, ScenarioSession, TimelineMarker, Geography, Placeable, PlaceableTemplate, ScenarioModel } from '../types';
import { TacticalMap } from './TacticalMap';
import './ScenarioLab.css';

interface Props {
  currentScenarioId: string;
  currentMode: string;
  currentOrigin: string;
  isPlaying: boolean;
  speed: number;
  session: ScenarioSession | null;
  markers: TimelineMarker[];
  geography: Geography | null;
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
  session, markers, geography, onScenarioLoaded, onControl, onReset
}: Props) {
  const [activeTab, setActiveTab] = useState<'management' | 'editor'>('management');
  const [scenarios, setScenarios] = useState<ScenarioEntry[]>([]);
  const [selectedFileId, setSelectedFileId] = useState('scenario_swarm_beta');
  const [mode, setMode] = useState<'replay' | 'live'>('replay');
  const [genTemplate, setGenTemplate] = useState('swarm_pressure');
  const [genSeed, setGenSeed] = useState('');
  const [genDuration, setGenDuration] = useState('300');
  const [generating, setGenerating] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  // Editor State
  const [editorScenario, setEditorScenario] = useState<ScenarioModel>({
    scenario_id: 'custom_1',
    name: 'Custom Scenario 1',
    map_background: '',
    placeables: [],
    events: [],
    meta: {}
  });
  const [placeableTemplates, setTemplates] = useState<PlaceableTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  const liveActive = currentMode === 'live';

  const fetchScenarios = useCallback(async () => {
    try {
      const res = await api.getScenarios();
      setScenarios(res.scenarios || []);
    } catch { /* skip */ }
  }, []);

  useEffect(() => {
    fetchScenarios();
    api.getPlaceableTemplates().then(res => {
      const list = res.placeables || [];
      setTemplates(list);
      if (list.length > 0) setSelectedTemplate(list[0].type);
    }).catch(() => {});
  }, [fetchScenarios]);

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
      flash('Loaded ' + selectedFileId + ' (replay)');
    } else {
      await api.startLiveSession(selectedFileId);
      flash('Live session: ' + selectedFileId);
    }
    onScenarioLoaded();
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const seed = genSeed ? parseInt(genSeed) : undefined;
      const dur = parseInt(genDuration) || 300;
      const res = await api.generateScenario(genTemplate, seed, dur);
      flash('Generated: ' + res.file_id);
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
      flash('Generated & loaded: ' + res.file_id);
      await fetchScenarios();
      setSelectedFileId(res.file_id);
      onScenarioLoaded();
    } finally {
      setGenerating(false);
    }
  };

  const handleLiveTick = async (dt: number) => {
    await api.liveTick(dt);
    flash('Ticked +' + dt + 's');
  };

  const handleInject = async (type: string, params?: Record<string, unknown>) => {
    await api.liveInject(type, params);
    flash('Injected: ' + type);
  };

  // Editor Handlers
  const handleMapClick = (x: number, y: number) => {
    if (activeTab !== 'editor' || !selectedTemplate) return;
    const newPlaceable: Placeable = {
      id: 'p-' + Date.now(),
      type: selectedTemplate,
      x_km: x,
      y_km: y,
      properties: {}
    };
    setEditorScenario(prev => ({
      ...prev,
      placeables: [...prev.placeables, newPlaceable]
    }));
  };

  const handleSaveScenario = async () => {
    try {
      await api.saveScenario(editorScenario);
      flash('Scenario saved!');
      fetchScenarios();
    } catch { flash('Save failed'); }
  };

  return (
    <div className={'scenario-lab ' + (activeTab === 'editor' ? 'editor-mode-active' : '')}>
      <div className='slab-tabs'>
        <button className={activeTab === 'management' ? 'active' : ''} onClick={() => setActiveTab('management')}>MANAGEMENT</button>
        <button className={activeTab === 'editor' ? 'active' : ''} onClick={() => setActiveTab('editor')}>MAP EDITOR</button>
      </div>

      {statusMsg && <div className='slab-status'>{statusMsg}</div>}

      {activeTab === 'management' ? (
        <div className='slab-management-view'>
          <div className='slab-header'>
            <span className='slab-title'>⚗ SCENARIO LAB</span>
            <span className={'slab-badge slab-badge-mode mode-' + currentMode}>{currentMode.toUpperCase()}</span>
            <span className={'slab-badge slab-badge-origin origin-' + currentOrigin}>{ORIGIN_LABELS[currentOrigin] || currentOrigin.toUpperCase()}</span>
          </div>

          <div className='slab-section'>
            <label className='slab-label'>Playback Control</label>
            <div className='slab-playback-row'>
              <button className='slab-btn' onClick={onReset}>⟳ Reset</button>
              {isPlaying ? (
                <button className='slab-btn slab-btn-pause' onClick={() => onControl('pause')}>❚❚ Pause</button>
              ) : (
                <button className='slab-btn slab-btn-play' onClick={() => onControl('play')}>▶ Play</button>
              )}
              <div className='slab-speed-group'>
                {SPEEDS.map(s => (
                  <button key={s} className={'slab-speed-btn ' + (speed === s ? 'active' : '')} onClick={() => onControl('speed', s)}>×{s}</button>
                ))}
              </div>
            </div>
          </div>

          {session && session.scenario_id && (
            <div className='slab-active-session' style={{marginTop: 8}}>
              <span className='slab-active-name'>{session.scenario_label}</span>
              <span className='slab-active-meta'>{session.track_count} tracks · {session.group_count} groups · {session.duration_s}s</span>
            </div>
          )}

          <div className='slab-section' style={{marginTop: 12}}>
            <label className='slab-label'>Scenario Selector</label>
            <select className='slab-select' value={selectedFileId} onChange={e => setSelectedFileId(e.target.value)}>
              {scenarios.map(s => (
                <option key={s.file_id} value={s.file_id}>{s.title}{s.jury_demo ? ' ★' : ''}</option>
              ))}
            </select>
          </div>

          <div className='slab-section slab-row'>
            <div className='slab-mode-toggle'>
              <button className={'slab-mode-btn ' + (mode === 'replay' ? 'active' : '')} onClick={() => setMode('replay')}>Replay</button>
              <button className={'slab-mode-btn ' + (mode === 'live' ? 'active' : '')} onClick={() => setMode('live')}>Live</button>
            </div>
            <button className='slab-btn slab-btn-primary' onClick={handleLoad}>Load & Start</button>
          </div>

          <div className='slab-section' style={{marginTop: 12}}>
            <label className='slab-label'>Scenario Generator</label>
            <div className='slab-gen-row'>
              <select className='slab-select' value={genTemplate} onChange={e => setGenTemplate(e.target.value)}>
                {TEMPLATES.map(t => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>
              <input className='slab-input' style={{width: 65}} type='number' placeholder='Seed' value={genSeed} onChange={e => setGenSeed(e.target.value)} />
            </div>
            <div className='slab-gen-actions' style={{marginTop: 4}}>
              <button className='slab-btn' onClick={handleGenerate} disabled={generating}>Generate</button>
              <button className='slab-btn slab-btn-accent' onClick={handleGenerateAndLoad} disabled={generating}>Gen & Load</button>
            </div>
          </div>
        </div>
      ) : (
        <div className='slab-editor-view'>
          <div className='slab-editor-sidebar'>
            <div className='slab-section'>
              <label className='slab-label'>Scenario Info</label>
              <input className='slab-input' value={editorScenario.scenario_id} onChange={e => setEditorScenario({...editorScenario, scenario_id: e.target.value})} placeholder='Scenario ID' />
              <input className='slab-input' value={editorScenario.name} onChange={e => setEditorScenario({...editorScenario, name: e.target.value})} placeholder='Name' />
            </div>
            <div className='slab-section'>
              <label className='slab-label'>Asset Palette (Click to Select)</label>
              <div className='slab-asset-palette'>
                {placeableTemplates.map(t => (
                  <button key={t.type} className={'slab-asset-btn ' + (selectedTemplate === t.type ? 'active' : '')} onClick={() => setSelectedTemplate(t.type)}>
                    {t.type.toUpperCase()}
                  </button>
                ))}
              </div>
              <p style={{fontSize: 9, color: '#6e7681'}}>Click on map to place selected asset</p>
            </div>
            <div className='slab-section'>
              <button className='slab-btn slab-btn-primary' onClick={handleSaveScenario}>SAVE SCENARIO</button>
            </div>
            <div className='slab-section slab-editor-list'>
              <label className='slab-label'>Placed Assets ({editorScenario.placeables.length})</label>
              {editorScenario.placeables.map(p => (
                <div key={p.id} className='slab-placed-item'>
                  <span>{p.type} ({p.x_km.toFixed(0)}, {p.y_km.toFixed(0)})</span>
                  <button onClick={() => setEditorScenario({...editorScenario, placeables: editorScenario.placeables.filter(x => x.id !== p.id)})}>×</button>
                </div>
              ))}
            </div>
          </div>
          <div className='slab-editor-main'>
            <TacticalMap 
              geography={geography}
              tracks={[]}
              assets={[]}
              placeables={editorScenario.placeables}
              selectedTrack={null}
              onSelectTrack={() => {}}
              coas={[]}
              followTopThreat={false}
              onFollowTopThreatChange={() => {}}
              topThreatTrackId={null}
              onMapClick={handleMapClick}
            />
          </div>
        </div>
      )}
    </div>
  );
}
