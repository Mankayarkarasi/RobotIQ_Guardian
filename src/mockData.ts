import { 
  RoboticArmUnit, 
  VisualIntelligenceReport, 
  AdkInvestigationReport, 
  ArmEventRecord, 
  SimulatedRecoveryPlan, 
  PocEvidenceRecord 
} from './types';

export const INITIAL_ARM_FLEET: RoboticArmUnit[] = [
  {
    id: 'ARM-CELL-03',
    name: 'Precision Arm KR-210',
    model: '6-Axis Heavy Duty Articulated Industrial Manipulator',
    workcell: 'Workcell 03 - Transmission Subassembly',
    line: 'Line B (Powertrain Assembly)',
    status: 'degraded',
    application: 'Gearbox Housing Infeed & Precision Pin Press',
    payloadKg: 18.4,
    maxPayloadKg: 35.0,
    cycleTimeSeconds: 28.4,
    dailyCycleCount: 1420,
    joint3HealthScore: 54, // Degraded!
    activeIncidentId: 'INC-4029',
    lastInspectionTimestamp: '2026-10-17 08:45:12 UTC',
    activeWorkpiece: 'Transmission Casing Housing #TX-884',
    joints: [
      { id: 'j1', name: 'Base Rotation (Azimuth)', axis: 'J1', torqueNm: 84.2, ratedTorqueNm: 220.0, positionErrorDeg: 0.02, velocityRadS: 1.45, temperatureC: 38.4, vibrationRms: 0.8, degradationStatus: 'nominal' },
      { id: 'j2', name: 'Shoulder Elevation (Boom)', axis: 'J2', torqueNm: 142.0, ratedTorqueNm: 260.0, positionErrorDeg: 0.04, velocityRadS: 1.10, temperatureC: 44.1, vibrationRms: 1.2, degradationStatus: 'nominal' },
      { id: 'j3', name: 'Elbow Arm Flexure (Joint 3)', axis: 'J3', torqueNm: 138.8, ratedTorqueNm: 150.0, positionErrorDeg: 0.28, velocityRadS: 0.92, temperatureC: 64.8, vibrationRms: 4.8, degradationStatus: 'critical' },
      { id: 'j4', name: 'Forearm Roll (Wrist 1)', axis: 'J4', torqueNm: 24.5, ratedTorqueNm: 85.0, positionErrorDeg: 0.03, velocityRadS: 2.10, temperatureC: 39.0, vibrationRms: 0.7, degradationStatus: 'nominal' },
      { id: 'j5', name: 'Wrist Pitch (Wrist 2)', axis: 'J5', torqueNm: 18.2, ratedTorqueNm: 60.0, positionErrorDeg: 0.02, velocityRadS: 1.80, temperatureC: 36.5, vibrationRms: 0.6, degradationStatus: 'nominal' },
      { id: 'j6', name: 'Tool Flange Roll (Wrist 3)', axis: 'J6', torqueNm: 11.4, ratedTorqueNm: 40.0, positionErrorDeg: 0.01, velocityRadS: 2.40, temperatureC: 34.2, vibrationRms: 0.5, degradationStatus: 'nominal' }
    ],
    joint3Telemetry: {
      torqueRipplePercent: 16.8, // Baseline is < 4.0%
      backlashArcmin: 3.4, // Baseline is < 1.0 arcmin
      gearMeshFrequencyHz: 120.0,
      vibrationAccelerationG: 0.68, // Normal < 0.20 G
      motorWindingTempC: 64.8, // Normal < 48°C
      lubricantDegradationIndex: 78, // High degradation
      estimatedRemainingCycles: 380
    }
  },
  {
    id: 'ARM-CELL-01',
    name: 'Precision Arm KR-210',
    model: '6-Axis Heavy Duty Articulated Industrial Manipulator',
    workcell: 'Workcell 01 - Engine Block Stamping & Milling',
    line: 'Line A (Machining Line)',
    status: 'nominal',
    application: 'Cast Iron Block High-Speed Transfer',
    payloadKg: 22.0,
    maxPayloadKg: 35.0,
    cycleTimeSeconds: 24.1,
    dailyCycleCount: 1650,
    joint3HealthScore: 94,
    lastInspectionTimestamp: '2026-10-17 07:30:00 UTC',
    activeWorkpiece: 'V6 Engine Block Casting #EB-109',
    joints: [
      { id: 'j1', name: 'Base Rotation', axis: 'J1', torqueNm: 78.0, ratedTorqueNm: 220.0, positionErrorDeg: 0.01, velocityRadS: 1.50, temperatureC: 36.2, vibrationRms: 0.6, degradationStatus: 'nominal' },
      { id: 'j2', name: 'Shoulder Elevation', axis: 'J2', torqueNm: 130.5, ratedTorqueNm: 260.0, positionErrorDeg: 0.02, velocityRadS: 1.20, temperatureC: 41.0, vibrationRms: 0.9, degradationStatus: 'nominal' },
      { id: 'j3', name: 'Elbow Arm Flexure', axis: 'J3', torqueNm: 72.4, ratedTorqueNm: 150.0, positionErrorDeg: 0.03, velocityRadS: 1.35, temperatureC: 42.0, vibrationRms: 0.8, degradationStatus: 'nominal' },
      { id: 'j4', name: 'Forearm Roll', axis: 'J4', torqueNm: 21.0, ratedTorqueNm: 85.0, positionErrorDeg: 0.01, velocityRadS: 2.20, temperatureC: 37.1, vibrationRms: 0.5, degradationStatus: 'nominal' },
      { id: 'j5', name: 'Wrist Pitch', axis: 'J5', torqueNm: 16.4, ratedTorqueNm: 60.0, positionErrorDeg: 0.01, velocityRadS: 1.90, temperatureC: 35.0, vibrationRms: 0.4, degradationStatus: 'nominal' },
      { id: 'j6', name: 'Tool Flange Roll', axis: 'J6', torqueNm: 9.8, ratedTorqueNm: 40.0, positionErrorDeg: 0.01, velocityRadS: 2.50, temperatureC: 33.0, vibrationRms: 0.4, degradationStatus: 'nominal' }
    ],
    joint3Telemetry: {
      torqueRipplePercent: 3.2,
      backlashArcmin: 0.8,
      gearMeshFrequencyHz: 120.0,
      vibrationAccelerationG: 0.15,
      motorWindingTempC: 42.0,
      lubricantDegradationIndex: 12,
      estimatedRemainingCycles: 8500
    }
  },
  {
    id: 'ARM-CELL-02',
    name: 'Welding Manipulator AW-180',
    model: '6-Axis High-Accuracy Spot Welding Articulated Arm',
    workcell: 'Workcell 02 - Body Frame Robotic Spot Weld',
    line: 'Line A (Welding Subassembly)',
    status: 'nominal',
    application: 'Automated Spot Welding on Chassis Rail B',
    payloadKg: 14.5,
    maxPayloadKg: 25.0,
    cycleTimeSeconds: 31.0,
    dailyCycleCount: 1310,
    joint3HealthScore: 91,
    lastInspectionTimestamp: '2026-10-17 08:00:00 UTC',
    activeWorkpiece: 'Side Sill Reinforcement Frame #FR-402',
    joints: [
      { id: 'j1', name: 'Base Rotation', axis: 'J1', torqueNm: 62.0, ratedTorqueNm: 180.0, positionErrorDeg: 0.02, velocityRadS: 1.30, temperatureC: 37.5, vibrationRms: 0.7, degradationStatus: 'nominal' },
      { id: 'j2', name: 'Shoulder Elevation', axis: 'J2', torqueNm: 112.0, ratedTorqueNm: 220.0, positionErrorDeg: 0.03, velocityRadS: 1.05, temperatureC: 43.8, vibrationRms: 1.0, degradationStatus: 'nominal' },
      { id: 'j3', name: 'Elbow Arm Flexure', axis: 'J3', torqueNm: 68.2, ratedTorqueNm: 130.0, positionErrorDeg: 0.04, velocityRadS: 1.25, temperatureC: 44.5, vibrationRms: 1.1, degradationStatus: 'nominal' },
      { id: 'j4', name: 'Forearm Roll', axis: 'J4', torqueNm: 18.5, ratedTorqueNm: 70.0, positionErrorDeg: 0.02, velocityRadS: 2.00, temperatureC: 38.0, vibrationRms: 0.6, degradationStatus: 'nominal' },
      { id: 'j5', name: 'Wrist Pitch', axis: 'J5', torqueNm: 14.2, ratedTorqueNm: 50.0, positionErrorDeg: 0.02, velocityRadS: 1.70, temperatureC: 36.2, vibrationRms: 0.5, degradationStatus: 'nominal' },
      { id: 'j6', name: 'Tool Flange Roll', axis: 'J6', torqueNm: 8.5, ratedTorqueNm: 35.0, positionErrorDeg: 0.01, velocityRadS: 2.20, temperatureC: 34.0, vibrationRms: 0.4, degradationStatus: 'nominal' }
    ],
    joint3Telemetry: {
      torqueRipplePercent: 3.8,
      backlashArcmin: 0.9,
      gearMeshFrequencyHz: 118.0,
      vibrationAccelerationG: 0.18,
      motorWindingTempC: 44.5,
      lubricantDegradationIndex: 18,
      estimatedRemainingCycles: 7400
    }
  },
  {
    id: 'ARM-CELL-04',
    name: 'Palletizing Cell HP-300',
    model: '6-Axis High-Payload End-of-Line Palletizer',
    workcell: 'Workcell 04 - End-of-Line Packaging & Pallet',
    line: 'Line C (Packaging & Logistics)',
    status: 'nominal',
    application: 'Automated Transmission Crate Stacking',
    payloadKg: 48.0,
    maxPayloadKg: 80.0,
    cycleTimeSeconds: 19.5,
    dailyCycleCount: 2100,
    joint3HealthScore: 88,
    lastInspectionTimestamp: '2026-10-17 06:15:00 UTC',
    activeWorkpiece: 'Finished Gearbox Master Crate #CR-90',
    joints: [
      { id: 'j1', name: 'Base Rotation', axis: 'J1', torqueNm: 120.0, ratedTorqueNm: 350.0, positionErrorDeg: 0.03, velocityRadS: 1.60, temperatureC: 40.2, vibrationRms: 0.9, degradationStatus: 'nominal' },
      { id: 'j2', name: 'Shoulder Elevation', axis: 'J2', torqueNm: 195.0, ratedTorqueNm: 400.0, positionErrorDeg: 0.04, velocityRadS: 1.30, temperatureC: 46.5, vibrationRms: 1.4, degradationStatus: 'nominal' },
      { id: 'j3', name: 'Elbow Arm Flexure', axis: 'J3', torqueNm: 110.0, ratedTorqueNm: 250.0, positionErrorDeg: 0.05, velocityRadS: 1.40, temperatureC: 45.0, vibrationRms: 1.3, degradationStatus: 'nominal' },
      { id: 'j4', name: 'Forearm Roll', axis: 'J4', torqueNm: 35.0, ratedTorqueNm: 120.0, positionErrorDeg: 0.02, velocityRadS: 2.10, temperatureC: 39.2, vibrationRms: 0.8, degradationStatus: 'nominal' },
      { id: 'j5', name: 'Wrist Pitch', axis: 'J5', torqueNm: 28.0, ratedTorqueNm: 90.0, positionErrorDeg: 0.02, velocityRadS: 1.80, temperatureC: 37.0, vibrationRms: 0.7, degradationStatus: 'nominal' },
      { id: 'j6', name: 'Tool Flange Roll', axis: 'J6', torqueNm: 16.0, ratedTorqueNm: 60.0, positionErrorDeg: 0.01, velocityRadS: 2.30, temperatureC: 35.0, vibrationRms: 0.5, degradationStatus: 'nominal' }
    ],
    joint3Telemetry: {
      torqueRipplePercent: 4.5,
      backlashArcmin: 1.1,
      gearMeshFrequencyHz: 122.0,
      vibrationAccelerationG: 0.22,
      motorWindingTempC: 45.0,
      lubricantDegradationIndex: 25,
      estimatedRemainingCycles: 6200
    }
  }
];

