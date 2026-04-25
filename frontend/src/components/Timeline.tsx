import { useRef, useEffect, useState } from 'react';
import type { EventLog, TimelineMarker } from '../types';
import './Timeline.css';

interface Props {
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  speed: number;
  eventsLog: EventLog[];
  coaTriggerPending: boolean;
  onControl: (action: string, speed?: number) => void;
  onReset: () => void;
  onJump?: (target: string) => void;
  onSeek?: (time_s: number) => void;
  markers?: TimelineMarker[];
  mode?: string;
  compact?: boolean;
}

const SPEEDS = [0.5, 1, 2];

const MARKER_COLORS: Record<string, string> = {
  start: '#6e7681',
  first_contact: '#79c0ff',
  first_group: '#f0883e',
  first_decision: '#f85149',
  second_wave: '#d29922',
  sensor_degraded: '#bc8cff',
  end: '#6e7681',
};

const DEMO_JUMPS = [
  { target: 'first_contact', label: 'First Contact' },
  { target: 'first_group', label: 'Group Formed' },
  { target: 'first_decision', label: 'Decision' },
];

export function Timeline({
  currentTime, duration, isPlaying, speed, eventsLog, coaTriggerPending,
  onControl, onReset, onJump, onSeek, markers = [], mode, compact = false,
}: Props) {
  const logRef = useRef<HTMLDivElement>(null);
  const [hoveredMarker, setHoveredMarker] = useState<string | null>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollLeft = logRef.current.scrollWidth;
    }
  }, [eventsLog.length]);

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const dur = duration || 240;
  const progress = Math.min(100, (currentTime / dur) * 100);
  const progressBarRef = useRef<HTMLDivElement>(null);

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!onSeek || !progressBarRef.current) return;
    const rect = progressBarRef.current.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    onSeek(Math.round(pct * dur));
  };

  return (
    <div className={`timeline ${compact ? 'timeline--compact' : ''}`}>
      <div className="timeline-controls">
        <button className="tl-btn" onClick={onReset} title="Reset">⟳</button>

        {isPlaying ? (
          <button className="tl-btn tl-pause" onClick={() => onControl('pause')} title="Pause">❚❚</button>
        ) : (
          <button className="tl-btn tl-play" onClick={() => onControl('play')} title="Play">▶</button>
        )}

        <div className="speed-group">
          {SPEEDS.map(s => (
            <button
              key={s}
              className={`speed-btn ${speed === s ? 'active' : ''}`}
              onClick={() => onControl('speed', s)}
            >
              {s}x
            </button>
          ))}
        </div>

        <div className="tl-time">
          <span className="tl-time-value">{formatTime(currentTime)}</span>
          <span className="tl-time-label">/ {formatTime(dur)}</span>
        </div>

        <div className="tl-progress-bar" ref={progressBarRef} onClick={handleProgressClick}
             style={{ cursor: onSeek ? 'pointer' : 'default' }}>
          <div className="tl-progress-fill" style={{ width: `${progress}%` }} />
          <div className="tl-progress-marker" style={{ left: `${Math.min(progress, 100)}%` }} />
          {markers.map((m) => {
            const pct = Math.min(100, (m.t_s / dur) * 100);
            return (
              <div
                key={`${m.type}-${m.t_s}`}
                className={`tl-marker tl-marker-${m.type}`}
                style={{ left: `${pct}%`, borderColor: MARKER_COLORS[m.type] || '#79c0ff' }}
                title={`${m.label} (${formatTime(m.t_s)})`}
                onMouseEnter={() => setHoveredMarker(`${m.type}-${m.t_s}`)}
                onMouseLeave={() => setHoveredMarker(null)}
                onClick={() => onJump?.(m.type === 'second_wave' ? 'second_wave' :
                  m.type === 'first_contact' ? 'first_contact' :
                  m.type === 'first_group' ? 'first_group' :
                  m.type === 'first_decision' ? 'first_decision' : 'first_contact')}
              >
                {hoveredMarker === `${m.type}-${m.t_s}` && (
                  <span className="tl-marker-tooltip">{m.label}</span>
                )}
              </div>
            );
          })}
        </div>

        {coaTriggerPending && (
          <div className="tl-coa-alert">RECOMMENDATION READY</div>
        )}
      </div>

      {!compact && onJump && (
        <div className="tl-demo-strip">
          {DEMO_JUMPS.map(d => (
            <button
              key={d.target}
              className="tl-demo-btn"
              onClick={() => onJump(d.target)}
              title={`Jump to ${d.label}`}
            >
              {d.label}
            </button>
          ))}
        </div>
      )}

      <div className="tl-event-log" ref={logRef}>
        {eventsLog.slice(-20).map((e, i) => (
          <div key={i} className={`tl-event ev-${e.type?.toLowerCase().includes('alert') ? 'alert' : e.type?.toLowerCase().includes('track') ? 'track' : e.type?.toLowerCase().includes('group') ? 'group' : 'normal'}`}>
            <span className="tl-ev-time">{formatTime(e.t_s)}</span>
            <span className="tl-ev-type">{e.type}</span>
            <span className="tl-ev-summary">{e.summary}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
