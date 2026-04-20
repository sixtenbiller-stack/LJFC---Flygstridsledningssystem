import { useState } from 'react';
import type { DecisionCard as DecisionCardType, ResponseOption, ThreatGroup } from '../types';
import './DecisionCard.css';

interface Props {
  card: DecisionCardType;
  onApprove: (groupId: string, responseId: string) => void;
  onDefer: (groupId: string) => void;
  onOverride: (groupId: string, responseId: string, reason: string) => void;
  onGenerateCoas: () => void;
  onSimulate: (coaId: string) => void;
  loading: string;
}

const LANE_LABEL: Record<string, string> = { fast: 'FAST', slow: 'SLOW' };

export function DecisionCard({ card, onApprove, onDefer, onOverride, onGenerateCoas, onSimulate, loading }: Props) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [overrideMode, setOverrideMode] = useState(false);
  const [overrideReason, setOverrideReason] = useState('');
  const [showDetails, setShowDetails] = useState(false);

  const { group, recommended_response, alternatives } = card;
  const allResponses = [recommended_response, ...alternatives];
  const active = allResponses[selectedIdx] ?? recommended_response;

  const handleApprove = () => {
    onApprove(group.group_id, active.response_id);
  };

  const handleOverrideSubmit = () => {
    if (overrideReason.trim()) {
      onOverride(group.group_id, active.response_id, overrideReason.trim());
      setOverrideMode(false);
      setOverrideReason('');
    }
  };

  return (
    <div className={`decision-card lane-${group.recommended_lane}`}>
      <div className="dc-header">
        <div className="dc-header-left">
          <span className="dc-group-id">{group.group_id}</span>
          <span className={`dc-lane lane-badge-${group.recommended_lane}`}>
            {LANE_LABEL[group.recommended_lane] ?? group.recommended_lane}
          </span>
          <span className={`dc-trust trust-${card.data_trust_level}`}>
            {card.data_trust_level.toUpperCase()}
          </span>
        </div>
        <span className={`dc-authority auth-${card.authority_status}`}>
          {card.authority_status.replace(/_/g, ' ')}
        </span>
      </div>

      <GroupSummarySection group={group} />

      <div className="dc-section">
        <div className="dc-section-title">Inaction Consequence</div>
        <div className="dc-inaction">{group.inaction_consequence}</div>
      </div>

      <div className="dc-section">
        <div className="dc-section-title">Recommended Response</div>
        <div className="dc-response-tabs">
          {allResponses.map((r, i) => (
            <button
              key={r.response_id}
              type="button"
              className={`dc-resp-tab ${selectedIdx === i ? 'active' : ''}`}
              onClick={() => setSelectedIdx(i)}
            >
              #{r.rank} {r.title.length > 24 ? r.title.slice(0, 22) + '…' : r.title}
            </button>
          ))}
        </div>
        <ResponseDetail response={active} />
      </div>

      <div className="dc-section">
        <div className="dc-section-title">Reserve Impact</div>
        <div className="dc-reserve">{card.reserve_impact_summary}</div>
      </div>

      {group.uncertainty_flags.length > 0 && (
        <div className="dc-section">
          <div className="dc-section-title">Uncertainty</div>
          {group.uncertainty_flags.map((f, i) => (
            <div key={i} className={`dc-flag flag-${f.severity}`}>
              <span className="dc-flag-sev">{f.severity.toUpperCase()}</span>
              <span className="dc-flag-detail">{f.detail}</span>
            </div>
          ))}
        </div>
      )}

      <button type="button" className="dc-details-toggle" onClick={() => setShowDetails(d => !d)}>
        {showDetails ? '▾ Hide details' : '▸ Show scoring details'}
      </button>
      {showDetails && (
        <div className="dc-scoring">
          {Object.entries(active.scoring_factors).map(([k, v]) => (
            <div key={k} className="dc-factor-row">
              <span className="dc-factor-name">{k.replace(/_/g, ' ')}</span>
              <div className="dc-factor-bar">
                <div className="dc-factor-fill" style={{ width: `${Math.round(v * 100)}%` }} />
              </div>
              <span className="dc-factor-val">{(v * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}

      {!overrideMode ? (
        <div className="dc-actions">
          <button type="button" className="dc-btn dc-btn-primary" onClick={handleApprove} disabled={loading === 'group-approve'}>
            {loading === 'group-approve' ? '…' : `Approve: ${active.title}`}
          </button>
          <button type="button" className="dc-btn" onClick={onGenerateCoas}>Detailed COAs</button>
          <button type="button" className="dc-btn" onClick={() => onDefer(group.group_id)}>Defer</button>
          <button type="button" className="dc-btn dc-btn-warn" onClick={() => setOverrideMode(true)}>Override</button>
        </div>
      ) : (
        <div className="dc-override-box">
          <div className="dc-section-title">Override Reason (required)</div>
          <textarea
            className="dc-override-input"
            value={overrideReason}
            onChange={e => setOverrideReason(e.target.value)}
            placeholder="Explain why you are overriding the recommendation…"
            rows={2}
          />
          <div className="dc-override-actions">
            <button type="button" className="dc-btn dc-btn-warn" onClick={handleOverrideSubmit} disabled={!overrideReason.trim()}>
              Confirm Override
            </button>
            <button type="button" className="dc-btn" onClick={() => setOverrideMode(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="dc-lineage">
        Snapshot: {card.source_state_id}
      </div>
    </div>
  );
}

function GroupSummarySection({ group }: { group: ThreatGroup }) {
  return (
    <div className="dc-group-summary">
      <div className="dc-narration">{group.short_narration}</div>
      <div className="dc-metrics-grid">
        <MetricCell label="Type" value={group.group_type.replace(/_/g, ' ')} />
        <MetricCell label="Tracks" value={String(group.member_track_ids.length)} />
        <MetricCell label="Confidence" value={`${(group.confidence * 100).toFixed(0)}%`} />
        <MetricCell label="Urgency" value={`${(group.urgency_score * 100).toFixed(0)}%`} />
        <MetricCell label="ETA" value={group.time_to_zone_s != null ? `${Math.round(group.time_to_zone_s)}s` : '—'} />
        <MetricCell label="At Risk" value={group.most_at_risk_object_id?.replace('zone-', '') ?? '—'} />
        <MetricCell label="Saturation" value={`${(group.saturation_pressure * 100).toFixed(0)}%`} />
        <MetricCell label="Leak Risk" value={`${(group.leak_through_risk * 100).toFixed(0)}%`} />
      </div>
      {group.rationale.length > 0 && (
        <div className="dc-rationale">
          {group.rationale.map((r, i) => (
            <div key={i} className="dc-rationale-item">{r}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="dc-metric-cell">
      <span className="dc-metric-label">{label}</span>
      <span className="dc-metric-value">{value}</span>
    </div>
  );
}

function ResponseDetail({ response }: { response: ResponseOption }) {
  return (
    <div className="dc-response-detail">
      <div className="dc-resp-title">{response.title}</div>
      <div className="dc-resp-summary">{response.summary}</div>
      <div className="dc-resp-metrics">
        <MetricCell label="Effectiveness" value={`${(response.expected_effectiveness * 100).toFixed(0)}%`} />
        <MetricCell label="Readiness Cost" value={`${response.readiness_cost_pct.toFixed(0)}%`} />
        <MetricCell label="Time to Effect" value={`${response.time_to_effect_s}s`} />
        <MetricCell label="Reversibility" value={response.reversibility} />
        <MetricCell label="Authority" value={response.authority_required.replace(/_/g, ' ')} />
        <MetricCell label="Confidence" value={`${(response.confidence * 100).toFixed(0)}%`} />
      </div>
      {response.rationale.length > 0 && (
        <div className="dc-resp-rationale">
          {response.rationale.map((r, i) => (
            <div key={i} className="dc-rationale-item">{r}</div>
          ))}
        </div>
      )}
    </div>
  );
}