export const INITIAL_VISUAL_REPORT: VisualIntelligenceReport = {
  modelName: 'Gemini Robotics ER 2',
  modelVersion: 'gemini-robotics-er2-inspection-v1',
  targetJoint: 'Joint-3 (Elbow Flexure Harmonic Reducer Housing)',
  incidentId: 'INC-4029',
  inspectionTimestamp: '2026-10-17 08:42:35 UTC',
  overallWearAssessment: 'Sub-surface bearing fatigue and mechanical fretting detected on Joint-3 wave generator casing. Noticeable thermal gradient (+18.2°C above ambient) localized to harmonic gear interface with lubricant weeping past secondary labyrinth seal.',
  confidenceScore: 94.6,
  thermalDifferentialC: 18.2,
  opticalWearNotes: 'Inspection camera shows fine micro-abrasive iron particulate residue embedded in grease fringe around the flexspline perimeter. Structural casing integrity intact, but clearance backlash has expanded to 3.4 arcmin.',
  simulatedCaptureLabel: 'Arm-Cell-03 / Eye-in-Hand High-Resolution Macro Camera 03-B',
  observations: [
    {
      id: 'OBS-01',
      region: 'Joint-3 Gear Flange Seal Interface',
      label: 'Lubricant Weepage & Particulate Staining',
      confidence: 96.2,
      description: 'Localized synthetic grease leakage along lower labyrinth rim with dark particulate discoloration indicative of gear tooth contact fretting.',
      coordinates: { x: 34, y: 42, width: 32, height: 26 },
      status: 'warning'
    },
    {
      id: 'OBS-02',
      region: 'Wave Generator Bearing Hub',
      label: 'Thermal Concentration Ring',
      confidence: 93.8,
      description: 'Thermal imaging overlay reveals localized hot spot centered at 64.8°C on bearing hub versus 44.1°C adjacent boom baseline.',
      coordinates: { x: 40, y: 30, width: 22, height: 20 },
      status: 'alert'
    },
    {
      id: 'OBS-03',
      region: 'Flexspline Outer Housing',
      label: 'Surface Casting Integrity',
      confidence: 98.4,
      description: 'No external structural fractures or mechanical impact gouges observed on the cast aluminum arm elbow shell.',
      coordinates: { x: 20, y: 20, width: 60, height: 60 },
      status: 'nominal'
    }
  ]
};

