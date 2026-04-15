import { useRef, useEffect } from 'react';
import type { EventLog } from '../types';
import './Timeline.css';

interface Props {
  currentTime: number;
  isPlaying: boolean;
  speed: number;
  eventsLog: EventLog[];
  coaTriggerPending: boolean;
  onControl: (action: string, speed?: number) => void;
  onReset: () => void;
  /** Tighter layout when bottom bar is compact or collapsed */
  compact?: boolean;
}

const SPEEDS = [1, 2, 4, 8];

export function Timeline({
  currentTime, isPlaying, speed, eventsLog, coaTriggerPending, onControl, onReset,
  compact = false,
}: Props) {
  const logRef = useRef<HTMLDivElement>(null);

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

  const progress = Math.min(100, (currentTime / 240) * 100);

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
              ×{s}
            </button>
          ))}
        </div>

        <div className="tl-time">
          <span className="tl-time-value">{formatTime(currentTime)}</span>
          <span className="tl-time-label">/ 4:00</span>
        </div>

        <div className="tl-progress-bar">
          <div className="tl-progress-fill" style={{ width: `${progress}%` }} />
          <div className="tl-progress-marker" style={{ left: `${Math.min(progress, 100)}%` }} />
        </div>

        {coaTriggerPending && (
          <div className="tl-coa-alert">⚡ COA RECOMMENDED</div>
        )}
      </div>

      <div className="tl-event-log" ref={logRef}>
        {eventsLog.slice(-20).map((e, i) => (
          <div key={i} className={`tl-event ev-${e.type?.toLowerCase().includes('alert') ? 'alert' : e.type?.toLowerCase().includes('track') ? 'track' : 'normal'}`}>
            <span className="tl-ev-time">{formatTime(e.t_s)}</span>
            <span className="tl-ev-type">{e.type}</span>
            <span className="tl-ev-summary">{e.summary}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
