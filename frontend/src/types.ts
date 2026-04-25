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
  corridor_id?: string;
  group_seed_id?: string;
  formation_hint?: string;
  decoy_probability?: number;
  signature_hint?: string;
  payload_known?: boolean;
  payload_type?: string;
  rf_emitting?: boolean;
  maneuver_pattern?: string;
  source_disagreement?: boolean;
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

export interface AtoContext {
  ato_id: string;
  commander_intent: string;
  primary_defended_object_ids: string[];
  reserve_policy: Record<string, number | string | boolean>;
  approval_required: boolean;
  approval_role: string;
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
  mode?: string;
  runtime_mode?: string;
  scenario_origin?: string;
  scenario_meta?: Record<string, unknown>;
  sensor_states?: Record<string, unknown>;
  threat_groups?: ThreatGroup[];
  feed_status?: FeedStatus;
  feed_source?: string;
  last_feed_event?: FeedEvent | null;
  recommendation_status?: string;
  ai_provider_status?: AIProviderStatus;
  ato_context?: AtoContext;
}

export interface FeedEvent {
  feed_time_s: number;
  event_id: string;
  event_type: string;
  source: string;
  data: Record<string, unknown>;
}

export interface FeedStatus {
  feed_id: string;
  label: string;
  status: string;
  current_time_s: number;
  duration_s: number;
  speed_multiplier: number;
  source_file: string;
  last_event?: FeedEvent | null;
}

export interface AIProviderStatus {
  provider: string;
  model: string;
  status: string;
  label: string;
  last_error?: string;
}

export interface ScenarioEntry {
  scenario_id: string;
  file_id: string;
  source_file: string;
  source_type: string;
  title: string;
  short_description: string;
  duration_s?: number;
  seed?: number;
  template?: string;
  track_count?: number;
  group_count?: number;
  extended_fields?: boolean;
  recommended_mode: string;
  jury_demo?: boolean;
}

export interface ScenarioSession {
  scenario_id: string;
  scenario_label: string;
  source_file: string;
  runtime_mode: string;
  scenario_origin: string;
  mode: string;
  template_name?: string;
  seed?: number;
  runtime_session_id?: string;
  source_parent_scenario?: string;
  source_state_id: string;
  duration_s: number;
  current_time_s: number;
  status: string;
  is_playing: boolean;
  speed_multiplier: number;
  description: string;
  recommended_demo?: string;
  track_count: number;
  group_count: number;
  extended_schema_present: boolean;
  loaded_at: string;
  scenario_meta?: Record<string, unknown>;
  wave: number;
  last_mutation_count?: number;
  last_mutation_summary?: Record<string, unknown>;
  mutation_log?: Array<Record<string, unknown>>;
}

export interface TimelineMarker {
  t_s: number;
  type: string;
  label: string;
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

export interface AgentChatMessage {
  id?: string;
  role: 'operator' | 'assistant';
  message?: string;
  operator_message?: string;
  timestamp: string;
  source_state_id: string;
  provider?: string;
  model?: string;
  status?: string;
  parse_status?: string;
  fallback_used?: boolean;
  structured?: {
    schema_version: string;
    response_type: string;
    bluf: string;
    situation: string;
    evidence: Array<{ label: string; detail: string; cited_id: string }>;
    recommendation: string;
    next_actions: Array<{ label: string; command: string }>;
    confidence: 'low' | 'medium' | 'high';
    warnings: string[];
    cited_ids: string[];
  };
  display_text?: string;
}

export interface CopilotStatusData {
  provider: string;
  model: string;
  scenario_id: string;
  feed_count: number;
  session_commands: number;
  ai_status?: AIProviderStatus;
}

// ── Threat Groups & Responses ──

export interface UncertaintyFlag {
  flag: string;
  detail: string;
  severity: string;
}

export interface SourceEvidence {
  factor: string;
  value: number;
  detail: string;
}

export interface ThreatGroup {
  group_id: string;
  member_track_ids: string[];
  group_type: string;
  coordination_score: number;
  confidence: number;
  rationale: string[];
  short_narration: string;
  most_at_risk_object_id?: string;
  urgency_score: number;
  time_to_zone_s?: number;
  leak_through_risk: number;
  saturation_pressure: number;
  uncertainty_flags: UncertaintyFlag[];
  recommended_lane: string;
  source_state_id: string;
  top_response_ids: string[];
  evidence: SourceEvidence[];
  inaction_consequence: string;
}

export interface ResponseOption {
  response_id: string;
  group_id: string;
  rank: number;
  response_family: string;
  title: string;
  summary: string;
  intended_effect: string;
  expected_effectiveness: number;
  time_to_effect_s: number;
  reversibility: string;
  collateral_proxy: string;
  blue_force_interference: string;
  readiness_cost_pct: number;
  cost_exchange_proxy: string;
  operator_workload: string;
  authority_required: string;
  policy_gates: string[];
  rationale: string[];
  assumptions: string[];
  confidence: number;
  source_state_id: string;
  linked_coa_id?: string;
  scoring_factors: Record<string, number>;
}

export interface DecisionCard {
  card_id: string;
  group_id: string;
  group: ThreatGroup;
  recommended_response: ResponseOption;
  alternatives: ResponseOption[];
  authority_status: string;
  reserve_impact_summary: string;
  data_trust_level: string;
  source_state_id: string;
  timestamp: string;
}

export interface AfterActionRecord {
  record_id: string;
  timestamp: string;
  group_id: string;
  group_snapshot: Record<string, unknown>;
  response_chosen: string;
  response_family: string;
  operator_action: string;
  override_reason: string;
  simulation_run: boolean;
  simulation_outcome?: number;
  readiness_after: number;
  source_state_id: string;
  wave: number;
}
