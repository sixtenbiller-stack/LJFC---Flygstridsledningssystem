import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { api } from './api/client';
import { usePolling } from './hooks/usePolling';
import type {
  ScenarioState, ThreatAlert, CourseOfAction, SimulationResult,
  ExplanationData, AuditRecord, Geography, FeedItem, CopilotResponse,
  CopilotStatusData, ThreatGroup, DecisionCard as DecisionCardType,
  ScenarioSession, TimelineMarker,
} from './types';
import { TacticalMap } from './components/TacticalMap';
import { AlertQueue } from './components/AlertQueue';
import { GroupQueue } from './components/GroupQueue';
import { CopilotPanel } from './components/CopilotPanel';
import { DecisionCard } from './components/DecisionCard';
import { ScenarioLab } from './components/ScenarioLab';
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
  const [groups, setGroups] = useState<ThreatGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [decisionCard, setDecisionCard] = useState<DecisionCardType | null>(null);
  const [leftView, setLeftView] = useState<'tracks' | 'groups'>('tracks');
  const [runtimeMode, setRuntimeMode] = useState<string>('replay');
  const [scenarioOrigin, setScenarioOrigin] = useState<string>('builtin');
  const [session, setSession] = useState<ScenarioSession | null>(null);
  const [markers, setMarkers] = useState<TimelineMarker[]>([]);
  const [layoutPreset, setLayoutPreset] = useState<LayoutPresetId>('balanced');
  const [mainTab, setMainTab] = useState<'product' | 'lab'>('product');
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
    if (result.runtime_mode) setRuntimeMode(result.runtime_mode);
    if (result.scenario_origin) setScenarioOrigin(result.scenario_origin);
    return result;
  }, []);
  const fetchAlerts = useCallback(() => api.getAlerts(), []);

  const prevGroupCount = useRef(0);
  const fetchGroups = useCallback(async () => {
    try {
      const g: ThreatGroup[] = await api.getGroups();
      setGroups(g);
      if (g.length > 0 && leftView === 'tracks') {
        setLeftView('groups');
      }
      if (g.length > 0 && prevGroupCount.current === 0) {
        const topGroup = g[0];
        setSelectedGroup(topGroup.group_id);
        if (topGroup.member_track_ids.length > 0) {
          setSelectedTrack(topGroup.member_track_ids[0]);
        }
        try {
          const card: DecisionCardType = await api.getDecisionCard(topGroup.group_id);
          if (!('error' in card)) setDecisionCard(card);
        } catch { /* skip */ }
      }
      prevGroupCount.current = g.length;
    } catch { /* skip */ }
  }, [leftView]);

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
    const interval = setInterval(fetchGroups, 1500);
    return () => clearInterval(interval);
  }, [fetchGroups]);

  const refreshSession = useCallback(async () => {
    try {
      const s: ScenarioSession = await api.getSession();
      setSession(s);
      setRuntimeMode(s.runtime_mode || 'replay');
      setScenarioOrigin(s.scenario_origin || 'builtin');
    } catch { /* skip */ }
    try {
      const m: TimelineMarker[] = await api.getMarkers();
      setMarkers(m);
    } catch { /* skip */ }
  }, []);

  const handleScenarioLoaded = useCallback(async () => {
    setCoas([]);
    setExplanation(null);
    setSimResult(null);
    setDecisions([]);
    setCoaWave(0);
    setFeedItems([]);
    lastFeedId.current = undefined;
    geoLoaded.current = false;
    setFollowTopThreat(false);
    setGroups([]);
    setSelectedGroup(null);
    setDecisionCard(null);
    setLeftView('tracks');
    prevGroupCount.current = 0;
    await refreshSession();
    api.getCopilotStatus().then(setCopilotStatus).catch(() => {});
  }, [refreshSession]);

  useEffect(() => {
    // Only load a default scenario if one isn't already active on the server
    const init = async () => {
      try {
        const currentState = await api.getState();
        if (!currentState.scenario_id) {
          await api.loadScenario('scenario-alpha');
        }
      } catch {
        await api.loadScenario('scenario-alpha');
      }
      setLoaded(true);
      api.getCopilotStatus().then(setCopilotStatus).catch(() => {});
      refreshSession();
    };
    init();
  }, [refreshSession]);

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

  /* Scaling options internal use */
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

  const handleGroupClick = async (groupId: string) => {
    setSelectedGroup(groupId);
    try {
      const card: DecisionCardType = await api.getDecisionCard(groupId);
      if (!('error' in card)) {
        setDecisionCard(card);
        const g = groups.find(g => g.group_id === groupId);
        if (g && g.member_track_ids.length > 0) {
          setSelectedTrack(g.member_track_ids[0]);
        }
      }
    } catch { /* skip */ }
  };

  const handleGroupApprove = async (groupId: string, responseId: string) => {
    setLoading('group-approve');
    try {
      await api.approveGroupResponse(groupId, responseId, 'approve');
    } finally {
      setLoading('');
    }
  };

  const handleGroupDefer = async (groupId: string) => {
    try {
      await api.approveGroupResponse(groupId, '', 'defer');
    } catch { /* skip */ }
  };

  const handleGroupOverride = async (groupId: string, responseId: string, reason: string) => {
    setLoading('group-approve');
    try {
      await api.approveGroupResponse(groupId, responseId, 'override', reason);
    } finally {
      setLoading('');
    }
  };

  const handleJump = async (target: string) => {
    try {
      await api.jumpTo(target);
    } catch { /* skip */ }
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
    setGroups([]);
    setSelectedGroup(null);
    setDecisionCard(null);
    setLeftView('tracks');
    prevGroupCount.current = 0;
    await refreshSession();
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
      className={`app-layout ${mainTab === 'lab' ? 'lab-mode' : ''}`}
      style={{
        gridTemplateRows: mainTab === 'lab' ? '48px 1fr' : '48px 1fr 48px',
      }}
    >
      <header className="app-header">
        <div className="header-left">
          <span className="header-logo">◆</span>
          <span className="header-title">NEON COMMAND</span>
          <div className="app-main-tabs">
            <button
              className={`main-tab-btn ${mainTab === 'product' ? 'active' : ''}`}
              onClick={() => setMainTab('product')}
            >
              PRODUCT
            </button>
            <button
              className={`main-tab-btn ${mainTab === 'lab' ? 'active' : ''}`}
              onClick={() => setMainTab('lab')}
            >
              SCENARIO LAB
            </button>
          </div>
        </div>
        <div className="header-center">
          <span className="header-scenario">{state.scenario_name || 'No Scenario'}</span>
          <span className={`header-mode-badge mode-${runtimeMode}`}>{runtimeMode.toUpperCase()}</span>
          <span className={`header-origin-badge origin-${scenarioOrigin}`}>{scenarioOrigin.toUpperCase().replace('_', ' ')}</span>
          {state.wave > 0 && (
            <span className={`header-wave ${state.wave >= 2 ? 'wave-critical' : ''}`}>
              WAVE {state.wave}
            </span>
          )}
        </div>
        <div className="header-right">
          <span className="header-state-id">{state.source_state_id}</span>
        </div>
      </header>

      {mainTab === 'product' ? (
        <div
          className="app-body"
          ref={bodyRef}
          style={{
            gridTemplateColumns: `${leftPx}px 6px 1fr 6px ${rightPx}px`,
          }}
        >
          <aside className="left-rail panel-rail">
            <div className="left-view-toggle">
              <button
                type="button"
                className={`lv-tab ${leftView === 'tracks' ? 'active' : ''}`}
                onClick={() => setLeftView('tracks')}
              >
                TRACKS
              </button>
              <button
                type="button"
                className={`lv-tab ${leftView === 'groups' ? 'active' : ''}`}
                onClick={() => setLeftView('groups')}
              >
                GROUPS{groups.length > 0 ? ` (${groups.length})` : ''}
              </button>
            </div>
            {leftView === 'tracks' ? (
              <AlertQueue
                alerts={alerts || []}
                sortedAlerts={sortedAlerts}
                selectedTrack={selectedTrack}
                onAlertClick={handleAlertClick}
              />
            ) : (
              <GroupQueue
                groups={groups}
                selectedGroup={selectedGroup}
                onGroupClick={handleGroupClick}
              />
            )}
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
              highlightTrackIds={selectedGroup ? (groups.find(g => g.group_id === selectedGroup)?.member_track_ids ?? []) : []}
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
            {decisionCard && selectedGroup && (
              <div className="dc-container">
                <DecisionCard
                  card={decisionCard}
                  onApprove={handleGroupApprove}
                  onDefer={handleGroupDefer}
                  onOverride={handleGroupOverride}
                  onGenerateCoas={handleGenerateCoas}
                  onSimulate={handleSimulate}
                  loading={loading}
                />
              </div>
            )}
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
              groups={groups}
              selectedGroup={selectedGroup}
              decisionCard={decisionCard}
              scenarioMode={runtimeMode}
              scenarioOrigin={scenarioOrigin}
              onGenerateCoas={handleGenerateCoas}
              onExplain={handleExplain}
              onSimulate={handleSimulate}
              onApprove={handleApprove}
              onSendCommand={handleSendCommand}
            />
          </aside>
        </div>
      ) : (
        <div className="app-body-lab">
          <ScenarioLab
            currentScenarioId={state.scenario_id}
            currentMode={runtimeMode}
            currentOrigin={scenarioOrigin}
            isPlaying={state.is_playing}
            speed={state.speed_multiplier}
            session={session}
            markers={markers}
            geography={geo}
            onScenarioLoaded={() => {
              handleScenarioLoaded();
              setMainTab('product');
            }}
            onControl={handleControl}
            onReset={handleReset}
          />
        </div>
      )}

      <footer className="bottom-bar">
        <Timeline
          currentTime={state.current_time_s}
          duration={session?.duration_s ?? 240}
          isPlaying={state.is_playing}
          speed={state.speed_multiplier}
          eventsLog={state.events_log}
          coaTriggerPending={state.coa_trigger_pending}
          onControl={handleControl}
          onReset={handleReset}
          onJump={handleJump}
          onSeek={(t: number) => api.seekTo(t)}
          markers={markers}
          mode={runtimeMode}
          compact={true}
        />
      </footer>
    </div>
  );
}