export const INITIAL_ADK_REPORT: AdkInvestigationReport = {
  framework: 'Google ADK (Agent Development Kit)',
  agentName: 'Industrial Arm Diagnostics & Degradation Reasoning Agent',
  incidentId: 'INC-4029',
  executionStatus: 'completed',
  primaryHypothesis: 'Mechanical degradation of Joint-3 harmonic drive wave generator bearing and flexspline teeth due to cyclic reversal shock loads under 18.4 kg payload, leading to 16.8% torque ripple and backlash expansion.',
  confidence: 94.2,
  recommendedMitigation: 'Simulate derating Joint-3 peak acceleration to 60% and feed rate to 70% to arrest wear progression, while scheduling physical grease replacement and harmonic drive service at upcoming shift changeover.',
  steps: [
    {
      stepNumber: 1,
      phase: 'Telemetry Ingest',
      title: 'Automated Anomaly Detection on Joint-3 Signal Stream',
      timestamp: '08:42:10 UTC',
      toolInvoked: 'adk.telemetry.query_timeseries(arm_id="ARM-CELL-03", axis="J3")',
      reasoning: 'Continuous telemetry monitoring flagged statistically significant deviations in Joint-3 motor current draw and angular velocity tracking variance during infeed stroke.',
      findings: 'Torque ripple reached 16.8% (nominal baseline < 4.0%). Temperature rose steadily from 46°C to 64.8°C over 180 continuous work cycles.',
      status: 'completed'
    },
    {
      stepNumber: 2,
      phase: 'Kinematics Validation',
      title: 'Dynamic Payload & Kinematic Torque Verification',
      timestamp: '08:42:18 UTC',
      toolInvoked: 'adk.kinematics.evaluate_dynamics(arm_model="KR-210", payload_kg=18.4)',
      reasoning: 'Rule out external tooling overloading by comparing current 18.4 kg workpiece payload against theoretical dynamics envelope and safety margin.',
      findings: 'Workpiece payload is well within 35.0 kg rated payload (52.5% utilization). Overloading is ruled out as primary cause; root cause is internal mechanical degradation.',
      status: 'completed'
    },
    {
      stepNumber: 3,
      phase: 'Visual Inspection Request',
      title: 'Multimodal Invocation of Gemini Robotics ER 2',
      timestamp: '08:42:25 UTC',
      toolInvoked: 'gemini_robotics_er2.inspect_joint_visual(arm_id="ARM-CELL-03", joint_axis="J3")',
      reasoning: 'Dispatched optical and thermal camera query to inspect Joint-3 external seal, housing temperature gradient, and mechanical seal integrity.',
      findings: 'Gemini Robotics ER 2 confirmed lubricant weeping and severe thermal gradient (+18.2°C above ambient) concentrated at the wave generator hub.',
      status: 'completed'
    },
    {
      stepNumber: 4,
      phase: 'Multimodal Cross-Analysis',
      title: 'Synthesis of Telemetry, Spectral Harmonics & Visual Evidence',
      timestamp: '08:42:36 UTC',
      toolInvoked: 'adk.diagnostics.synthesize_fault_tree()',
      reasoning: 'Correlating 120 Hz gear mesh vibration peak with 3.4 arcmin backlash and visual grease weepage to isolate specific component failure mechanism.',
      findings: 'Definitive fault signature of harmonic drive wave generator flex-bearing fatigue and lubricant breakdown in Joint-3.',
      status: 'completed'
    },
    {
      stepNumber: 5,
      phase: 'Mitigation Formulation',
      title: 'Human-Approved Simulation Plan Generation',
      timestamp: '08:42:45 UTC',
      toolInvoked: 'adk.planning.generate_mitigation_plan()',
      reasoning: 'Formulated non-disruptive software derating profile that enables Arm-Cell-03 to complete the current production batch safely until maintenance window.',
      findings: 'Derating Joint-3 acceleration to 60% projected to reduce mechanical contact stress by 38.5% and prevent unexpected line stoppage.',
      status: 'completed'
    }
  ]
};

