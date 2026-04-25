import './MapToolbar.css';

import { useState } from 'react';

export interface MapLayerToggles {
  coverage: boolean;
  predictedPaths: boolean;
  terrainLabels: boolean;
  defendedZones: boolean;
}

interface Props {
  zoomPct: number;
  layers: MapLayerToggles;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onLayerToggle: (key: keyof MapLayerToggles) => void;
  // Hamburger props
  scenarioName?: string;
  runtimeMode: string;
  scenarioOrigin: string;
  wave: number;
  stateId: string;
  layoutPreset: string;
  onApplyPreset: (id: any) => void;
}

export function MapToolbar({
  zoomPct,
  layers,
  onZoomIn,
  onZoomOut,
  onLayerToggle,
  scenarioName,
  runtimeMode,
  scenarioOrigin,
  wave,
  stateId,
  layoutPreset,
  onApplyPreset,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="map-toolbar">
      <div className="map-toolbar-left">
        <div className="hamburger-menu">
          <button
            type="button"
            className="hamburger-btn"
            onClick={() => setMenuOpen(!menuOpen)}
            title="Menu"
          >
            ☰
          </button>
          {menuOpen && (
            <div className="hamburger-dropdown">
              <div className="dropdown-section">
                <span className="dropdown-label">Tactical Info</span>
                <div className="dropdown-scenario-info">
                  <span className="dropdown-scenario-name">{scenarioName || 'No Scenario'}</span>
                  <div className="dropdown-badges">
                    <span className={`header-mode-badge mode-${runtimeMode}`}>{runtimeMode.toUpperCase()}</span>
                    <span className={`header-origin-badge origin-${scenarioOrigin}`}>{scenarioOrigin.toUpperCase().replace('_', ' ')}</span>
                    {wave > 0 && (
                      <span className={`header-wave ${wave >= 2 ? 'wave-critical' : ''}`}>
                        WAVE {wave}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="dropdown-section">
                <span className="dropdown-label">Layout Presets</span>
                <div className="layout-presets">
                  {['balanced', 'combat', 'intelligence'].map((id) => (
                    <button
                      key={id}
                      type="button"
                      className={`layout-preset-btn ${layoutPreset === id ? 'active' : ''}`}
                      onClick={() => {
                        onApplyPreset(id);
                        setMenuOpen(false);
                      }}
                    >
                      {id.charAt(0).toUpperCase() + id.slice(1)}
                    </button>
                  ))}
                  <button
                    type="button"
                    className="layout-reset-btn"
                    onClick={() => {
                      onApplyPreset('balanced');
                      setMenuOpen(false);
                    }}
                  >
                    Reset layout
                  </button>
                </div>
              </div>

              <div className="dropdown-section">
                <span className="dropdown-label">System</span>
                <span className="header-state-id">{stateId}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="map-toolbar-right">
        <div className="map-toolbar-group zoom-group">
          <button type="button" className="map-tb-btn icon" onClick={onZoomOut} title="Zoom out">−</button>
          <span className="map-zoom-readout">{zoomPct}%</span>
          <button type="button" className="map-tb-btn icon" onClick={onZoomIn} title="Zoom in">+</button>
        </div>
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
      </div>
    </div>
  );
}
