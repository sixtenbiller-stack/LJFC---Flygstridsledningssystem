import './MapToolbar.css';

export interface MapLayerToggles {
  coverage: boolean;
  predictedPaths: boolean;
  terrainLabels: boolean;
  defendedZones: boolean;
}

interface Props {
  zoomPct: number;
  followTopThreat: boolean;
  layers: MapLayerToggles;
  onFitTheater: () => void;
  onFocusSelection: () => void;
  onToggleFollow: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onLayerToggle: (key: keyof MapLayerToggles) => void;
  minimal?: boolean;
  activeTool?: 'select' | 'place';
  onToolChange?: (tool: 'select' | 'place') => void;
}

export function MapToolbar({
  zoomPct,
  followTopThreat,
  layers,
  onFitTheater,
  onFocusSelection,
  onToggleFollow,
  onZoomIn,
  onZoomOut,
  onLayerToggle,
  minimal = false,
  activeTool,
  onToolChange,
}: Props) {
  return (
    <div className="map-toolbar">
      {minimal && onToolChange && (
        <div className="map-toolbar-group tools">
          <button 
            type="button" 
            className={`map-tb-btn ${activeTool === 'select' ? 'active' : ''}`}
            onClick={() => onToolChange('select')}
          >
            Selection Tool
          </button>
          <button 
            type="button" 
            className={`map-tb-btn ${activeTool === 'place' ? 'active' : ''}`}
            onClick={() => onToolChange('place')}
          >
            Placement Tool
          </button>
        </div>
      )}
      {!minimal && (
        <div className="map-toolbar-group">
          <button type="button" className="map-tb-btn" onClick={onFitTheater} title="Fit entire theater">
            Fit theater
          </button>
          <button type="button" className="map-tb-btn" onClick={onFocusSelection} title="Zoom to selected track">
            Focus selection
          </button>
          <button
            type="button"
            className={`map-tb-btn ${followTopThreat ? 'active' : ''}`}
            onClick={onToggleFollow}
            title="Auto-select highest-priority threat"
          >
            Follow top threat
          </button>
        </div>
      )}
      <div className="map-toolbar-group">
        <button type="button" className="map-tb-btn icon" onClick={onZoomOut} title="Zoom out">−</button>
        <span className="map-zoom-readout">{zoomPct}%</span>
        <button type="button" className="map-tb-btn icon" onClick={onZoomIn} title="Zoom in">+</button>
      </div>
      {!minimal && (
        <div className="map-toolbar-group layers">
          <label className="map-tb-check">
            <input type="checkbox" checked={layers.coverage} onChange={() => onLayerToggle('coverage')} />
            Coverage
          </label>
          <label className="map-tb-check">
            <input type="checkbox" checked={layers.predictedPaths} onChange={() => onLayerToggle('predictedPaths')} />
            Paths
          </label>
          <label className="map-tb-check">
            <input type="checkbox" checked={layers.defendedZones} onChange={() => onLayerToggle('defendedZones')} />
            Zones
          </label>
          <label className="map-tb-check">
            <input type="checkbox" checked={layers.terrainLabels} onChange={() => onLayerToggle('terrainLabels')} />
            Labels
          </label>
        </div>
      )}
    </div>
  );
}