export const INITIAL_ARM_EVENTS: ArmEventRecord[] = [
  {
    id: 'EVT-904',
    incidentId: 'INC-4029',
    timestamp: '08:42:45 UTC',
    cycleNumber: 1420,
    joint: 'J3 (Elbow)',
    severity: 'info',
    category: 'ADK Agent Action',
    summary: 'Google ADK diagnostic agent completed multimodal reasoning trace for Joint-3 degradation.',
    metricValue: 'Confidence: 94.2%'
  },
  {
    id: 'EVT-903',
    incidentId: 'INC-4029',
    timestamp: '08:42:35 UTC',
    cycleNumber: 1420,
    joint: 'J3 (Elbow)',
    severity: 'warning',
    category: 'Visual Defect Logged',
    summary: 'Gemini Robotics ER 2 detected grease weeping and 18.2°C thermal delta on Joint-3 housing.',
    metricValue: 'Temp: 64.8°C'
  },
  {
    id: 'EVT-902',
    incidentId: 'INC-4029',
    timestamp: '08:41:50 UTC',
    cycleNumber: 1418,
    joint: 'J3 (Elbow)',
    severity: 'warning',
    category: 'Torque Anomaly',
    summary: 'Joint-3 torque ripple exceeded advisory threshold (16.8% vs 4.0% baseline).',
    metricValue: 'Ripple: 16.8%'
  },
  {
    id: 'EVT-901',
    incidentId: 'INC-4029',
    timestamp: '08:35:12 UTC',
    cycleNumber: 1405,
    joint: 'J3 (Elbow)',
    severity: 'info',
    category: 'Thermal Advisory',
    summary: 'Joint-3 winding temperature crossed 60°C warning boundary during heavy infeed stroke.',
    metricValue: 'Temp: 61.2°C'
  },
  {
    id: 'EVT-900',
    incidentId: 'INC-4029',
    timestamp: '08:00:00 UTC',
    cycleNumber: 1330,
    joint: 'System',
    severity: 'info',
    category: 'Workcell Event',
    summary: 'Shift B transmission assembly batch started on Arm-Cell-03.',
    metricValue: 'Batch: TX-884'
  }
];

