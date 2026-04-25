"""Pydantic domain models for LJFC COMMAND."""
from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class Side(str, Enum):
    FRIENDLY = "friendly"
    HOSTILE = "hostile"
    UNKNOWN = "unknown"


class AssetType(str, Enum):
    FIGHTER = "fighter"
    UAV = "uav"
    SAM_BATTERY = "sam_battery"


class AssetStatus(str, Enum):
    READY = "ready"
    STANDBY = "standby"
    ALERT = "alert"
    ACTIVE = "active"
    RECOVERING = "recovering"
    UNAVAILABLE = "unavailable"


class SpeedClass(str, Enum):
    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


class AltitudeBand(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PriorityBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatGroupType(str, Enum):
    UNKNOWN = "unknown"
    SINGLE_INBOUND = "single_inbound"
    COORDINATED_PROBE = "coordinated_probe"
    PROBABLE_SWARM = "probable_swarm"
    MIXED_RAID_WITH_DECOYS = "mixed_raid_with_decoys"
    SECOND_WAVE_PRESSURE = "second_wave_pressure"
    RECON_OR_DECOY_SCREEN = "recon_or_decoy_screen"


class WorkflowLane(str, Enum):
    FAST = "fast"
    SLOW = "slow"


class ResponseFamily(str, Enum):
    OBSERVE_VERIFY = "observe_verify"
    PROTECT_POSTURE = "protect_posture"
    REPOSITION_COVERAGE = "reposition_coverage"
    NON_KINETIC_DISRUPT = "non_kinetic_disrupt_synthetic"
    ACTIVE_DEFENSE = "active_defense_synthetic"
    MIXED_RESPONSE = "mixed_response_synthetic"
    HOLD_RESERVE = "hold_reserve_and_monitor"
    RECOVER_REASSESS = "recover_reassess"
    ESCALATE_COMMAND = "escalate_command_review"


class AuthorityStatus(str, Enum):
    AVAILABLE_NOW = "available_now"
    NEEDS_CONFIRMATION = "needs_confirmation"
    NOT_AVAILABLE = "not_available"
    POLICY_BLOCKED = "policy_blocked"


class DataTrustLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Geography ──

class Point(BaseModel):
    x_km: float
    y_km: float


class GeoFeature(BaseModel):
    id: str
    type: str
    name: str
    side: str = "friendly"
    x_km: float
    y_km: float
    value_score: float = 0.0
    defended_priority: int = 5
    # type-specific optional fields
    runway_status: str | None = None
    population_label: str | None = None
    coverage_radius_km: float | None = None
    missile_count: int | None = None
    sam_class: str | None = None
    detection_range_km: float | None = None
    sensor_type: str | None = None
    notes: str | None = None


class TerrainFeature(BaseModel):
    id: str
    type: str
    name: str
    polygon_km: list[list[float]]
    elevation_m: float | None = None
    notes: str | None = None


class DefendedZone(BaseModel):
    id: str
    name: str
    center_km: list[float]
    radius_km: float
    priority: int
    protected_features: list[str] = []
    notes: str | None = None


class Geography(BaseModel):
    meta: dict[str, Any]
    features: list[GeoFeature]
    terrain: list[TerrainFeature]
    defended_zones: list[DefendedZone]


# ── Assets ──

class Munitions(BaseModel, extra="allow"):
    air_to_air: int = 0
    decoy: int = 0
    sam_missile: int = 0
    light_munition: int = 0


class Asset(BaseModel):
    asset_id: str
    side: str = "friendly"
    asset_type: str
    asset_class: str
    home_base_id: str
    current_location: Point
    status: str = "ready"
    readiness: float = 1.0
    endurance_min: float | None = None
    speed_class: str | None = None
    response_tags: list[str] = []
    current_assignment: str | None = None
    recovery_eta_min: float | None = None
    availability_reason: str | None = None
    munitions: Munitions = Field(default_factory=Munitions)
    coverage_radius_km: float | None = None
    engagement_ceiling_m: float | None = None


# ── Tracks ──

class PathPoint(BaseModel):
    t_s: float
    x_km: float
    y_km: float


class Track(BaseModel):
    track_id: str
    side: str = "hostile"
    class_label: str = "unknown"
    confidence: float = 0.5
    x_km: float
    y_km: float
    heading_deg: float = 0.0
    speed_class: str = "medium"
    altitude_band: str = "medium"
    detected_by: list[str] = []
    predicted_path: list[PathPoint] = []
    notes: str | None = None
    status: str = "active"  # active, intercepted, lost
    # Extended group-aware fields (optional — absent in legacy scenarios)
    corridor_id: str | None = None
    group_seed_id: str | None = None
    formation_hint: str | None = None
    decoy_probability: float | None = None
    signature_hint: str | None = None
    payload_known: bool | None = None
    payload_type: str | None = None
    rf_emitting: bool | None = None
    maneuver_pattern: str | None = None
    source_disagreement: bool | None = None


# ── Alerts ──

class Alert(BaseModel):
    alert_id: str
    priority: str
    tracks: list[str]
    threatened_zone: str | None = None
    estimated_eta_s: float | None = None
    message: str
    timestamp_s: float = 0.0
    threat_score: float = 0.0


# ── Threat Score ──

class ThreatScoreBreakdown(BaseModel):
    track_id: str
    total_score: float
    priority_band: str
    factors: dict[str, float]
    nearest_zone_id: str | None = None
    eta_s: float | None = None


# ── COAs ──

class CoaAction(BaseModel):
    asset_id: str
    action_type: str
    target_track_ids: list[str] = []
    defended_zone_id: str | None = None


class CourseOfAction(BaseModel):
    coa_id: str
    rank: int
    title: str
    summary: str
    actions: list[CoaAction]
    protected_objectives: list[str] = []
    readiness_cost_pct: float = 0.0
    reserve_posture: str = ""
    estimated_outcome: str = ""
    risk_level: str = "medium"
    assumptions: list[str] = []
    rationale: str = ""
    source_state_id: str | None = None


# ── Simulation ──

class SimTimelineEvent(BaseModel):
    t_s: float
    event: str
    detail: str


class SimulationResult(BaseModel):
    run_id: str
    source_state_id: str
    coa_id: str
    seed: int
    duration_s: float = 120
    outcome_score: float = 0.0
    threats_intercepted: int = 0
    threats_missed: int = 0
    threats_monitored: int = 0
    zone_breaches: int = 0
    asset_losses: int = 0
    missiles_expended: dict[str, int] = {}
    readiness_remaining_pct: float = 100.0
    recovery_time_min: float = 0
    timeline: list[SimTimelineEvent] = []
    post_engagement_readiness: dict[str, Any] = {}
    narration: str = ""


# ── Audit ──

class AuditRecord(BaseModel):
    decision_id: str
    timestamp: str
    coa_id: str
    source_state_id: str
    operator_note: str = ""
    readiness_delta: str = ""
    readiness_remaining_pct: float = 100.0
    wave: int = 1


# ── Threat Groups ──

class UncertaintyFlag(BaseModel):
    flag: str
    detail: str
    severity: str = "medium"  # low, medium, high


class SourceEvidence(BaseModel):
    factor: str
    value: float
    detail: str


class ThreatGroup(BaseModel):
    group_id: str
    member_track_ids: list[str]
    group_type: str = "unknown"
    coordination_score: float = 0.0
    confidence: float = 0.5
    rationale: list[str] = []
    short_narration: str = ""
    most_at_risk_object_id: str | None = None
    urgency_score: float = 0.0
    time_to_zone_s: float | None = None
    leak_through_risk: float = 0.0
    saturation_pressure: float = 0.0
    uncertainty_flags: list[UncertaintyFlag] = []
    recommended_lane: str = "slow"
    source_state_id: str = ""
    top_response_ids: list[str] = []
    evidence: list[SourceEvidence] = []
    inaction_consequence: str = ""


class ResponseOption(BaseModel):
    response_id: str
    group_id: str
    rank: int = 0
    response_family: str
    title: str
    summary: str
    intended_effect: str = ""
    expected_effectiveness: float = 0.0
    time_to_effect_s: float = 60.0
    reversibility: str = "medium"
    collateral_proxy: str = "none"
    blue_force_interference: str = "none"
    readiness_cost_pct: float = 0.0
    cost_exchange_proxy: str = "favorable"
    operator_workload: str = "low"
    authority_required: str = "available_now"
    policy_gates: list[str] = []
    rationale: list[str] = []
    assumptions: list[str] = []
    confidence: float = 0.5
    source_state_id: str = ""
    linked_coa_id: str | None = None
    scoring_factors: dict[str, float] = {}


class DecisionCardSnapshot(BaseModel):
    card_id: str
    group_id: str
    group: ThreatGroup
    recommended_response: ResponseOption
    alternatives: list[ResponseOption] = []
    authority_status: str = "available_now"
    reserve_impact_summary: str = ""
    data_trust_level: str = "medium"
    source_state_id: str = ""
    timestamp: str = ""


class AfterActionRecord(BaseModel):
    record_id: str
    timestamp: str
    group_id: str
    group_snapshot: dict[str, Any] = {}
    response_chosen: str = ""
    response_family: str = ""
    operator_action: str = ""  # approve, defer, override
    override_reason: str = ""
    simulation_run: bool = False
    simulation_outcome: float | None = None
    readiness_after: float = 100.0
    source_state_id: str = ""
    wave: int = 1


# ── Scenario Events ──

class ScenarioEvent(BaseModel):
    t_s: float
    event_type: str
    data: dict[str, Any]


# ── API Request/Response ──

class ScenarioLoadRequest(BaseModel):
    scenario_id: str = "scenario-alpha"


class ScenarioControlRequest(BaseModel):
    action: str  # play, pause, reset, speed
    speed: float | None = None


class CoaRequest(BaseModel):
    wave: int | None = None
    policy_profile: str | None = None


class ExplainRequest(BaseModel):
    coa_id: str
    question: str = "Why is this ranked first?"


class SimulateRequest(BaseModel):
    coa_id: str
    seed: int = 42


class ApproveRequest(BaseModel):
    coa_id: str
    operator_note: str = ""


class ScenarioState(BaseModel):
    scenario_id: str
    scenario_name: str = ""
    current_time_s: float
    is_playing: bool
    speed_multiplier: float
    source_state_id: str
    tracks: list[Track]
    assets: list[Asset]
    alerts: list[Alert]
    geography: Geography | None = None
    wave: int
    coa_trigger_pending: bool = False
    events_log: list[dict[str, Any]] = []
    mode: str = "replay"  # replay | live
    scenario_meta: dict[str, Any] = {}
    sensor_states: dict[str, Any] = {}


# ── Copilot Feed & Commands ──

class FeedItem(BaseModel):
    id: str
    timestamp: str
    source_state_id: str
    category: str  # threat_update, wave_detected, readiness, coa_generated, sim_complete, plan_invalidated, approval, constraint, recommendation
    severity: str = "info"  # info, warning, critical
    title: str
    body: str
    suggested_actions: list[str] = []
    related_ids: list[str] = []


class CopilotCommand(BaseModel):
    input: str
    source_state_id: str | None = None


class CopilotResponse(BaseModel):
    type: str  # text, coas, explanation, simulation, brief, comparison, focus, error
    message: str
    data: dict[str, Any] = {}
    source_state_id: str = ""
    suggested_actions: list[str] = []


class CopilotStatus(BaseModel):
    provider: str  # gemini, mock
    model: str
    scenario_id: str
    feed_count: int
    session_commands: int
