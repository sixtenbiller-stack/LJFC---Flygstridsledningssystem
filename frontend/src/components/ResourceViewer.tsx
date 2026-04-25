import React from 'react';
import './ResourceViewer.css';

interface ResourceSpec {
  id: string;
  name: string;
  type: string;
  capabilities?: string[];
  max_speed?: string;
  munitions_loadout?: string[];
  endurance_min?: number;
  payload_capacity?: string;
  range_class?: string;
  guidance?: string;
  usage?: string;
  platform?: string;
}

interface ResourceCatalogue {
  aircraft: {
    fighters: ResourceSpec[];
    drones: ResourceSpec[];
    bombers: ResourceSpec[];
  };
  weapons: {
    missiles: ResourceSpec[];
    bullets: ResourceSpec[];
  };
}

interface ResourceViewerProps {
  resources: ResourceCatalogue | null;
}

export const ResourceViewer: React.FC<ResourceViewerProps> = ({ resources }) => {
  if (!resources) return <div className="rv-loading">Loading resources...</div>;

  const renderSection = (title: string, items: ResourceSpec[]) => {
    if (!items || items.length === 0) return null;
    return (
      <div className="rv-section">
        <h3 className="rv-section-title">{title}</h3>
        <div className="rv-grid">
          {items.map(item => (
            <div key={item.id} className="rv-card">
              <div className="rv-card-header">
                <span className="rv-id">{item.id}</span>
                <span className="rv-type">{item.type}</span>
              </div>
              <div className="rv-name">{item.name}</div>
              <div className="rv-details">
                {item.capabilities && (
                  <div className="rv-detail">
                    <span className="rv-label">Capabilities:</span> {item.capabilities.join(', ')}
                  </div>
                )}
                {item.max_speed && (
                  <div className="rv-detail">
                    <span className="rv-label">Max Speed:</span> {item.max_speed}
                  </div>
                )}
                {item.munitions_loadout && item.munitions_loadout.length > 0 && (
                  <div className="rv-detail">
                    <span className="rv-label">Loadout:</span> {item.munitions_loadout.join(', ')}
                  </div>
                )}
                {item.endurance_min && (
                  <div className="rv-detail">
                    <span className="rv-label">Endurance:</span> {item.endurance_min} min
                  </div>
                )}
                {item.payload_capacity && (
                  <div className="rv-detail">
                    <span className="rv-label">Payload:</span> {item.payload_capacity}
                  </div>
                )}
                {item.range_class && (
                  <div className="rv-detail">
                    <span className="rv-label">Range:</span> {item.range_class}
                  </div>
                )}
                {item.guidance && (
                  <div className="rv-detail">
                    <span className="rv-label">Guidance:</span> {item.guidance}
                  </div>
                )}
                {item.usage && (
                  <div className="rv-detail">
                    <span className="rv-label">Usage:</span> {item.usage}
                  </div>
                )}
                {item.platform && (
                  <div className="rv-detail">
                    <span className="rv-label">Platform:</span> {item.platform}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="resource-viewer">
      <div className="rv-header">TACTICAL RESOURCE CATALOGUE</div>
      <div className="rv-content">
        <h2 className="rv-group-title">AIRCRAFT</h2>
        {renderSection('Fighters', resources.aircraft.fighters)}
        {renderSection('Drones', resources.aircraft.drones)}
        {renderSection('Bombers', resources.aircraft.bombers)}
        
        <h2 className="rv-group-title">WEAPONS</h2>
        {renderSection('Missiles', resources.weapons.missiles)}
        {renderSection('Bullets / Ammo', resources.weapons.bullets)}
      </div>
    </div>
  );
};