export const INITIAL_RECOVERY_PLANS: SimulatedRecoveryPlan[] = [
  {
    id: 'PLAN-01',
    targetArmId: 'ARM-CELL-03',
    incidentId: 'INC-4029',
    title: 'Simulate Joint-3 Dynamic Torque & Acceleration Derating (70%)',
    description: 'Simulates capping Joint-3 maximum rotational acceleration to 60% and feed rate to 70% in software trajectory generator to reduce flexspline tooth contact stress by 38.5% until planned maintenance.',
    interventionType: 'derate_torque',
    projectedStressReduction: '-38.5% mechanical load',
    requiresTechnicianSignoff: true,
    status: 'pending_approval',
    simulationNote: 'PoC Simulation Mode: Adjusts software motion interpolation profile. Does not perform physical machine actuation.',
    checklist: {
      payload_verified: true,
      telemetry_logged: true,
      shift_supervisor_notified: false
    }
  },
  {
    id: 'PLAN-02',
    targetArmId: 'ARM-CELL-03',
    incidentId: 'INC-4029',
    title: 'Simulate Maintenance Pose Safe Homing Transition',
    description: 'Simulates a low-velocity (0.1 rad/s) controlled trajectory guiding the arm to the ergonomic inspection stand position with mechanical elbow support engaged.',
    interventionType: 'maintenance_homing',
    projectedStressReduction: 'Zero static load on Joint-3',
    requiresTechnicianSignoff: true,
    status: 'pending_approval',
    simulationNote: 'PoC Simulation Mode: Verifies waypoint feasibility in kinematic simulator.',
    checklist: {
      stand_clear: true,
      slow_velocity_armed: true,
      lockout_tagout_staged: false
    }
  },
  {
    id: 'PLAN-03',
    targetArmId: 'ARM-CELL-03',
    incidentId: 'INC-4029',
    title: 'Simulate Tool Center Point (TCP) S-Curve Smoothing',
    description: 'Simulates upgrading trapezoidal velocity blending to 5th-order jerk-limited S-curve trajectory to eliminate sudden reversal shock pulses on Joint-3 harmonic drive.',
    interventionType: 'smooth_trajectory',
    projectedStressReduction: '-24.0% peak reversal torque',
    requiresTechnicianSignoff: false,
    status: 'pending_approval',
    simulationNote: 'PoC Simulation Mode: Calculates trajectory smoothness metrics.',
    checklist: {
      trajectory_verified: true,
      jerk_limit_checked: true
    }
  },
  {
    id: 'PLAN-04',
    targetArmId: 'ARM-CELL-03',
    incidentId: 'INC-4029',
    title: 'Simulate Controlled Workcell Cycle Completion & Standby Hold',
    description: 'Simulates allowing current transmission housing #TX-884 to safely finish insertion, then commanding workcell infeed gate into safe standby.',
    interventionType: 'cycle_hold',
    projectedStressReduction: 'Prevents mid-cycle workpiece defect',
    requiresTechnicianSignoff: true,
    status: 'pending_approval',
    simulationNote: 'PoC Simulation Mode: Demonstrates graceful manufacturing cycle termination.',
    checklist: {
      current_part_monitored: true,
      conveyor_interlock_ready: true
    }
  }
];

