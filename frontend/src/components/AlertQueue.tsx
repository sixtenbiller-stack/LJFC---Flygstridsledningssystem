import { useMemo, useState } from 'react';
import type { ThreatAlert } from '../types';
import './AlertQueue.css';

type BandFilter = 'all' | 'critical' | 'high' | 'medium' | 'low';
type SortMode = 'priority' | 'eta' | 'score';

interface Props {
  alerts: ThreatAlert[];
  sortedAlerts: ThreatAlert[];
  selectedTrack: string | null;
  onAlertClick: (trackId: string) => void;
}

const BAND_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export function AlertQueue({
  alerts, sortedAlerts, selectedTrack, onAlertClick,
}: Props) {
  const [band, setBand] = useState<BandFilter>('all');
  const [sortMode, setSortMode] = useState<SortMode>('priority');

  const displayList = useMemo(() => {
    let list = [...sortedAlerts];
    if (band !== 'all') {
      list = list.filter(a => a.priority_band === band);
    }
    if (sortMode === 'eta') {
      list.sort((a, b) => (a.eta_s ?? 9999) - (b.eta_s ?? 9999));
    } else if (sortMode === 'score') {
      list.sort((a, b) => b.threat_score - a.threat_score);
    } else {
      list.sort((a, b) => {
        const ba = BAND_ORDER[a.priority_band] ?? 4;
        const bb = BAND_ORDER[b.priority_band] ?? 4;
        if (ba !== bb) return ba - bb;
        return b.threat_score - a.threat_score;
      });
    }
    return list;
  }, [sortedAlerts, band, sortMode]);

  const topThreat = sortedAlerts[0];

  return (
    <div className="alert-queue">
      <div className="alert-queue-header">
        <span className="aq-title">THREAT QUEUE</span>
        <span className="aq-count">{alerts.length} tracks</span>
      </div>

      <div className="aq-toolbar">
        <div className="aq-filters" role="tablist" aria-label="Threat band filter">
          {(['all', 'critical', 'high', 'medium', 'low'] as const).map(b => (
            <button
              key={b}
              type="button"
              className={`aq-filter ${band === b ? 'active' : ''}`}
              onClick={() => setBand(b)}
            >
              {b === 'all' ? 'All' : b.charAt(0).toUpperCase() + b.slice(1)}
            </button>
          ))}
        </div>
        <div className="aq-sort">
          <span className="aq-sort-label">Sort</span>
          <select
            className="aq-sort-select"
            value={sortMode}
            onChange={e => setSortMode(e.target.value as SortMode)}
            aria-label="Sort threats"
          >
            <option value="priority">Priority</option>
            <option value="eta">ETA</option>
            <option value="score">Score</option>
          </select>
        </div>
      </div>

      {alerts.length === 0 && (
        <div className="aq-empty">No threats detected — start playback or use <span className="aq-mono">/brief</span></div>
      )}

      {alerts.length > 0 && topThreat && (
        <div className="aq-pinned">
          <div className="aq-pinned-label">Top threat</div>
          <button
            type="button"
            className={`aq-pinned-card band-${topThreat.priority_band} ${selectedTrack === topThreat.track_id ? 'selected' : ''}`}
            onClick={() => onAlertClick(topThreat.track_id)}
          >
            <span className="aq-pinned-id">{topThreat.track_id}</span>
            <span className="aq-pinned-meta">
              {(topThreat.threat_score * 100).toFixed(0)}%
              {topThreat.eta_s != null ? ` · ETA ${Math.round(topThreat.eta_s)}s` : ''}
            </span>
          </button>
        </div>
      )}

      {alerts.length > 0 && displayList.length === 0 && (
        <div className="aq-empty">No threats match filters</div>
      )}

      {(topThreat ? displayList.filter(a => a.track_id !== topThreat.track_id) : displayList).map(a => {
        const isSelected = selectedTrack === a.track_id;
        return (
          <div
            key={a.track_id}
            className={`alert-card band-${a.priority_band} ${isSelected ? 'selected' : ''}`}
            onClick={() => onAlertClick(a.track_id)}
          >
            <div className="alert-top">
              <span className="alert-track-id">{a.track_id}</span>
              <span className={`alert-band band-${a.priority_band}`}>{a.priority_band.toUpperCase()}</span>
            </div>
            <div className="alert-class">{a.class_label}</div>
            <div className="alert-details">
              <div className="alert-detail">
                <span className="alert-detail-label">Score</span>
                <span className="alert-detail-value">{(a.threat_score * 100).toFixed(0)}%</span>
              </div>
              <div className="alert-detail">
                <span className="alert-detail-label">Conf</span>
                <span className="alert-detail-value">{(a.confidence * 100).toFixed(0)}%</span>
              </div>
              {a.eta_s != null && (
                <div className="alert-detail">
                  <span className="alert-detail-label">ETA</span>
                  <span className="alert-detail-value">{Math.round(a.eta_s)}s</span>
                </div>
              )}
              <div className="alert-detail">
                <span className="alert-detail-label">Spd</span>
                <span className="alert-detail-value">{a.speed_class}</span>
              </div>
            </div>
            {a.nearest_zone_id && (
              <div className="alert-zone">→ {a.nearest_zone_id.replace('zone-', '')}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}
