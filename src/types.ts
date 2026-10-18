export type NavSection = 'fleet' | 'investigate' | 'recover' | 'evidence';

export type InvestigateTab = 
  | 'overview' 
  | 'telemetry' 
  | 'visual_intelligence' 
  | 'agentic_investigation' 
  | 'events_timeline';

export type ArmStatus = 'nominal' | 'degraded' | 'maintenance_required' | 'cycle_paused';

export interface ArmJointMetric {
  id: string;
  name: string;
  axis: 'J1' | 'J2' | 'J3' | 'J4' | 'J5' | 'J6';
  torqueNm: number;
  ratedTorqueNm: number;
  positionErrorDeg: number;
  velocityRadS: number;
  temperatureC: number;
  vibrationRms: number; // mm/s
  degradationStatus: 'nominal' | 'advisory' | 'critical';
}

export interface Joint3DetailedTelemetry {
  torqueRipplePercent: number; // baseline < 4%, degraded ~16.8%
  backlashArcmin: number; // baseline < 1.0, degraded 3.4
  gearMeshFrequencyHz: number; // 120 Hz
  vibrationAccelerationG: number;
  motorWindingTempC: number;
  lubricantDegradationIndex: number; // 0-100
  estimatedRemainingCycles: number;
}

export interface RoboticArmUnit {
  id: string;
  name: string;
  model: string;
  workcell: string;
  line: string;
  status: ArmStatus;
  application: string;
  payloadKg: number;
  maxPayloadKg: number;
  cycleTimeSeconds: number;
  dailyCycleCount: number;
  joint3HealthScore: number; // 0-100%
  activeIncidentId?: string; // Stable incident ID, e.g. 'INC-4029'
  joints: ArmJointMetric[];
  joint3Telemetry: Joint3DetailedTelemetry;
  lastInspectionTimestamp: string;
  activeWorkpiece: string;
}

export interface VisualObservation {
  id: string;
  region: string;
  label: string;
  confidence: number;
  description: string;
  coordinates: { x: number; y: number; width: number; height: number }; // percentage
  status: 'warning' | 'alert' | 'nominal';
}

export interface VisualIntelligenceReport {
  modelName: string; // 'Gemini Robotics ER 2'
  modelVersion: string;
  targetJoint: string; // 'Joint-3 (Elbow Flexure)'
  incidentId: string; // 'INC-4029'
  inspectionTimestamp: string;
  overallWearAssessment: string;
  confidenceScore: number;
  observations: VisualObservation[];
  thermalDifferentialC: number;
  opticalWearNotes: string;
  simulatedCaptureLabel: string;
}

export interface AdkInvestigationStep {
  stepNumber: number;
  phase: 'Prediction Agent' | 'Prevention Agent' | 'Investigation Agent' | 'Recovery Agent' | 'Learning Agent';
  title: string;
  toolInvoked?: string;
  timestamp: string;
  reasoning: string;
  findings: string;
  status: 'completed' | 'in_progress';
}

export interface AdkInvestigationReport {
  framework: string; // 'Google ADK (Agent Development Kit)'
  agentName: string;
  incidentId: string; // 'INC-4029'
  executionStatus: 'completed' | 'running';
  primaryHypothesis: string;
  confidence: number;
  recommendedMitigation: string;
  steps: AdkInvestigationStep[];
}

export interface ArmEventRecord {
  id: string;
  incidentId?: string; // 'INC-4029'
  timestamp: string;
  cycleNumber: number;
  joint: string;
  severity: 'critical' | 'warning' | 'info';
  category: 'Torque Anomaly' | 'Thermal Advisory' | 'Visual Defect Logged' | 'Workcell Event' | 'ADK Agent Action';
  summary: string;
  metricValue?: string;
}

export interface SimulatedRecoveryPlan {
  id: string;
  targetArmId: string;
  incidentId: string; // 'INC-4029'
  title: string;
  description: string;
  interventionType: 'derate_torque' | 'maintenance_homing' | 'smooth_trajectory' | 'cycle_hold';
  projectedStressReduction: string;
  requiresTechnicianSignoff: boolean;
  status: 'pending_approval' | 'simulating' | 'simulation_applied';
  signoffTechnician?: string;
  workOrderId?: string;
  simulationNote: string;
  checklist?: Record<string, boolean>;
}

export interface PocEvidenceRecord {
  id: string;
  armId: string;
  incidentId: string; // 'INC-4029'
  targetJoint: string;
  timestamp: string;
  reportType: string;
  telemetryFramesCount: number;
  adkTraceId: string;
  geminiModelVersion: string;
  fileSizeKb: number;
  summary: string;
}

export interface BackendState {
  connected: boolean;
  latencyMs: number;
  url: string;
  lastChecked: string;
  error?: string;
}