export const INITIAL_POC_EVIDENCE: PocEvidenceRecord[] = [
  {
    id: 'EVD-301',
    armId: 'ARM-CELL-03',
    incidentId: 'INC-4029',
    targetJoint: 'Joint-3 (Elbow Harmonic Reducer)',
    timestamp: '2026-10-17 08:43:00 UTC',
    reportType: 'Multimodal Joint-3 Degradation Investigation Package',
    telemetryFramesCount: 4200,
    adkTraceId: 'adk-trace-kr210-j3-4091',
    geminiModelVersion: 'gemini-robotics-er2-inspection-v1',
    fileSizeKb: 1240,
    summary: 'Captured high-rate telemetry time-series, Gemini Robotics ER 2 visual inspection macros, and Google ADK diagnostic reasoning chain for incident INC-4029.'
  },
  {
    id: 'EVD-300',
    armId: 'ARM-CELL-03',
    incidentId: 'INC-4020',
    targetJoint: 'Joint-3 (Baseline Nominal Run)',
    timestamp: '2026-10-17 07:00:00 UTC',
    reportType: 'Shift A Baseline Telemetry Reference',
    telemetryFramesCount: 3600,
    adkTraceId: 'adk-trace-kr210-j3-baseline',
    geminiModelVersion: 'gemini-robotics-er2-inspection-v1',
    fileSizeKb: 980,
    summary: 'Nominal baseline telemetry snapshot prior to torque ripple onset for comparative wear analysis.'
  }
];
