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

const SPEEDS = [1, 2, 4, 8];

export function ScenarioLab({
  currentScenarioId, currentMode, currentOrigin, isPlaying, speed,
  session, markers, geography, onScenarioLoaded, onControl, onReset
}: Props) {
  const [activeTab, setActiveTab] = useState<'management' | 'editor'>('management');
  const [scenarios, setScenarios] = useState<ScenarioEntry[]>([]);
  const [selectedFileId, setSelectedFileId] = useState('');
  const [mode, setMode] = useState<'replay' | 'live'>('replay');
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
  const [selectedPlaceableId, setSelectedPlaceableId] = useState<string | null>(null);
  const [editorTool, setEditorTool] = useState<'select' | 'place'>('select');

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
  useEffect(() => {
    const timer = setTimeout(() => {
      api.syncScenario(editorScenario).catch(() => {});
    }, 500);
    return () => clearTimeout(timer);
  }, [editorScenario]);


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

  // Editor Handlers
  const handleMapClick = (x: number, y: number) => {
    if (activeTab !== 'editor') return;
    if (editorTool === 'select') {
       setSelectedPlaceableId(null);
       return;
    }
    if (!selectedTemplate) return;
    const newPlaceable: Placeable = {
      id: 'p-' + Date.now(),
      type: selectedTemplate,
      x_km: x,
      y_km: y,
      properties: {
        range_km: selectedTemplate === 'arthur_radar' ? 100 : 50
      }
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

  const handleDeletePlaceable = (id: string) => {
    setEditorScenario(prev => ({
      ...prev,
      placeables: prev.placeables.filter(p => p.id !== id)
    }));
    if (selectedPlaceableId === id) setSelectedPlaceableId(null);
  };

  const handleMovePlaceable = (id: string, x: number, y: number) => {
    setEditorScenario(prev => ({
      ...prev,
      placeables: prev.placeables.map(p => p.id === id ? { ...p, x_km: x, y_km: y } : p)
    }));
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
    setSelectedTemplate(placeableTemplates[0]?.type || null);
    setSelectedPlaceableId(null);
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
            <span className={'slab-badge slab-badge-origin origin-' + currentOrigin}>{currentOrigin.toUpperCase()}</span>
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
        </div>
      ) : (
        <div className='slab-editor-view'>
          <div className='slab-editor-sidebar'>
            <div className='slab-section'>
              <label className='slab-label'>Editor Tools</label>
              <div className='slab-mode-toggle'>
                <button 
                  className={'slab-mode-btn ' + (editorTool === 'select' ? 'active' : '')} 
                  onClick={() => setEditorTool('select')}
                >
                  SELECTION
                </button>
                <button 
                  className={'slab-mode-btn ' + (editorTool === 'place' ? 'active' : '')} 
                  onClick={() => setEditorTool('place')}
                >
                  PLACEMENT
                </button>
              </div>
            </div>

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

          <div className='slab-editor-list' style={{marginTop: 10}}>
            <label className='slab-label'>Placed Assets ({editorScenario.placeables.length})</label>
            <div style={{maxHeight: 150, overflowY: 'auto'}}>
              {editorScenario.placeables.map(p => (
                <div key={p.id} className={'slab-placed-item ' + (selectedPlaceableId === p.id ? 'active' : '')} onClick={() => setSelectedPlaceableId(p.id)}>
                  <span style={{overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                    {p.type} ({p.x_km.toFixed(0)}, {p.y_km.toFixed(0)})
                  </span>
                  <button onClick={(e) => { e.stopPropagation(); handleDeletePlaceable(p.id); }}>×</button>
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
              onDeletePlaceable={handleDeletePlaceable}
              onMovePlaceable={handleMovePlaceable}
              editorMode={true}
              mapBackground={editorScenario.map_background}
              selectedPlaceableId={selectedPlaceableId}
              onSelectPlaceable={setSelectedPlaceableId}
              selectedTemplate={selectedTemplate}
              activeTool={editorTool}
              onToolChange={setEditorTool}
            />
          </div>
        </div>
      )}
    </div>
  );
}
