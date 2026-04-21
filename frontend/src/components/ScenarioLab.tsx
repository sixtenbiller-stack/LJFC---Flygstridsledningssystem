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
  const [selectedFileId, setSelectedFileId] = useState('');
  const [mode, setMode] = useState<'replay' | 'live'>('replay');
  const [genTemplate, setGenTemplate] = useState('swarm_pressure');
  const [genSeed, setGenSeed] = useState('');
  const [genDuration, setGenDuration] = useState('300');
  const [generating, setGenerating] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  // Editor State
  const [editorScenario, setEditorScenario] = useState<ScenarioModel>({
    scenario_id: 'custom_' + Date.now(),
    name: 'New Custom Scenario',
    map_background: '',
    placeables: [],
    events: [],
    meta: {}
  });
  const [placeableTemplates, setTemplates] = useState<PlaceableTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

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

  const handleLoadForEdit = async (fileId: string) => {
    if (!fileId) return;
    try {
      const data = await api.getScenarioRaw(fileId);
      setEditorScenario({
        scenario_id: data.meta?.scenario_id || data.scenario_id || fileId,
        name: data.meta?.name || data.name || data.title || fileId,
        map_background: data.meta?.map_background || data.map_background || '',
        placeables: data.placeables || [],
        events: data.events || [],
        meta: data.meta || {}
      });
      flash('Loaded for edit: ' + fileId);
    } catch { flash('Load failed'); }
  };

  const handleResetMap = () => {
    setEditorScenario({
      scenario_id: 'custom_' + Date.now(),
      name: 'New Custom Scenario',
      map_background: '',
      placeables: [],
      events: [],
      meta: {}
    });
    flash('Map reset');
  };

  const handleUploadMap = async (file: File) => {
    try {
      const res = await api.uploadMap(file);
      if (res.url) {
        setEditorScenario({ ...editorScenario, map_background: res.url });
        flash('Map uploaded!');
      } else if (res.error) {
        flash('Error: ' + res.error);
      }
    } catch { flash('Upload failed'); }
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
              <option value="">-- Choose Scenario --</option>
              {scenarios.map(s => (
                <option key={s.file_id} value={s.file_id}>{s.title}{s.jury_demo ? ' ★' : ''}</option>
              ))}
            </select>
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
              <div style={{display: 'flex', flexDirection: 'column', gap: 4}}>
                <input className='slab-input' value={editorScenario.scenario_id} onChange={e => setEditorScenario({...editorScenario, scenario_id: e.target.value})} placeholder='Scenario ID (e.g. proto_1)' />
                <input className='slab-input' value={editorScenario.name} onChange={e => setEditorScenario({...editorScenario, name: e.target.value})} placeholder='Display Name' />
              </div>
            </div>

            <div className='slab-section'>
              <label className='slab-label'>Map Background (PNG/JPG)</label>
              <div style={{display: 'flex', gap: 4}}>
                <input className='slab-input' style={{flex: 1}} value={editorScenario.map_background || ''} onChange={e => setEditorScenario({...editorScenario, map_background: e.target.value})} placeholder='/api/maps/gotland.png' />
                <label className='slab-btn' style={{cursor: 'pointer', padding: '4px 8px', display: 'flex', alignItems: 'center'}}>
                   ⬆
                   <input type="file" style={{display: 'none'}} accept="image/*" onChange={e => {
                      const file = e.target.files?.[0];
                      if (file) handleUploadMap(file);
                   }} />
                </label>
              </div>
            </div>

            <div className='slab-section'>
              <label className='slab-label'>Load Existing to Edit</label>
              <select className='slab-select' onChange={e => handleLoadForEdit(e.target.value)}>
                <option value="">-- Choose Scenario --</option>
                {scenarios.map(s => (
                  <option key={s.file_id} value={s.file_id}>{s.title}</option>
                ))}
              </select>
            </div>

            <div className='slab-section'>
              <label className='slab-label'>Asset Palette (Click to Select)</label>
              <div className='slab-asset-palette'>
                {placeableTemplates.length === 0 && <p style={{fontSize: 10, color: '#f85149'}}>No placeable templates found.</p>}
                {placeableTemplates.map(t => (
                  <button key={t.type} className={'slab-asset-btn ' + (selectedTemplate === t.type ? 'active' : '')} onClick={() => setSelectedTemplate(t.type)}>
                    {t.type.toUpperCase()}
                  </button>
                ))}
              </div>
              <p style={{fontSize: 9, color: '#6e7681', marginTop: 4}}>Click on map to place asset</p>
            </div>

            <div className='slab-section slab-row' style={{paddingTop: 10, borderTop: '1px solid var(--border)'}}>
              <button className='slab-btn' style={{flex: 1}} onClick={handleResetMap}>RESET ALL</button>
              <button className='slab-btn slab-btn-primary' style={{flex: 1}} onClick={handleSaveScenario}>SAVE</button>
            </div>

            <div className='slab-section slab-editor-list' style={{marginTop: 10}}>
              <label className='slab-label'>Placed Assets ({editorScenario.placeables.length})</label>
              <div style={{maxHeight: 150, overflowY: 'auto'}}>
                {editorScenario.placeables.map(p => (
                  <div key={p.id} className='slab-placed-item'>
                    <span style={{overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                      {p.type} ({p.x_km.toFixed(0)}, {p.y_km.toFixed(0)})
                    </span>
                    <button onClick={() => setEditorScenario({...editorScenario, placeables: editorScenario.placeables.filter(x => x.id !== p.id)})}>×</button>
                  </div>
                ))}
              </div>
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
              editorMode={true}
              mapBackground={editorScenario.map_background}
            />
          </div>
        </div>
      )}
    </div>
  );
}
