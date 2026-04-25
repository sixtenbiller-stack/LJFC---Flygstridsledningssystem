import { useState, useEffect, useCallback } from 'react';
import type { ScenarioState, AtoContext } from '../types';
import { sanitizeDisplayText } from '../utils/sanitizeDisplayText';
import './AtoMissionCard.css';

const EXPANDED_KEY = 'ljfc-ato-mission-expanded';

function loadExpandedDefault(): boolean {
  try {
    const v = localStorage.getItem(EXPANDED_KEY);
    if (v === '0') return false;
    if (v === '1') return true;
  } catch {
    /* ignore */
  }
  return true;
}

interface Props {
  state: ScenarioState;
}

export function AtoMissionCard({ state }: Props) {
  const [expanded, setExpanded] = useState(loadExpandedDefault);
  const [detailsOpen, setDetailsOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(EXPANDED_KEY, expanded ? '1' : '0');
    } catch {
      /* ignore */
    }
  }, [expanded]);

  const onToggleExpand = useCallback(() => {
    setExpanded(e => !e);
  }, []);

  const ato: AtoContext | undefined = state.ato_context;
  const atoFighterReserve =
    ato && typeof ato.reserve_policy?.min_fighter_reserve === 'number'
      ? ato.reserve_policy.min_fighter_reserve
      : null;
  const primaryDef = ato?.primary_defended_object_ids?.[0] ?? '—';
  const labelId = ato?.ato_id || state.active_ato_id || '—';

  if (!expanded) {
    return (
      <div
        className="ato-mission-collapsed"
        onClick={onToggleExpand}
        onKeyDown={e => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onToggleExpand();
          }
        }}
        role="button"
        tabIndex={0}
        title="Show ATO / mission constraints"
        aria-label="Expand ATO mission constraints"
      >
        <span className="ato-mission-collapsed-icon">◎</span>
        <span className="ato-mission-collapsed-label">ATO / MISSION</span>
        <span className="ato-mission-collapsed-id">{labelId}</span>
        {primaryDef !== '—' && <span className="ato-mission-collapsed-pri">{primaryDef}</span>}
      </div>
    );
  }

  return (
    <div className="ato-mission-card" aria-label="Synthetic ATO mission constraints">
      <div className="ato-mission-header">
        <div className="ato-mission-title">ATO / mission constraints</div>
        <button
          type="button"
          className="ato-mission-collapse-btn"
          onClick={() => setExpanded(false)}
          title="Minimize"
          aria-label="Minimize ATO card"
        >
          —
        </button>
      </div>
      {ato && !ato.ato_error ? (
        <>
          <dl className="ato-mission-grid">
            <dt>ATO</dt>
            <dd>{ato.ato_id || state.active_ato_id || '—'}</dd>
            <dt>Intent</dt>
            <dd className="ato-mission-intent">
              {sanitizeDisplayText((ato.commander_intent || '—').slice(0, 220))}
            </dd>
            <dt>Primary defended</dt>
            <dd>{primaryDef}</dd>
            <dt>Reserve rule</dt>
            <dd>
              {atoFighterReserve != null
                ? `Keep ${atoFighterReserve} fighter(s)`
                : '—'}
            </dd>
            <dt>Approval</dt>
            <dd>
              {ato.approval_role
                ? sanitizeDisplayText(ato.approval_role.slice(0, 80))
                : '—'}
            </dd>
            <dt>Status</dt>
            <dd>{ato.status || 'synthetic / active'}</dd>
          </dl>
          {(ato.missions_preview?.length ?? 0) > 0 && (
            <div className="ato-mission-details">
              <button
                type="button"
                className="ato-mission-toggle"
                onClick={e => {
                  e.stopPropagation();
                  setDetailsOpen(v => !v);
                }}
                aria-expanded={detailsOpen}
              >
                {detailsOpen ? 'Hide details' : 'Details'}
              </button>
              {detailsOpen && (
                <ul className="ato-mission-missions">
                  {ato.missions_preview!.map((m, i) => (
                    <li key={i}>
                      <span className="ato-mm-type">{m.mission_type}</span>
                      {sanitizeDisplayText(m.title.slice(0, 120))}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      ) : (
        <p className="ato-mission-placeholder">
          {ato?.ato_error
            ? sanitizeDisplayText(String(ato.ato_error).slice(0, 200))
            : 'No synthetic ATO context in this state.'}
        </p>
      )}
    </div>
  );
}
