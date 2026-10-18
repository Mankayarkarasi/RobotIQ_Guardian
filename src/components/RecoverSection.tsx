import type { GuardianIncidentDetail } from '../services/api';
import React, { useState } from 'react';
import { RoboticArmUnit, SimulatedRecoveryPlan } from '../types';
import { 
  RefreshCw, CheckCircle2, AlertTriangle, Play, 
  Wrench, FileText, CheckSquare, Square, Info, ShieldCheck, XCircle, HelpCircle, Clock
} from 'lucide-react';

interface RecoverSectionProps {
  liveIncident?: GuardianIncidentDetail | null;
  arms: RoboticArmUnit[];
  plans: SimulatedRecoveryPlan[];
  backendLinked?: boolean;
  selectedArmId: string;
  selectedIncidentId: string;
  onApplySimulatedPlan: (planId: string, technician: string, workOrder: string) => void;
  onUpdatePlanChecklist?: (planId: string, key: string, value: boolean) => void;
}

export type ApprovalStatus = 'PENDING_APPROVAL' | 'READY_FOR_APPROVAL' | 'APPROVED' | 'REVISION_REQUESTED' | 'REJECTED';

interface ApprovalRecord {
  decisionId: string;
  robotId: string;
  incidentId: string;
  planId: string;
  specialistName: string;
  workOrderId: string;
  decisionType: 'APPROVED' | 'REVISION_REQUESTED' | 'REJECTED';
  reasonOrComment: string;
  timestamp: string;
  demoIndicator: string;
}

