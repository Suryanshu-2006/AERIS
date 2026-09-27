export interface CylinderState {
  cylinder_id: number;
  egt_c: number;
  cht_c: number;
  combustion_efficiency: number;
  cooling_effectiveness: number;
}

export interface TelemetryData {
  timestamp: number;
  rpm: number;
  manifold_pressure_inhg: number;
  egt_1: number;
  egt_2: number;
  egt_3: number;
  egt_4: number;
  mean_egt_c: number;
  cht_1: number;
  cht_2: number;
  cht_3: number;
  cht_4: number;
  mean_cht_c: number;
  oil_pressure_psi: number;
  oil_temperature_c: number;
  turbo_boost_psi: number;
  vibration_g: number;
  bus_voltage: number;
  fuel_flow_gph: number;
  altitude_ft?: number;
  ambient_temp_c?: number;
  mission_phase?: string;
}

export interface HealthScores {
  engine: number;
  combustion: number;
  cooling: number;
  lubrication: number;
  turbo: number;
  mechanical: number;
  electrical: number;
  sensors: number;
}

export interface FaultHypothesis {
  fault_id: string;
  fault_name: string;
  category: 'MECHANICAL' | 'SENSOR' | 'MODEL_MISMATCH' | 'UNKNOWN';
  severity: number;
  confidence: number;
  subsystem: string;
  affected_components: string[];
}

export interface AnomalyResult {
  timestamp: number;
  anomaly_score: number;
  confidence: number;
  is_anomalous: boolean;
  severity: string;
  anomalous_channels: string[];
  description: string;
}

export interface SensorIntegrityResult {
  sensor_name: string;
  integrity_score: number;
  is_faulty: boolean;
  fault_type: string;
  evidence: string[];
  confidence: number;
}

export interface EvidenceItem {
  step: string;
  description: string;
  confidence: number;
  timestamp: number;
}

export interface DiagnosisState {
  timestamp: number;
  anomaly: AnomalyResult;
  primary_fault?: FaultHypothesis;
  alternative_hypotheses: FaultHypothesis[];
  sensor_integrity: SensorIntegrityResult[];
  observation: string;
  diagnosis_summary: string;
  recommendation: string;
}

export interface RULEstimate {
  component: string;
  rul_hours: number;
  lower_bound_hours: number;
  upper_bound_hours: number;
  confidence: number;
  is_model_estimate: boolean;
}

export interface MissionSafeHorizon {
  safe_hours: number;
  lower_bound_hours: number;
  upper_bound_hours: number;
  confidence: number;
  limiting_factor: string;
  limiting_subsystem: string;
}

export interface PhaseRisk {
  phase: string;
  risk: number;
  altitude_ft: number;
  throttle: number;
  duration_h: number;
  stress_factor: number;
}

export interface MissionRiskResult {
  mission_id: string;
  mission_risk_score: number;
  mission_readiness: 'READY' | 'CAUTION' | 'WARNING' | 'NOT_READY';
  critical_phase: string;
  critical_phase_risk: number;
  risk_drivers: string[];
  safe_horizon_hours: number;
  phase_risks: PhaseRisk[];
  engine_health: number;
}

export interface WhatIfTrajectoryPoint {
  time_hours: number;
  phase: string;
  health: number;
  temperature_c: number;
  oil_pressure_psi: number;
  rul_hours: number;
  risk_score: number;
  safe_horizon_hours: number;
}

export interface WhatIfResult {
  baseline_risk: MissionRiskResult;
  modified_risk: MissionRiskResult;
  baseline_trajectory: WhatIfTrajectoryPoint[];
  modified_trajectory: WhatIfTrajectoryPoint[];
  risk_delta: number;
  safe_horizon_delta: number;
  critical_phase_changed: boolean;
  summary: string;
  recommendation: string;
}

export interface SystemState {
  timestamp: number;
  mode: 'LIVE' | 'SIMULATION' | 'REPLAY';
  is_running: boolean;
  is_paused: boolean;
  telemetry: TelemetryData;
  twin: {
    expected: Record<string, number>;
    residuals: Record<string, number>;
  };
  health: HealthScores;
  diagnosis: DiagnosisState;
  prognostics: {
    engine_rul?: RULEstimate;
    mission_safe_horizon?: MissionSafeHorizon;
  };
  mission_risk: MissionRiskResult;
  evidence_chain: EvidenceItem[];
  recommendation: string;
  active_faults: any[];
}

export interface AircraftProfile {
  id: string;
  tailNumber: string;
  callsign: string;
  model: string;
  engineConfig: string;
  status: 'ACTIVE_SORTIE' | 'LOITER_PATROL' | 'CLIMB_EN_ROUTE' | 'STANDBY';
  altitudeFt: number;
  airspeedKts: number;
  linkHealth: string;
  eng1Name: string;
  eng2Name: string;
}
