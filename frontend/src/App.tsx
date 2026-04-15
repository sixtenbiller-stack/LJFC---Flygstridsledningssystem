import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from './api/client';
import { usePolling } from './hooks/usePolling';
import type {
  ScenarioState, ThreatAlert, CourseOfAction, SimulationResult,
  ExplanationData, AuditRecord, Geography, FeedItem, CopilotResponse,
  CopilotStatusData,
} from './types';
import { TacticalMap } from './components/TacticalMap';
import { AlertQueue } from './components/AlertQueue';
import { CopilotPanel } from './components/CopilotPanel';
import { Timeline } from './components/Timeline';
import {
  loadLayout,
  saveLayout,
  clampRails,
  presetToPixels,
  LAYOUT_PRESETS,
  getBottomHeight,
  type LayoutPresetId,
  type BottomBarMode,
  type StoredLayout,
} from './layout/layoutStorage';
import './App.css';

const BAND_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export default function App() {
  const [loaded, setLoaded] = useState(false);
  const [geo, setGeo] = useState<Geography | null>(null);
  const [selectedTrack, setSelectedTrack] = useState<string | null>(null);
  const [coas, setCoas] = useState<CourseOfAction[]>([]);
  const [explanation, setExplanation] = useState<ExplanationData | null>(null);
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  const [decisions, setDecisions] = useState<AuditRecord[]>([]);
  const [coaWave, setCoaWave] = useState(0);
  const [loading, setLoading] = useState('');
  const [feedItems, setFeedItems] = useState<FeedItem[]>([]);
  const [copilotStatus, setCopilotStatus] = useState<CopilotStatusData | null>(null);
  const [followTopThreat, setFollowTopThreat] = useState(false);
  const [layoutPreset, setLayoutPreset] = useState<LayoutPresetId>('balanced');
  const [leftPx, setLeftPx] = useState(320);
  const [rightPx, setRightPx] = useState(420);
  const [bottomMode, setBottomMode] = useState<BottomBarMode>('normal');
  const [timelineCollapsed, setTimelineCollapsed] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<ScenarioState | null>(null);
  const dragRef = useRef<'left' | 'right' | null>(null);
  const dragStartRef = useRef({ x: 0, l: 0, r: 0 });
  const geoLoaded = useRef(false);
  const lastFeedId = useRef<string | undefined>(undefined);

  const fetchState = useCallback(async () => {
    const needGeo = !geoLoaded.current;
    const result = await api.getState(needGeo);
    if (result.geography) {
      setGeo(result.geography);
      geoLoaded.current = true;
    }
    return result;
  }, []);
  const fetchAlerts = useCallback(() => api.getAlerts(), []);

  const fetchFeed = useCallback(async () => {
    try {
      const items: FeedItem[] = await api.getFeed(lastFeedId.current);
      if (items.length > 0) {
        setFeedItems(prev => [...prev, ...items]);
        lastFeedId.current = items[items.length - 1].id;
      }
    } catch {
      /* skip */
    }
  }, []);

  const { data: state } = usePolling<ScenarioState>(fetchState, 800, loaded);
  const { data: alerts } = usePolling<ThreatAlert[]>(fetchAlerts, 1000, loaded);

  useEffect(() => {
    stateRef.current = state ?? null;
  }, [state]);

  const sortedAlerts = useMemo(() => {
    const list = [...(alerts || [])];
    list.sort((a, b) => {
      const ba = BAND_ORDER[a.priority_band] ?? 4;
      const bb = BAND_ORDER[b.priority_band] ?? 4;
      if (ba !== bb) return ba - bb;
      return b.threat_score - a.threat_score;
    });
    return list;
  }, [alerts]);

  const topThreatTrackId = sortedAlerts[0]?.track_id ?? null;

  useEffect(() => {
    if (followTopThreat && topThreatTrackId) {
      setSelectedTrack(topThreatTrackId);
    }
  }, [followTopThreat, topThreatTrackId]);

  useEffect(() => {
    const interval = setInterval(fetchFeed, 2000);
    return () => clearInterval(interval);
  }, [fetchFeed]);

  useEffect(() => {
    api.loadScenario('scenario-alpha').then(() => setLoaded(true));
    api.getCopilotStatus().then(setCopilotStatus).catch(() => {});
  }, []);

  const initLayout = useCallback(() => {
    const w = bodyRef.current?.clientWidth ?? (typeof window !== 'undefined' ? window.innerWidth : 1400);
    const stored = loadLayout();
    if (stored) {
      const c = clampRails(w, stored.leftPx, stored.rightPx);
      setLeftPx(c.leftPx);
      setRightPx(c.rightPx);
      setLayoutPreset(stored.preset);
      setBottomMode(stored.bottomMode);
    } else {
      const p = presetToPixels('balanced', w);
      setLeftPx(p.leftPx);
      setRightPx(p.rightPx);
    }
  }, []);

  useEffect(() => {
    if (!loaded) return;
    const t = window.setTimeout(initLayout, 0);
    return () => window.clearTimeout(t);
  }, [loaded, initLayout]);

  useEffect(() => {
    const onResize = () => {
      const w = bodyRef.current?.clientWidth ?? window.innerWidth;
      const c = clampRails(w, leftPx, rightPx);
      setLeftPx(c.leftPx);
      setRightPx(c.rightPx);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [leftPx, rightPx]);

  useEffect(() => {
    const layout: StoredLayout = {
      preset: layoutPreset,
      leftPx,
      rightPx,
      bottomMode,
    };
    saveLayout(layout);
  }, [layoutPreset, leftPx, rightPx, bottomMode]);

  const applyPreset = useCallback((id: LayoutPresetId) => {
    const w = bodyRef.current?.clientWidth ?? window.innerWidth;
    const p = presetToPixels(id, w);
    setLeftPx(p.leftPx);
    setRightPx(p.rightPx);
    setLayoutPreset(id);
  }, []);

  const onDividerMouseDown = (side: 'left' | 'right') => (e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = side;
    dragStartRef.current = { x: e.clientX, l: leftPx, r: rightPx };
  };

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const w = bodyRef.current?.clientWidth ?? window.innerWidth;
      const dx = e.clientX - dragStartRef.current.x;
      if (dragRef.current === 'left') {
        const nl = dragStartRef.current.l + dx;
        const c = clampRails(w, nl, rightPx);
        setLeftPx(c.leftPx);
        setRightPx(c.rightPx);
      } else {
        const nr = dragStartRef.current.r - dx;
        const c = clampRails(w, leftPx, nr);
        setLeftPx(c.leftPx);
        setRightPx(c.rightPx);
      }
    };
    const onUp = () => {
      dragRef.current = null;
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [leftPx, rightPx]);

  const onDividerDoubleClick = () => applyPreset('balanced');

  const handleControl = async (action: string, speed?: number) => {
    await api.control(action, speed);
  };

  const handleGenerateCoas = async () => {
    setLoading('coas');
    try {
      const res = await api.generateCoas(state?.wave);
      setCoas(res.coas || []);
      setCoaWave(res.wave || 0);
      setExplanation(null);
      setSimResult(null);
    } finally {
      setLoading('');
    }
  };

  const handleExplain = async (coaId: string) => {
    setLoading('explain');
    try {
      const res = await api.explain(coaId);
      setExplanation(res);
    } finally {
      setLoading('');
    }
  };

  const handleSimulate = async (coaId: string) => {
    setLoading('simulate');
    try {
      const res = await api.simulate(coaId);
      setSimResult(res);
    } finally {
      setLoading('');
    }
  };

  const handleApprove = async (coaId: string) => {
    setLoading('approve');
    try {
      const res = await api.approve(coaId);
      setDecisions(prev => [...prev, res]);
    } finally {
      setLoading('');
    }
  };

  const handleSendCommand = async (input: string): Promise<CopilotResponse | null> => {
    try {
      const resp = await api.sendCommand(input, state?.source_state_id);
      if (resp.type === 'coas' && resp.data?.coas) {
        setCoas(resp.data.coas as CourseOfAction[]);
        setCoaWave((resp.data.wave as number) || state?.wave || 0);
        setExplanation(null);
        setSimResult(null);
      }
      return resp;
    } catch {
      return null;
    }
  };

  const handleAlertClick = (trackId: string) => {
    setSelectedTrack(trackId);
  };

  const handleReset = async () => {
    await api.control('reset');
    setCoas([]);
    setExplanation(null);
    setSimResult(null);
    setDecisions([]);
    setCoaWave(0);
    setFeedItems([]);
    lastFeedId.current = undefined;
    geoLoaded.current = false;
    setFollowTopThreat(false);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      const typing = t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable;
      if (typing && e.code === 'Space') return;
      if (e.code === 'Space' && !typing) {
        e.preventDefault();
        const s = stateRef.current;
        void api.control(s?.is_playing ? 'pause' : 'play');
      }
      if (typing) return;
      if (['Digit1', 'Digit2', 'Digit4', 'Digit8'].includes(e.code) && !e.ctrlKey && !e.metaKey) {
        const map: Record<string, number> = { Digit1: 1, Digit2: 2, Digit4: 4, Digit8: 8 };
        const sp = map[e.code];
        if (sp) void api.control('speed', sp);
      }
      if (e.key === 'g' || e.key === 'G') void handleGenerateCoas();
      if (e.key === 'w' || e.key === 'W') {
        const top = coas[0]?.coa_id;
        if (top) void handleExplain(top);
      }
      if (e.key === 's' || e.key === 'S') {
        const top = coas[0]?.coa_id;
        if (top) void handleSimulate(top);
      }
      if (e.key === 'b' || e.key === 'B') void handleSendCommand('/brief');
      if (e.key === 'r' || e.key === 'R') void handleSendCommand('/replan');
      if (e.key === 'f' || e.key === 'F') void handleSendCommand('/fit-theater');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [coas]);

  const bottomH = timelineCollapsed ? 52 : getBottomHeight(bottomMode);

  if (!loaded || !state) {
    return (
      <div className="loading-screen">
        <div className="loading-title">NEON COMMAND</div>
        <div className="loading-sub">Initializing tactical systems...</div>
      </div>
    );
  }

  return (
    <div
      className="app-layout"
      style={{
        gridTemplateRows: `48px 1fr ${bottomH}px`,
      }}
    >
      <header className="app-header">
        <div className="header-left">
          <span className="header-logo">◆</span>
          <span className="header-title">NEON COMMAND</span>
          <span className="header-sub">Smart Stridsledning</span>
        </div>
        <div className="header-center">
          <span className="header-scenario">{state.scenario_name || 'No Scenario'}</span>
          {state.wave > 0 && (
            <span className={`header-wave ${state.wave >= 2 ? 'wave-critical' : ''}`}>
              WAVE {state.wave}
            </span>
          )}
        </div>
        <div className="header-right">
          <div className="layout-presets" title="Layout presets">
            {(Object.keys(LAYOUT_PRESETS) as LayoutPresetId[]).map((id) => (
              <button
                key={id}
                type="button"
                className={`layout-preset-btn ${layoutPreset === id ? 'active' : ''}`}
                onClick={() => applyPreset(id)}
              >
                {LAYOUT_PRESETS[id].label}
              </button>
            ))}
            <button type="button" className="layout-reset-btn" onClick={() => applyPreset('balanced')}>
              Reset layout
            </button>
          </div>
          <span className="header-state-id">{state.source_state_id}</span>
        </div>
      </header>

      <div
        className="app-body"
        ref={bodyRef}
        style={{
          gridTemplateColumns: `${leftPx}px 6px 1fr 6px ${rightPx}px`,
        }}
      >
        <aside className="left-rail panel-rail">
          <AlertQueue
            alerts={alerts || []}
            sortedAlerts={sortedAlerts}
            selectedTrack={selectedTrack}
            onAlertClick={handleAlertClick}
          />
        </aside>

        <div
          className="col-resizer"
          role="separator"
          aria-orientation="vertical"
          onMouseDown={onDividerMouseDown('left')}
          onDoubleClick={onDividerDoubleClick}
        />

        <main className="center-map">
          <TacticalMap
            geography={geo}
            tracks={state.tracks}
            assets={state.assets}
            selectedTrack={selectedTrack}
            onSelectTrack={setSelectedTrack}
            coas={coas}
            followTopThreat={followTopThreat}
            onFollowTopThreatChange={setFollowTopThreat}
            topThreatTrackId={topThreatTrackId}
          />
        </main>

        <div
          className="col-resizer"
          role="separator"
          aria-orientation="vertical"
          onMouseDown={onDividerMouseDown('right')}
          onDoubleClick={onDividerDoubleClick}
        />

        <aside className="right-rail panel-rail">
          <CopilotPanel
            state={state}
            coas={coas}
            coaWave={coaWave}
            explanation={explanation}
            simResult={simResult}
            decisions={decisions}
            loading={loading}
            feedItems={feedItems}
            copilotStatus={copilotStatus}
            alerts={sortedAlerts}
            selectedTrack={selectedTrack}
            onGenerateCoas={handleGenerateCoas}
            onExplain={handleExplain}
            onSimulate={handleSimulate}
            onApprove={handleApprove}
            onSendCommand={handleSendCommand}
          />
        </aside>
      </div>

      <footer className={`bottom-bar ${timelineCollapsed ? 'collapsed' : ''}`}>
        <div className="timeline-size-controls">
          <button type="button" className={bottomMode === 'compact' ? 'active' : ''} onClick={() => { setBottomMode('compact'); setTimelineCollapsed(false); }}>S</button>
          <button type="button" className={bottomMode === 'normal' ? 'active' : ''} onClick={() => { setBottomMode('normal'); setTimelineCollapsed(false); }}>M</button>
          <button type="button" className={bottomMode === 'expanded' ? 'active' : ''} onClick={() => { setBottomMode('expanded'); setTimelineCollapsed(false); }}>L</button>
          <button type="button" title="Collapse timeline" onClick={() => setTimelineCollapsed(c => !c)}>▾</button>
        </div>
        <Timeline
          currentTime={state.current_time_s}
          isPlaying={state.is_playing}
          speed={state.speed_multiplier}
          eventsLog={state.events_log}
          coaTriggerPending={state.coa_trigger_pending}
          onControl={handleControl}
          onReset={handleReset}
          compact={bottomMode === 'compact' || timelineCollapsed}
        />
      </footer>
    </div>
  );
}
