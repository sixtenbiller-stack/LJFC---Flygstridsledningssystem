import React, { useState, useEffect } from 'react';
import type { Track } from '../types';
import { api } from '../api/client';
import './TacticalInfoCard.css';

interface Props {
  track: Track | null;
  onClose: () => void;
}

export function TacticalInfoCard({ track, onClose }: Props) {
  const [aiBrief, setAiBrief] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    if (!track) return;
    let cancelled = false;
    setAiBrief(null);
    setAiLoading(true);
    api
      .getTrackBrief(track.track_id)
      .then((r) => {
        if (!cancelled) setAiBrief((r.brief && r.brief.trim()) || null);
      })
      .catch(() => {
        if (!cancelled) setAiBrief(null);
      })
      .finally(() => {
        if (!cancelled) setAiLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [track?.track_id, track?.x_km, track?.y_km]);

  if (!track) return null;

  return (
    <div className="tactical-info-card">
      <div className="tic-header">
        <div className="tic-title">TRACK DETAILS</div>
        <button className="tic-close" onClick={onClose}>×</button>
      </div>
      
      <div className="tic-body">
        <div className="tic-id-row">
          <span className="tic-label">ID:</span>
          <span className="tic-value-highlight">{track.track_id}</span>
        </div>

        <div className="tic-ai-brief">
          <div className="tic-ai-label">AI ASSESSMENT</div>
          {aiLoading && <div className="tic-ai-loading">Analysing contact…</div>}
          {!aiLoading && aiBrief && <div className="tic-ai-text">{aiBrief}</div>}
          {!aiLoading && !aiBrief && (
            <div className="tic-ai-unavail">No AI narrative (configure Ollama / Gemini in backend `.env`)</div>
          )}
        </div>

        <div className="tic-grid">
          <div className="tic-item">
            <span className="tic-label">CLASS</span>
            <span className="tic-value">{track.class_label.toUpperCase()}</span>
          </div>
          <div className="tic-item">
            <span className="tic-label">CONFID</span>
            <span className="tic-value">{(track.confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="tic-item">
            <span className="tic-label">SPEED</span>
            <span className="tic-value">{track.speed_class}</span>
          </div>
          <div className="tic-item">
            <span className="tic-label">HDG</span>
            <span className="tic-value">{track.heading_deg.toFixed(0)}°</span>
          </div>
          <div className="tic-item">
            <span className="tic-label">ALT</span>
            <span className="tic-value">{track.altitude_band}</span>
          </div>
          <div className="tic-item">
            <span className="tic-label">STATUS</span>
            <span className="tic-value">{track.status}</span>
          </div>
        </div>

        <div className="tic-pos-row">
          <span className="tic-label">POS:</span>
          <span className="tic-value-mono">
            {track.x_km.toFixed(2)}, {track.y_km.toFixed(2)}
          </span>
        </div>
      </div>
      
      <div className="tic-footer">
        <div className={`tic-threat-status ${track.confidence > 0.8 ? 'critical' : 'warning'}`}>
          {track.confidence > 0.8 ? 'HIGH PRIORITY THREAT' : 'ACTIVE TRACK'}
        </div>
      </div>
    </div>
  );
}
