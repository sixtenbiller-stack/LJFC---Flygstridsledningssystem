export interface Point {
  x_km: number;
  y_km: number;
}

export interface GeoFeature {
  id: string;
  type: string;
  name: string;
  side: string;
  x_km: number;
  y_km: number;
  value_score: number;
  defended_priority: number;
  runway_status?: string;
  population_label?: string;
  coverage_radius_km?: number;
  missile_count?: number;
  sam_class?: string;
  detection_range_km?: number;
  sensor_type?: string;
  notes?: string;
}

export interface TerrainFeature {
  id: string;
  type: string;
  name: string;
  polygon_km: number[][];
  elevation_m?: number;
  notes?: string;
}

export interface DefendedZone {
  id: string;
  name: string;
  center_km: number[];
  radius_km: number;
  priority: number;
  protected_features: string[];
  notes?: string;
}

export interface Geography {
  meta: Record<string, unknown>;
  features: GeoFeature[];
  terrain: TerrainFeature[];
  defended_zones: DefendedZone[];
}

export interface Asset {
  asset_id: string;
  side: string;
  asset_type: string;
  asset_class: string;
  home_base_id: string;
  current_location: Point;
  status: string;
  readiness: number;
  endurance_min?: number;
  speed_class?: string;
  response_tags: string[];
  current_assignment?: string;
  recovery_eta_min?: number;
  availability_reason?: string;
  munitions: Record<string, number>;
  coverage_radius_km?: number;
  engagement_ceiling_m?: number;
}

export interface PathPoint {
  t_s: number;
  x_km: number;
  y_km: number;
}

export interface Track {
  track_id: string;
  side: string;
  class_label: string;
  confidence: number;
  x_km: number;
  y_km: number;
  heading_deg: number;
  speed_class: string;
  altitude_band: string;
  detected_by: string[];
  predicted_path: PathPoint[];
  notes?: string;
  status: string;
}

export interface Alert {
  alert_id: string;
  priority: string;
  tracks: string[];
  threatened_zone?: string;
  estimated_eta_s?: number;
  message: string;
  timestamp_s: number;
  threat_score: number;
}

export interface ThreatAlert {
  track_id: string;
  class_label: string;
  confidence: number;
  threat_score: number;
  priority_band: string;
  factors: Record<string, number>;
  nearest_zone_id?: string;
  eta_s?: number;
  heading_deg: number;
  speed_class: string;
  altitude_band: string;
  x_km: number;
  y_km: number;
}

export interface CoaAction {
  asset_id: string;
  action_type: string;
  target_track_ids: string[];
  defended_zone_id?: string;
}

export interface CourseOfAction {
  coa_id: string;
  rank: number;
  title: string;
  summary: string;
  actions: CoaAction[];
  protected_objectives: string[];
  readiness_cost_pct: number;
  reserve_posture: string;
  estimated_outcome: string;
  risk_level: string;
  assumptions: string[];
  rationale: string;
  source_state_id?: string;
}

export interface SimTimelineEvent {
  t_s: number;
  event: string;
  detail: string;
}

export interface SimulationResult {
  run_id: string;
  source_state_id: string;
  coa_id: string;
  seed: number;
  duration_s: number;
  outcome_score: number;
  threats_intercepted: number;
  threats_missed: number;
  threats_monitored: number;
  zone_breaches: number;
  asset_losses: number;
  missiles_expended: Record<string, number>;
  readiness_remaining_pct: number;
  recovery_time_min: number;
  timeline: SimTimelineEvent[];
  post_engagement_readiness: Record<string, unknown>;
  narration: string;
}

export interface AuditRecord {
  decision_id: string;
  timestamp: string;
  coa_id: string;
  source_state_id: string;
  operator_note: string;
  readiness_delta: string;
  readiness_remaining_pct: number;
  wave: number;
}

export interface EventLog {
  t_s: number;
  type: string;
  summary: string;
}

export interface ScenarioState {
  scenario_id: string;
  scenario_name: string;
  current_time_s: number;
  is_playing: boolean;
  speed_multiplier: number;
  source_state_id: string;
  tracks: Track[];
  assets: Asset[];
  alerts: Alert[];
  geography?: Geography;
  wave: number;
  coa_trigger_pending: boolean;
  events_log: EventLog[];
}

export interface ExplanationData {
  coa_id: string;
  question_received: string;
  source_state_id: string;
  explanation: {
    primary_factors: Array<{
      factor: string;
      detail: string;
      data_citation?: string;
    }>;
    trade_off_summary: string;
    uncertainty_notes: string[];
    recommendation_confidence: string;
  };
  narration: string;
}

export interface FeedItem {
  id: string;
  timestamp: string;
  source_state_id: string;
  category: string;
  severity: string;
  title: string;
  body: string;
  suggested_actions: string[];
  related_ids: string[];
}

export interface CopilotResponse {
  type: string;
  message: string;
  data: Record<string, unknown>;
  source_state_id: string;
  suggested_actions: string[];
}

export interface CopilotStatusData {
  provider: string;
  model: string;
  scenario_id: string;
  feed_count: number;
  session_commands: number;
}
