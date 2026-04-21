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

const SPEEDS = [1, 2, 4, 8];

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
  { target: 'first_group', label: 'First Group' },
  { target: 'first_decision', label: 'Decision' },
  { target: 'second_wave', label: '2nd Wave' },
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
        <div className="tl-time">
          <span className="tl-time-value">{formatTime(currentTime)}</span>
          <span className="tl-time-label">/ {formatTime(dur)}</span>
        </div>
      </div>
    </div>
  );
}