export const RecoverSection: React.FC<RecoverSectionProps> = ({
  liveIncident,
  arms,
  plans,
  backendLinked = false,
  selectedArmId,
  selectedIncidentId,
  onApplySimulatedPlan,
  onUpdatePlanChecklist
}) => {
  const [selectedPlanId, setSelectedPlanId] = useState<string>(plans[0]?.id || '');
  const [technicianName, setTechnicianName] = useState<string>('');
  const [workOrderId, setWorkOrderId] = useState<string>('');
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simulationResult, setSimulationResult] = useState<string | null>(null);

  // Per-plan approval state mapping
  const [planApprovals, setPlanApprovals] = useState<Record<string, ApprovalRecord>>({});
  
  // Modal / input state for Revision / Rejection reasons
  const [activeDecisionModal, setActiveDecisionModal] = useState<'REVISION' | 'REJECT' | null>(null);
  const [decisionReasonInput, setDecisionReasonInput] = useState<string>('');

  const selectedPlan = plans.find(p => p.id === selectedPlanId) || plans[0];
  const proposedActions = liveIncident?.recovery_plan?.recommended_actions || [];
  const selectedArm = arms.find(a => a.id === selectedArmId) || arms[0];

  const currentChecklist = selectedPlan.checklist || {
    safety_clear: true,
    telemetry_logged: true,
    scheduled_downtime_notified: false
  };

  const handleToggleCheck = (key: string) => {
    const nextVal = !currentChecklist[key];
    if (onUpdatePlanChecklist) {
      onUpdatePlanChecklist(selectedPlan.id, key, nextVal);
    }
  };

  // Validation checks
  const allChecksComplete = Object.values(currentChecklist).every(Boolean);
  const hasSpecialist = technicianName.trim().length > 0;
  const hasWorkOrder = workOrderId.trim().length > 0;
  const isSafetyVerified = allChecksComplete && hasSpecialist && hasWorkOrder;

  // Current plan approval record
  const currentApproval = planApprovals[selectedPlan.id];
  const approvalStatus: ApprovalStatus = currentApproval 
    ? (currentApproval.decisionType === 'APPROVED' ? 'APPROVED' : currentApproval.decisionType === 'REVISION_REQUESTED' ? 'REVISION_REQUESTED' : 'REJECTED')
    : (isSafetyVerified ? 'READY_FOR_APPROVAL' : 'PENDING_APPROVAL');

  // Handle Approve
  const handleApprovePlan = () => {
    if (backendLinked || !isSafetyVerified) return;
    const record: ApprovalRecord = {
      decisionId: `DEC-${Math.floor(1000 + Math.random() * 9000)}`,
      robotId: selectedArm.id,
      incidentId: selectedIncidentId,
      planId: selectedPlan.id,
      specialistName: technicianName,
      workOrderId,
      decisionType: 'APPROVED',
      reasonOrComment: 'Plan verified against kinetic envelope & approved for simulation execution.',
      timestamp: new Date().toLocaleTimeString(),
      demoIndicator: 'Demo Session Approval (Backend Integration Pending)'
    };
    setPlanApprovals(prev => ({ ...prev, [selectedPlan.id]: record }));
  };

  // Handle Submit Revision Request or Rejection with Reason
  const handleSubmitReasonDecision = () => {
    if (backendLinked || !activeDecisionModal || !decisionReasonInput.trim()) return;
    const decisionType = activeDecisionModal === 'REVISION' ? 'REVISION_REQUESTED' : 'REJECTED';
    const record: ApprovalRecord = {
      decisionId: `DEC-${Math.floor(1000 + Math.random() * 9000)}`,
      robotId: selectedArm.id,
      incidentId: selectedIncidentId,
      planId: selectedPlan.id,
      specialistName: technicianName,
      workOrderId,
      decisionType,
      reasonOrComment: decisionReasonInput.trim(),
      timestamp: new Date().toLocaleTimeString(),
      demoIndicator: 'Demo Session Approval (Backend Integration Pending)'
    };
    setPlanApprovals(prev => ({ ...prev, [selectedPlan.id]: record }));
    setActiveDecisionModal(null);
    setDecisionReasonInput('');
  };

  // Simulation gating logic: requires safety verification AND explicit approval
  const canSimulate = !backendLinked && isSafetyVerified && approvalStatus === 'APPROVED' && selectedPlan.status !== 'simulation_applied';

  const handleExecuteSimulation = () => {
    if (!canSimulate) return;
    setIsSimulating(true);
    setSimulationResult(null);

    setTimeout(() => {
      onApplySimulatedPlan(selectedPlan.id, technicianName, workOrderId);
      setIsSimulating(false);
      setSimulationResult(`Simulated profile applied successfully to kinematic trajectory preview for ${selectedPlan.targetArmId} (${selectedPlan.incidentId}). Stress reduced by 38.5%.`);
    }, 1200);
  };

  // Determine 6-stage workflow statuses
  const stageRecommendation = 'Completed';
  const stagePrediction = 'Completed';
  const stageApproval = approvalStatus === 'APPROVED' ? 'Completed' : approvalStatus === 'REJECTED' ? 'Failed or Rejected' : approvalStatus === 'REVISION_REQUESTED' ? 'In Progress' : isSafetyVerified ? 'Ready' : 'Not Started';
  const stageSimulation = selectedPlan.status === 'simulation_applied' ? 'Completed' : isSimulating ? 'In Progress' : approvalStatus === 'APPROVED' ? 'Ready' : 'Blocked';
  const stageVerification = selectedPlan.status === 'simulation_applied' ? 'Ready' : 'Pending';
  const stageOutcome = selectedPlan.status === 'simulation_applied' ? 'Awaiting Validation' : 'Awaiting';

  return (
    <div className="space-y-6">
      {backendLinked && <div className="text-xs font-mono rounded-lg border border-amber-700/60 bg-amber-950/30 px-4 py-3 text-amber-300" role="status">Backend-linked incident: the proposal below is derived from the backend. UI-only Approve / Reject / Simulation controls are disabled. Authoritative human approval and simulation must use the FastAPI recovery endpoints; no physical recovery or production resumption is authorized.</div>}
      {/* Header */}
      <div className="pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
          <span>HUMAN-APPROVED RECOVERY PROTOCOLS</span>
          <span className="text-slate-600">·</span>
          <span>SIMULATION PLAYBOOKS</span>
          <span className="text-slate-600">·</span>
          <span className="text-slate-400">[UI-Only Simulation Mode]</span>
        </div>
        <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white font-mono mt-0.5">
          Simulated Workcell Recovery & Verification
        </h1>
        <p className="text-xs text-slate-400 mt-1 max-w-3xl">
          Backend-origin recovery recommendation, human authorization status, and verification requirements. This interface does not actuate physical hardware.
        </p>
      </div>

      {/* 6-Stage Workflow Progress Indicator */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 font-mono">
        <div className="text-[11px] text-slate-400 uppercase tracking-wider mb-3">
          Recovery Workflow Progress Indicator
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
          {/* Stage 1 */}
          <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded flex flex-col justify-between">
            <div className="text-[10px] text-slate-500 uppercase">01. Recommendation</div>
            <div className="mt-1 font-semibold text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Completed</span>
            </div>
          </div>
          {/* Stage 2 */}
          <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded flex flex-col justify-between">
            <div className="text-[10px] text-slate-500 uppercase">02. Prediction</div>
            <div className="mt-1 font-semibold text-cyan-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Ready</span>
            </div>
          </div>
          {/* Stage 3 */}
          <div className={`p-2.5 bg-slate-950/80 border rounded flex flex-col justify-between ${
            approvalStatus === 'APPROVED' ? 'border-emerald-600/80' : approvalStatus === 'REJECTED' ? 'border-red-600/80' : 'border-cyan-600/80'
          }`}>
            <div className="text-[10px] text-slate-500 uppercase">03. Human Approval</div>
            <div className={`mt-1 font-semibold flex items-center gap-1.5 text-xs ${
              approvalStatus === 'APPROVED' ? 'text-emerald-400' : approvalStatus === 'REJECTED' ? 'text-red-400' : approvalStatus === 'REVISION_REQUESTED' ? 'text-amber-400' : 'text-cyan-400'
            }`}>
              {approvalStatus === 'APPROVED' ? <CheckCircle2 className="w-3.5 h-3.5" /> : approvalStatus === 'REJECTED' ? <XCircle className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
              <span>{approvalStatus === 'APPROVED' ? 'Approved' : approvalStatus === 'REJECTED' ? 'Rejected' : approvalStatus === 'REVISION_REQUESTED' ? 'Revision Req.' : isSafetyVerified ? 'Ready' : 'Pending'}</span>
            </div>
          </div>
          {/* Stage 4 */}
          <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded flex flex-col justify-between">
            <div className="text-[10px] text-slate-500 uppercase">04. Simulation</div>
            <div className={`mt-1 font-semibold flex items-center gap-1.5 ${
              selectedPlan.status === 'simulation_applied' ? 'text-emerald-400' : isSimulating ? 'text-cyan-400' : canSimulate ? 'text-cyan-300' : 'text-slate-500'
            }`}>
              <Play className="w-3.5 h-3.5" />
              <span>{selectedPlan.status === 'simulation_applied' ? 'Completed' : isSimulating ? 'Running' : canSimulate ? 'Ready' : 'Blocked'}</span>
            </div>
          </div>
          {/* Stage 5 */}
          <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded flex flex-col justify-between">
            <div className="text-[10px] text-slate-500 uppercase">05. Verification</div>
            <div className="mt-1 font-semibold text-slate-400 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-slate-500" />
              <span>{selectedPlan.status === 'simulation_applied' ? 'Awaiting Validation' : 'Pending'}</span>
            </div>
          </div>
          {/* Stage 6 */}
          <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded flex flex-col justify-between">
            <div className="text-[10px] text-slate-500 uppercase">06. Outcome</div>
            <div className="mt-1 font-semibold text-slate-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-slate-500" />
              <span>{selectedPlan.status === 'simulation_applied' ? 'Validated' : 'Awaiting'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* PoC Simulation Mode Disclaimer Banner */}
      <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono text-slate-300">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>
            <strong className="text-cyan-400">PoC Simulation Mode:</strong> Target Workcell: <strong className="text-white">{selectedArm.id}</strong> · Active Incident: <strong className="text-amber-400">{selectedIncidentId}</strong>.
          </span>
        </div>
        <span className="text-[11px] text-slate-400">
          Data Source: <span className="text-slate-300 font-semibold">Simulated Kinematics Profile</span>
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Playbook List */}
        <div className="space-y-3">
          <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
            Available Simulated Playbooks
          </div>

          <div className="space-y-2">
            {plans.map((plan) => {
              const isSelected = plan.id === selectedPlanId;
              const planAppr = planApprovals[plan.id];
              const badgeLabel = plan.status === 'simulation_applied' 
                ? 'Applied (Sim)' 
                : planAppr?.decisionType === 'APPROVED' 
                ? 'Approved' 
                : planAppr?.decisionType === 'REJECTED' 
                ? 'Rejected' 
                : planAppr?.decisionType === 'REVISION_REQUESTED' 
                ? 'Revision Req.' 
                : 'Pending Review';

              const badgeColor = plan.status === 'simulation_applied'
                ? 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                : planAppr?.decisionType === 'APPROVED'
                ? 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                : planAppr?.decisionType === 'REJECTED'
                ? 'bg-red-950/80 border-red-800 text-red-300'
                : planAppr?.decisionType === 'REVISION_REQUESTED'
                ? 'bg-amber-950/80 border-amber-800 text-amber-300'
                : 'bg-slate-950 border-slate-700 text-amber-300';

              return (
                <button
                  key={plan.id}
                  onClick={() => {
                    setSelectedPlanId(plan.id);
                    setSimulationResult(null);
                  }}
                  className={`w-full p-3.5 rounded-lg text-left transition-all border font-mono ${
                    isSelected
                      ? 'bg-slate-800 border-cyan-500/80 shadow-sm'
                      : 'bg-slate-900/80 border-slate-800 hover:bg-slate-850 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-white">{plan.title.split('(')[0]}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border uppercase ${badgeColor}`}>
                      {badgeLabel}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{plan.description}</p>

                  <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-800/80">
                    <span>Target: <span className="text-slate-300">{plan.targetArmId}</span> ({plan.incidentId})</span>
                    <span className="text-cyan-400 font-semibold">{backendLinked ? 'Backend proposal shown at right' : plan.projectedStressReduction}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Specification, Safety Verification, Human Approval & Simulation Execution */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-5 space-y-5">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider">
                  Simulation Specification
                </span>
                <span className="text-[11px] font-mono text-amber-400">
                  Target: {selectedPlan.targetArmId} · Incident: {selectedPlan.incidentId}
                </span>
              </div>
              <h2 className="text-base font-bold text-white font-mono mt-0.5">{selectedPlan.title}</h2>
              <p className="text-xs text-slate-400 mt-1">{selectedPlan.description}</p>
            </div>

            {liveIncident && (
              <div className="p-4 bg-slate-950/70 rounded-lg border border-amber-800/60 space-y-2 font-mono text-xs">
                <div className="text-amber-300 font-bold">BACKEND RECOVERY PROPOSAL · {liveIncident.recovery_plan?.risk_level || 'Risk not provided'}</div>
                <ol className="list-decimal pl-5 space-y-1 text-slate-300">{proposedActions.map((action,i)=><li key={i}>{action}</li>)}</ol>
                <div className="border-t border-slate-800 pt-2 text-amber-300">Residual risk: {liveIncident.recovery_prediction?.residual_risk || 'Not provided'} · Evidence-based recovery success score: {liveIncident.recovery_prediction?.recovery_success_score ?? 'N/A'} (not calibrated probability)</div>
                <p className="text-slate-400">{liveIncident.recovery_prediction?.summary || 'Physical intervention and verified recovery are required before resumption.'}</p>
                <p className="text-rose-300">Backend authorization not connected to these UI-only controls; simulation and production resumption remain blocked.</p>
              </div>
            )}

            {/* SECTION A: Pre-Simulation Safety Verification */}
            <div className="p-4 bg-slate-950/70 rounded-lg border border-slate-800 space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <div className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  Pre-Simulation Safety Verification
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${
                  isSafetyVerified 
                    ? 'bg-cyan-950/80 border-cyan-600 text-cyan-300' 
                    : 'bg-amber-950/80 border-amber-600 text-amber-300'
                }`}>
                  {isSafetyVerified ? 'Ready for Approval' : 'Incomplete'}
                </span>
              </div>

              <div className="space-y-2 pt-1">
                {Object.entries(currentChecklist).map(([key, checked], idx) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => handleToggleCheck(key)}
                    className="flex items-center gap-2 text-left w-full hover:text-white text-slate-300"
                  >
                    {checked ? (
                      <CheckSquare className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-600 shrink-0" />
                    )}
                    <span>
                      {idx + 1}. {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                  </button>
                ))}
              </div>

              {/* Human Signoff Inputs */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-slate-800/80">
                <div>
                  <label className="text-slate-400 block mb-1 text-[11px]">Authorizing Specialist Name *</label>
                  <input
                    type="text"
                    value={technicianName}
                    onChange={(e) => setTechnicianName(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-white focus:outline-none focus:border-cyan-500 text-xs"
                    placeholder="Enter specialist name"
                  />
                </div>

                <div>
                  <label className="text-slate-400 block mb-1 text-[11px]">Maintenance Work Order Ref *</label>
                  <input
                    type="text"
                    value={workOrderId}
                    onChange={(e) => setWorkOrderId(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-white focus:outline-none focus:border-cyan-500 text-xs"
                    placeholder="Enter work order ID"
                  />
                </div>
              </div>
            </div>

            {/* SECTION B: Human Approval Decision Panel */}
            <div className="p-4 bg-slate-950/80 rounded-lg border border-slate-800 space-y-4 font-mono text-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                  <div>
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                      Human Approval Decision
                    </h3>
                    <span className="text-[10px] text-slate-400">
                      Demo Session Approval — Backend Integration Pending
                    </span>
                  </div>
                </div>

                {/* Status Badge */}
                <div className={`px-2.5 py-1 rounded text-xs font-bold border uppercase tracking-wider ${
                  approvalStatus === 'APPROVED' ? 'bg-emerald-950/90 border-emerald-600 text-emerald-300' :
                  approvalStatus === 'REJECTED' ? 'bg-red-950/90 border-red-600 text-red-300' :
                  approvalStatus === 'REVISION_REQUESTED' ? 'bg-slate-800 border-slate-600 text-slate-300' :
                  approvalStatus === 'READY_FOR_APPROVAL' ? 'bg-cyan-950/90 border-cyan-600 text-cyan-300' :
                  'bg-amber-950/90 border-amber-600 text-amber-300'
                }`}>
                  {approvalStatus === 'APPROVED' ? 'Approved' :
                   approvalStatus === 'REJECTED' ? 'Rejected' :
                   approvalStatus === 'REVISION_REQUESTED' ? 'Revision Requested' :
                   approvalStatus === 'READY_FOR_APPROVAL' ? 'Ready for Approval' :
                   'Pending Approval'}
                </div>
              </div>

              {/* Decision Metadata Display */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] bg-slate-900/60 p-3 rounded border border-slate-800">
                <div>
                  <span className="text-slate-500 block">Robot ID:</span>
                  <span className="text-white font-bold">{selectedArm.id}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Incident:</span>
                  <span className="text-amber-400 font-bold">{selectedIncidentId}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Specialist:</span>
                  <span className="text-slate-200 truncate block">{technicianName || 'Not Set'}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Work Order:</span>
                  <span className="text-slate-200">{workOrderId || 'Not Set'}</span>
                </div>
              </div>

              {/* Decision Summary if recorded */}
              {currentApproval && (
                <div className="p-3 bg-slate-900/90 rounded border border-slate-800 space-y-1.5 text-[11px]">
                  <div className="flex items-center justify-between text-slate-400 font-bold border-b border-slate-800 pb-1">
                    <span>Recorded Decision: {currentApproval.decisionType}</span>
                    <span className="text-slate-500 font-mono">{currentApproval.timestamp}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Comments / Reason:</span>
                    <p className="text-slate-200 mt-0.5">{currentApproval.reasonOrComment}</p>
                  </div>
                  <div className="text-[10px] text-slate-500 italic">
                    {currentApproval.demoIndicator}
                  </div>
                </div>
              )}

              {/* Decision Action Buttons */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <button
                  type="button"
                  disabled={!isSafetyVerified}
                  onClick={handleApprovePlan}
                  className={`px-3.5 py-2 font-bold rounded flex items-center gap-1.5 transition-all ${
                    isSafetyVerified 
                      ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-900/30' 
                      : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  }`}
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Approve Recovery Plan</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveDecisionModal('REVISION')}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-amber-300 font-bold rounded flex items-center gap-1.5 border border-slate-700 transition-colors"
                >
                  <HelpCircle className="w-4 h-4" />
                  <span>Request Revision</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveDecisionModal('REJECT')}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-red-300 font-bold rounded flex items-center gap-1.5 border border-slate-700 transition-colors"
                >
                  <XCircle className="w-4 h-4" />
                  <span>Reject Recovery Plan</span>
                </button>
              </div>

              {!isSafetyVerified && (
                <div className="text-[11px] text-amber-400 font-mono">
                  ⚠ Complete all mandatory pre-simulation safety verification items and provide specialist name and work order to enable approval.
                </div>
              )}
            </div>

            {/* Revision / Rejection Reason Modal / Input Box */}
            {activeDecisionModal && (
              <div className="p-4 bg-slate-950 border border-slate-700 rounded-lg space-y-3 font-mono text-xs">
                <div className="text-xs font-bold text-white flex items-center justify-between">
                  <span>{activeDecisionModal === 'REVISION' ? 'Provide Revision Request Comment' : 'Provide Rejection Reason'}</span>
                  <button 
                    onClick={() => setActiveDecisionModal(null)}
                    className="text-slate-400 hover:text-white"
                  >
                    ✕
                  </button>
                </div>
                <textarea
                  value={decisionReasonInput}
                  onChange={(e) => setDecisionReasonInput(e.target.value)}
                  placeholder={activeDecisionModal === 'REVISION' ? 'Specify required trajectory or threshold adjustments...' : 'Specify safety or operational rationale for rejection...'}
                  className="w-full bg-slate-900 border border-slate-700 rounded p-2.5 text-white text-xs focus:outline-none focus:border-cyan-500 h-20"
                />
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setActiveDecisionModal(null)}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={!decisionReasonInput.trim()}
                    onClick={handleSubmitReasonDecision}
                    className={`px-3 py-1.5 font-bold rounded text-xs ${
                      decisionReasonInput.trim() ? 'bg-cyan-600 hover:bg-cyan-500 text-white' : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                    }`}
                  >
                    Submit {activeDecisionModal === 'REVISION' ? 'Revision Request' : 'Rejection'}
                  </button>
                </div>
              </div>
            )}

            {/* Simulation Status Feedback */}
            {simulationResult && (
              <div className="p-3 bg-emerald-950/50 border border-emerald-800 text-emerald-200 text-xs font-mono rounded flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{simulationResult}</span>
              </div>
            )}

            {/* Execute Simulation Section */}
            <div className="pt-3 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-mono text-xs">
              <div>
                <span className="text-slate-400 block">Simulation Execution Gate:</span>
                <span className={canSimulate ? 'text-emerald-400 font-bold' : 'text-amber-400'}>
                  {canSimulate 
                    ? 'Ready for Simulation Execution (Approved & Verified)' 
                    : approvalStatus !== 'APPROVED' 
                    ? 'Blocked: Requires explicit Human Approval ("Approve Recovery Plan")' 
                    : 'Blocked: Complete safety verification checks & required fields'}
                </span>
              </div>

              <button
                type="button"
                disabled={!canSimulate || isSimulating}
                onClick={handleExecuteSimulation}
                className={`px-4 py-2 font-mono text-xs font-bold rounded flex items-center gap-2 transition-all shrink-0 ${
                  canSimulate && !isSimulating
                    ? 'bg-cyan-600 text-white hover:bg-cyan-500 shadow-md shadow-cyan-900/30'
                    : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                }`}
              >
                {isSimulating ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Evaluating Kinematics Simulation...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Apply Simulated Backend Recovery Proposal</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
