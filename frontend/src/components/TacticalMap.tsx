import { useMemo, useState, useCallback, useRef, useEffect } from 'react';
import type { Geography, Track, Asset, CourseOfAction } from '../types';
import { MapToolbar, type MapLayerToggles } from './MapToolbar';
import './TacticalMap.css';

interface Props {
  geography: Geography | null;
  tracks: Track[];
  assets: Asset[];
  selectedTrack: string | null;
  onSelectTrack: (id: string | null) => void;
  coas: CourseOfAction[];
  followTopThreat: boolean;
  onFollowTopThreatChange: (v: boolean) => void;
  topThreatTrackId: string | null;
  highlightTrackIds?: string[];
  /** Changes when a new feed event arrives — triggers a brief track highlight pulse */
  feedActivityKey?: string;
}

const BOUNDS = { xMin: 0, xMax: 400, yMin: 0, yMax: 600 };
const PADDING = 30;
const VIEW_W = 460;
const VIEW_H = 660;

function toSvg(xKm: number, yKm: number): [number, number] {
  const x = PADDING + ((xKm - BOUNDS.xMin) / (BOUNDS.xMax - BOUNDS.xMin)) * (VIEW_W - 2 * PADDING);
  const y = PADDING + ((BOUNDS.yMax - yKm) / (BOUNDS.yMax - BOUNDS.yMin)) * (VIEW_H - 2 * PADDING);
  return [x, y];
}

function polyToSvg(poly: number[][]): string {
  return poly.map(([x, y]) => toSvg(x, y).join(',')).join(' ');
}

const ICON: Record<string, string> = {
  air_base: '✦',
  city: '●',
  sam_site: '◈',
  sensor_site: '◎',
  fighter: '▲',
  uav: '△',
  sam_battery: '◆',
};

function headingArrow(deg: number, len: number): [number, number] {
  const rad = ((deg - 90) * Math.PI) / 180;
  return [Math.cos(rad) * len, -Math.sin(rad) * len];
}

const DEFAULT_LAYERS: MapLayerToggles = {
  coverage: true,
  predictedPaths: true,
  terrainLabels: true,
  defendedZones: true,
};

