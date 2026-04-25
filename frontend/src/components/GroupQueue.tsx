import type { ThreatGroup } from '../types';
import './GroupQueue.css';

interface Props {
  groups: ThreatGroup[];
  selectedGroup: string | null;
  onGroupClick: (groupId: string) => void;
}

const LANE_LABEL: Record<string, string> = { fast: 'FAST', slow: 'SLOW' };

export function GroupQueue({ groups, selectedGroup, onGroupClick }: Props) {
  const topGroup = groups[0];

  return (
    <div className="group-queue">
      <div className="gq-header">
        <span className="gq-title">THREAT GROUPS</span>
        <span className="gq-count">{groups.length} group{groups.length !== 1 ? 's' : ''}</span>
      </div>

      {groups.length === 0 && (
        <div className="gq-empty">No threat groups formed — start playback to populate threats</div>
      )}

      {topGroup && (
        <div className="gq-pinned">
          <div className="gq-pinned-label">Top group</div>
          <button
            type="button"
            className={`gq-pinned-card ${selectedGroup === topGroup.group_id ? 'selected' : ''} lane-${topGroup.recommended_lane}`}
            onClick={() => onGroupClick(topGroup.group_id)}
          >
            <div className="gq-pinned-top">
              <span className="gq-pinned-id">{topGroup.group_id}</span>
              <span className={`gq-lane lane-badge-${topGroup.recommended_lane}`}>
                {LANE_LABEL[topGroup.recommended_lane] ?? topGroup.recommended_lane}
              </span>
            </div>
            <div className="gq-pinned-type">{topGroup.group_type.replace(/_/g, ' ')}</div>
            <div className="gq-pinned-meta">
              {topGroup.member_track_ids.length} tracks · urgency {(topGroup.urgency_score * 100).toFixed(0)}%
              {topGroup.time_to_zone_s != null ? ` · ETA ${Math.round(topGroup.time_to_zone_s)}s` : ''}
              {topGroup.most_at_risk_object_id ? ` · defended ${topGroup.most_at_risk_object_id}` : ''}
            </div>
          </button>
        </div>
      )}

      {groups.slice(1).map(g => (
        <div
          key={g.group_id}
          className={`gq-card ${selectedGroup === g.group_id ? 'selected' : ''} lane-${g.recommended_lane}`}
          onClick={() => onGroupClick(g.group_id)}
        >
          <div className="gq-card-top">
            <span className="gq-card-id">{g.group_id}</span>
            <span className={`gq-lane lane-badge-${g.recommended_lane}`}>
              {LANE_LABEL[g.recommended_lane] ?? g.recommended_lane}
            </span>
          </div>
          <div className="gq-card-type">{g.group_type.replace(/_/g, ' ')}</div>
          <div className="gq-card-details">
            <div className="gq-detail">
              <span className="gq-detail-label">Tracks</span>
              <span className="gq-detail-value">{g.member_track_ids.length}</span>
            </div>
            <div className="gq-detail">
              <span className="gq-detail-label">Urgency</span>
              <span className="gq-detail-value">{(g.urgency_score * 100).toFixed(0)}%</span>
            </div>
            <div className="gq-detail">
              <span className="gq-detail-label">Conf</span>
              <span className="gq-detail-value">{(g.confidence * 100).toFixed(0)}%</span>
            </div>
            {g.time_to_zone_s != null && (
              <div className="gq-detail">
                <span className="gq-detail-label">ETA</span>
                <span className="gq-detail-value">{Math.round(g.time_to_zone_s)}s</span>
              </div>
            )}
          </div>
          {g.most_at_risk_object_id && (
            <div className="gq-at-risk">→ {g.most_at_risk_object_id.replace('zone-', '')}</div>
          )}
        </div>
      ))}
    </div>
  );
}