export function TacticalMap({
  geography, tracks, assets, selectedTrack, onSelectTrack, coas,
  followTopThreat, onFollowTopThreatChange, topThreatTrackId,
  highlightTrackIds = [],
  feedActivityKey,
}: Props) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [layers, setLayers] = useState<MapLayerToggles>(DEFAULT_LAYERS);
  const [feedPulse, setFeedPulse] = useState(false);
  const panning = useRef(false);
  const panStart = useRef({ x: 0, y: 0, px: 0, py: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const trackGroupRefs = useRef<Record<string, SVGGElement | null>>({});
  const lastActivityKey = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!feedActivityKey || feedActivityKey === lastActivityKey.current) return;
    lastActivityKey.current = feedActivityKey;
    setFeedPulse(true);
    const t = window.setTimeout(() => setFeedPulse(false), 700);
    return () => clearTimeout(t);
  }, [feedActivityKey]);

  const assignedAssets = useMemo(() => {
    const set = new Set<string>();
    for (const coa of coas) {
      for (const a of coa.actions) set.add(a.asset_id);
    }
    return set;
  }, [coas]);

  const zoomPct = Math.round(zoom * 100);

  const fitTheater = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  const focusSelection = useCallback(() => {
    if (!selectedTrack || !containerRef.current) return;
    const g = trackGroupRefs.current[selectedTrack];
    const container = containerRef.current;
    if (!g) return;
    const gr = g.getBoundingClientRect();
    const cr = container.getBoundingClientRect();
    const tcx = gr.left + gr.width / 2 - cr.left;
    const tcy = gr.top + gr.height / 2 - cr.top;
    const cx = cr.width / 2;
    const cy = cr.height / 2;
    setPan(p => ({ x: p.x + (cx - tcx), y: p.y + (cy - tcy) }));
    setZoom(z => Math.max(1.2, Math.min(2.2, z * 1.15)));
  }, [selectedTrack]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'f' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        focusSelection();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [focusSelection]);

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = -e.deltaY * 0.0015;
    setZoom(z => Math.min(2.5, Math.max(0.45, z + delta)));
  }, []);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    const t = e.target as HTMLElement;
    if (t.closest('.hostile-track') || t.closest('.map-toolbar')) return;
    panning.current = true;
    panStart.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y };
  }, [pan.x, pan.y]);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!panning.current) return;
      const dx = e.clientX - panStart.current.x;
      const dy = e.clientY - panStart.current.y;
      setPan({ x: panStart.current.px + dx, y: panStart.current.py + dy });
    };
    const onUp = () => { panning.current = false; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  const showDetailLabels = zoom >= 0.85;

  const toggleLayer = (key: keyof MapLayerToggles) => {
    setLayers(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (!geography) {
    return <div className="map-empty">Loading tactical display...</div>;
  }

  return (
    <div
      className="tactical-map-container"
      ref={containerRef}
      onWheel={onWheel}
    >
      <MapToolbar
        zoomPct={zoomPct}
        followTopThreat={followTopThreat}
        layers={layers}
        onFitTheater={fitTheater}
        onFocusSelection={focusSelection}
        onToggleFollow={() => onFollowTopThreatChange(!followTopThreat)}
        onZoomIn={() => setZoom(z => Math.min(2.5, z * 1.12))}
        onZoomOut={() => setZoom(z => Math.max(0.45, z / 1.12))}
        onLayerToggle={toggleLayer}
      />
      <div
        className="map-transform-layer"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: 'center center',
        }}
        onMouseDown={onMouseDown}
      >
        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          className={`tactical-map-svg${selectedTrack ? ' has-selection' : ''}`}
          onClick={() => onSelectTrack(null)}
        >
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="glow-strong">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {Array.from({ length: 9 }, (_, i) => {
            const x = PADDING + ((i * 50) / (BOUNDS.xMax - BOUNDS.xMin)) * (VIEW_W - 2 * PADDING);
            return <line key={`gx${i}`} x1={x} y1={PADDING} x2={x} y2={VIEW_H - PADDING} className="grid-line" />;
          })}
          {Array.from({ length: 13 }, (_, i) => {
            const y = PADDING + ((i * 50) / (BOUNDS.yMax - BOUNDS.yMin)) * (VIEW_H - 2 * PADDING);
            return <line key={`gy${i}`} x1={PADDING} y1={y} x2={VIEW_W - PADDING} y2={y} className="grid-line" />;
          })}

          {geography.terrain.map((t) => {
            const pts = polyToSvg(t.polygon_km);
            return (
              <polygon key={t.id} points={pts} className={`terrain terrain-${t.type}`} />
            );
          })}

          {layers.defendedZones && geography.defended_zones.map((z) => {
            const [cx, cy] = toSvg(z.center_km[0], z.center_km[1]);
            const r = (z.radius_km / (BOUNDS.xMax - BOUNDS.xMin)) * (VIEW_W - 2 * PADDING);
            return (
              <g key={z.id}>
                <circle cx={cx} cy={cy} r={r} className={`zone zone-p${z.priority}`} />
                {showDetailLabels && (
                  <text x={cx} y={cy - r - 4} className="zone-label">{z.name.replace(' Defence Zone', '').replace(' Zone', '')}</text>
                )}
              </g>
            );
          })}

          {layers.coverage && geography.features.filter(f => f.type === 'sam_site').map(f => {
            const [cx, cy] = toSvg(f.x_km, f.y_km);
            const r = ((f.coverage_radius_km || 0) / (BOUNDS.xMax - BOUNDS.xMin)) * (VIEW_W - 2 * PADDING);
            return <circle key={`sam-cov-${f.id}`} cx={cx} cy={cy} r={r} className="sam-coverage" />;
          })}

          {layers.coverage && geography.features.filter(f => f.type === 'sensor_site').map(f => {
            const [cx, cy] = toSvg(f.x_km, f.y_km);
            const r = ((f.detection_range_km || 0) / (BOUNDS.xMax - BOUNDS.xMin)) * (VIEW_W - 2 * PADDING);
            return <circle key={`sensor-cov-${f.id}`} cx={cx} cy={cy} r={r} className="sensor-coverage" />;
          })}

          {geography.features.map((f) => {
            const [x, y] = toSvg(f.x_km, f.y_km);
            const showLab = layers.terrainLabels && showDetailLabels;
            return (
              <g key={f.id}>
                <text x={x} y={y + 4} className={`feature-icon feature-${f.type}`} textAnchor="middle">
                  {ICON[f.type] || '○'}
                </text>
                {showLab && (
                  <text x={x} y={y + 14} className="feature-label" textAnchor="middle">
                    {f.name.length > 18 ? f.name.slice(0, 16) + '…' : f.name}
                  </text>
                )}
              </g>
            );
          })}

          {assets.map((a) => {
            const [x, y] = toSvg(a.current_location.x_km, a.current_location.y_km);
            const isAssigned = assignedAssets.has(a.asset_id);
            const statusClass = a.status === 'recovering' ? 'asset-recovering'
              : a.status === 'active' ? 'asset-active'
              : isAssigned ? 'asset-assigned' : '';
            return (
              <g key={a.asset_id} className={`asset ${statusClass}`}>
                <text x={x + (assets.indexOf(a) % 4) * 4 - 6} y={y - 8} className="asset-icon" textAnchor="middle">
                  {ICON[a.asset_type] || '◇'}
                </text>
              </g>
            );
          })}

          {layers.predictedPaths && tracks.filter(t => t.side === 'hostile' && t.predicted_path.length > 1).map(t => {
            const pathStr = t.predicted_path
              .map(p => toSvg(p.x_km, p.y_km).join(','))
              .join(' ');
            return (
              <polyline key={`path-${t.track_id}`} points={pathStr} className="track-predicted-path" />
            );
          })}

          {tracks.filter(t => t.side === 'hostile').map(t => {
            const [x, y] = toSvg(t.x_km, t.y_km);
            const isSelected = selectedTrack === t.track_id;
            const [dx, dy] = headingArrow(t.heading_deg, 14);
            const threatClass = t.confidence >= 0.8 ? 'track-high' : t.confidence >= 0.6 ? 'track-medium' : 'track-low';
            const isTop = topThreatTrackId === t.track_id;
            const isGrouped = highlightTrackIds.includes(t.track_id);
            return (
              <g
                key={t.track_id}
                ref={(el) => { trackGroupRefs.current[t.track_id] = el; }}
                className={`hostile-track ${threatClass} ${isSelected ? 'track-selected' : ''} ${isTop ? 'track-top-threat' : ''} ${isGrouped ? 'track-group-highlight' : ''} ${feedPulse ? 'track-feed-pulse' : ''}`}
                onClick={(e) => { e.stopPropagation(); onSelectTrack(t.track_id); }}
                style={{ cursor: 'pointer' }}
              >
                {isGrouped && <circle cx={x} cy={y} r={12} className="track-group-ring" />}
                <line x1={x} y1={y} x2={x + dx} y2={y + dy} className="track-heading" />
                <circle cx={x} cy={y} r={isSelected ? 7 : 5} className="track-dot" />
                {(showDetailLabels || isSelected || isTop) && (
                  <text x={x + 10} y={y - 6} className="track-label">
                    {t.track_id} [{t.class_label}]
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
