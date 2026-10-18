import React, { useState, useEffect, useCallback } from 'react';
import { 
  NavSection, 
  InvestigateTab,
  RoboticArmUnit, 
  VisualIntelligenceReport, 
  AdkInvestigationReport, 
  ArmEventRecord, 
  SimulatedRecoveryPlan, 
  PocEvidenceRecord, 
  BackendState 
} from './types';
import { checkFastApiHealth, fetchGuardianSnapshot, GuardianIncidentDetail } from './services/api';
import { TopBar } from './components/TopBar';
import { FleetSection } from './components/FleetSection';
import { InvestigateSection } from './components/InvestigateSection';
import { RecoverSection } from './components/RecoverSection';
import { EvidenceSection } from './components/EvidenceSection';

// Empty view-models contain no incident-specific synthetic results.
const emptyVisualReport: VisualIntelligenceReport = {modelName:'Not available',modelVersion:'',targetJoint:'',incidentId:'',inspectionTimestamp:'',overallWearAssessment:'No active backend incident',confidenceScore:0,observations:[],thermalDifferentialC:0,opticalWearNotes:'No active visual analysis',simulatedCaptureLabel:'Illustrative asset'};
const emptyAdkReport: AdkInvestigationReport = {framework:'No active investigation',agentName:'',incidentId:'',executionStatus:'running',primaryHypothesis:'None',confidence:0,recommendedMitigation:'No active backend incident',steps:[]};

export default function App() {
  const [activeSection, setActiveSection] = useState<NavSection>('fleet');
  const [arms, setArms] = useState<RoboticArmUnit[]>([]);
  const [visualReport, setVisualReport] = useState<VisualIntelligenceReport | null>(null);
  const [adkReport, setAdkReport] = useState<AdkInvestigationReport | null>(null);
  const [events, setEvents] = useState<ArmEventRecord[]>([]);
  const [plans, setPlans] = useState<SimulatedRecoveryPlan[]>([]);
  const [evidenceRecords, setEvidenceRecords] = useState<PocEvidenceRecord[]>([]);
  const [selectedArmId, setSelectedArmId] = useState<string>('');
  const [liveIncident, setLiveIncident] = useState<GuardianIncidentDetail | null>(null);
  const [dataWarning, setDataWarning] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [investigateTab, setInvestigateTab] = useState<InvestigateTab>('overview');

  // FastAPI backend state check
  const [backendState, setBackendState] = useState<BackendState>({
    connected: false,
    latencyMs: 0,
    url: '/api',
    lastChecked: 'Checking...',
    error: 'Initial health check in progress'
  });

  const checkBackend = useCallback(async () => {
    setLoading(true);
    const state = await checkFastApiHealth();
    setBackendState(state);
    if (!state.connected) {
      setArms([]); setLiveIncident(null); setPlans([]); setEvents([]); setEvidenceRecords([]);
      setVisualReport(null); setAdkReport(null);
      setDataWarning('Backend disconnected — operational data unavailable. No mock incidents are displayed.');
      setLoading(false); return;
    }
    try {
      const snapshot = await fetchGuardianSnapshot();
      const incident = snapshot.incident;
      setLiveIncident(incident);
      const mapped = snapshot.fleet.map(cell => {
        const active = incident?.cell_id === cell.cell_id;
        const signals = active ? incident.telemetry_result?.breached_signals || [] : [];
        const vib = signals.find(s=>s.signal==='joint_3_vibration');
        const temp = signals.find(s=>s.signal==='temperature');
        const cycle = signals.find(s=>s.signal==='cycle_time');
        return {
          id: `ARM-${cell.cell_id}`, name: `Robot ${cell.robot_id}`, workcell: cell.cell_id,
          model: 'Model not provided by backend', line:'Production line not provided',
          application:'Robotic pick-and-place',activeWorkpiece:'Not provided',
          status: (active || cell.status!=='NORMAL' ? 'degraded':'nominal') as RoboticArmUnit['status'],
          activeIncidentId: active ? incident.incident_id : (cell.active_incident||undefined),
          // This backend reports overall health, not Joint-3 health; used only as display placeholder.
          joint3HealthScore: cell.health_score, // Displayed as backend overall cell health, not Joint-3 health
          cycleTimeSeconds: cycle?.actual ?? 0,
          dailyCycleCount:0, payloadKg:0, maxPayloadKg:0,
          lastInspectionTimestamp: active ? incident.created_at : 'Not provided',
          // Axis names describe the UI schematic only. No joint torque or rated capacity is fabricated.
          joints: (['J1','J2','J3','J4','J5','J6'] as const).map(axis => ({
            id:axis.toLowerCase(), name:`Joint ${axis.slice(1)}`, axis,
            torqueNm:0, ratedTorqueNm:0, positionErrorDeg:0, velocityRadS:0,
            temperatureC:axis==='J3' ? (temp?.actual ?? 0) : 0,
            vibrationRms:axis==='J3' ? (vib?.actual ?? 0) : 0,
            degradationStatus:(axis==='J3' && active ? 'critical' : 'nominal') as 'critical' | 'nominal'
          })),
          joint3Telemetry: {torqueRipplePercent:0,backlashArcmin:0,gearMeshFrequencyHz:0,vibrationAccelerationG:0,motorWindingTempC:0,lubricantDegradationIndex:0,estimatedRemainingCycles:0}
        };
      });
      setArms(mapped);
      if (!incident) {
        setSelectedArmId(mapped[0]?.id || ''); setEvidenceRecords([]); setEvents([]);
        setVisualReport(null); setAdkReport(null); setPlans([]);
        setDataWarning('Live fleet loaded. No active incident. Operational findings are not simulated.');
        return;
      }
      setSelectedArmId(`ARM-${incident.cell_id}`);
      setDataWarning('Backend-connected synthetic telemetry and cached Gemini observations. Unavailable joint measurements show N/A; cell health is a backend overall score.');
      const er = incident.robotics_er_result;
      if (er) setVisualReport({
        modelName:'Gemini Robotics ER 2',modelVersion:er.generated_by||'Cached result',targetJoint:'Pick-and-place operation',incidentId:incident.incident_id,
        inspectionTimestamp:incident.created_at,overallWearAssessment:er.summary||'No visual summary',
        confidenceScore:er.observations?.length ? Math.round(er.observations.reduce((sum,o)=>sum+o.confidence,0)/er.observations.length*100) : 0,thermalDifferentialC:0,opticalWearNotes:'Not assessed by this video. No thermal camera or grease inspection evidence.',
        simulatedCaptureLabel:'Cached operation video; no joint macro imagery',
        observations:(er.observations||[]).map((o,i)=>({id:`V${i+1}`,region:`Video ${o.timestamp_seconds}s`,label:'Robotics ER observation',confidence:o.confidence*100,description:o.observation,coordinates:{x:0,y:0,width:0,height:0},status:'warning' as const}))
      });
      const trace=incident.adk_orchestration?.execution_trace||[];
      const phases:AdkInvestigationReport['steps'][number]['phase'][]=['Prediction Agent','Prevention Agent','Investigation Agent','Recovery Agent','Learning Agent'];
      setAdkReport({
        framework:`Google ADK — ${incident.adk_orchestration?.provenance?.execution_mode||'mode unverified'}`,
        agentName:'GuardianCoordinator (backend trace)',incidentId:incident.incident_id,executionStatus:'completed',
        primaryHypothesis:incident.root_cause?.root_cause?.name||'Undetermined',
        confidence:Math.round((incident.root_cause?.score||0)*100),
        recommendedMitigation:incident.recovery_plan?.reasoning_summary||'Await human approval; no production restart authorized',
        steps:trace.map((s,i)=>({stepNumber:s.step||i+1,phase:phases[Math.min(i,4)],title:s.agent,toolInvoked:s.tool,timestamp:s.timestamp,reasoning:s.action,findings:JSON.stringify(s.output||{}),status:'completed'}))
      });
      setEvents((incident.audit_log||[]).map((e,i)=>({id:e.event_id,incidentId:incident.incident_id,timestamp:e.timestamp,cycleNumber:0,joint:'J3',severity:'info',category:'ADK Agent Action',summary:`${e.event} (${e.source})`})));
      setEvidenceRecords([{id:'BACKEND-EVIDENCE',armId:`ARM-${incident.cell_id}`,incidentId:incident.incident_id,targetJoint:'J3',timestamp:incident.created_at,reportType:'Backend evidence and audit',telemetryFramesCount:incident.evidence?.length||0,adkTraceId:'See API trace',geminiModelVersion:er?.generated_by||'CACHE',fileSizeKb:0,summary:`${incident.evidence?.length||0} backend evidence objects. Root cause ${incident.root_cause?.root_cause?.name||'unconfirmed'}.`}]);
      // One backend-origin proposal card; never invent a separate approval or recovery outcome.
      const actions = incident.recovery_plan?.recommended_actions || [];
      setPlans([{id:`BACKEND-${incident.incident_id}`,targetArmId:`ARM-${incident.cell_id}`,
        incidentId:incident.incident_id,title:'Backend Recovery Proposal',
        description:actions.join(' → ') || 'No recovery actions provided by backend',
        interventionType:'cycle_hold',projectedStressReduction:'Not measured',
        requiresTechnicianSignoff:true,status:'pending_approval',
        simulationNote:'Proposal only. No physical robot execution or backend approval has occurred.',
        checklist:{safety_clear:false,telemetry_logged:false,scheduled_downtime_notified:false}}]);
    } catch(error) {
      setArms([]); setLiveIncident(null); setPlans([]); setEvents([]); setEvidenceRecords([]);
      setVisualReport(null); setAdkReport(null);
      setBackendState(previous => ({...previous,connected:false,error:'Fleet/incident fetch failed'}));
      setDataWarning(`Backend data load failed: ${error instanceof Error?error.message:String(error)}`);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    checkBackend();
  }, [checkBackend]);

  // Navigate to investigate tab with selected arm
  const handleInvestigateArm = (armId: string, targetTab?: InvestigateTab) => {
    setSelectedArmId(armId);
    if (targetTab) {
      setInvestigateTab(targetTab);
    }
    setActiveSection('investigate');
  };

  // Flag note
  const handleSimulateMaintenanceFlag = (armId: string) => {
    setDataWarning(`Maintenance flag for ${armId} requires a backend update; display state has not been modified.`);
  };

  // Backend-managed incidents cannot be approved or executed by local UI state.
  const handleApplySimulatedPlan = (_planId: string, _technician: string, _workOrder: string) => {
    setDataWarning('Recovery execution is blocked until backend authorization is integrated and verified.');
  };

  // Update recovery plan checklist items and preserve across navigation
  const handleUpdatePlanChecklist = (planId: string, key: string, value: boolean) => {
    setPlans(prev => prev.map(p => {
      if (p.id !== planId) return p;
      return {
        ...p,
        checklist: {
          ...(p.checklist || {}),
          [key]: value
        }
      };
    }));
  };

  const selectedArm = arms.find(a => a.id === selectedArmId) || arms[0];
  const selectedIncidentId = liveIncident?.incident_id || 'NO-ACTIVE-INCIDENT';
  const advisoryCount = arms.filter(a => a.status === 'degraded' || a.status === 'maintenance_required').length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Bar with 3-Zone Contract & Approved Logo */}
      <TopBar
        activeSection={activeSection}
        onSelectSection={setActiveSection}
        backendState={backendState}
        onRefreshBackend={checkBackend}
        advisoryCount={advisoryCount}
      />

      {dataWarning && <div className="mx-auto max-w-7xl px-4 lg:px-8 py-2 text-xs font-mono text-amber-300 border-b border-amber-900/40" role="status">{dataWarning}</div>}
      {/* Main Content Area */}
      {loading && <div className="mx-auto max-w-7xl w-full px-4 py-3 text-xs font-mono text-cyan-300" role="status">Loading backend operational data...</div>}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 lg:p-8">
        {!loading && (!backendState.connected || arms.length===0) && <div role="alert" className="rounded-xl border border-amber-800/60 p-8 text-amber-300 bg-slate-900">Backend operational data unavailable. Check FastAPI connectivity and refresh.</div>}
        {!loading && backendState.connected && !liveIncident && activeSection !== 'fleet' && <div role="status" className="rounded-xl border border-slate-800 p-8 text-slate-300 bg-slate-900">No active backend incident. Run a demo scenario to populate this section.</div>}
        {!loading && backendState.connected && arms.length > 0 && activeSection === 'fleet' && (
          <FleetSection
            arms={arms}
            selectedArmId={selectedArmId}
            onSelectArm={setSelectedArmId}
            onInvestigateArm={handleInvestigateArm}
            visualReport={visualReport || emptyVisualReport}
            adkReport={adkReport || emptyAdkReport}
            recoveryPlans={plans}
            liveIncident={liveIncident}
          />
        )}

        {!loading && backendState.connected && liveIncident && activeSection === 'investigate' && visualReport && adkReport && (
          <InvestigateSection
            arms={arms}
            selectedArmId={selectedArmId}
            onSelectArm={setSelectedArmId}
            visualReport={visualReport || emptyVisualReport}
            adkReport={adkReport || emptyAdkReport}
            events={events}
            liveIncident={liveIncident}
            activeTab={investigateTab}
            onSelectTab={setInvestigateTab}
          />
        )}

        {!loading && backendState.connected && liveIncident && plans.length > 0 && activeSection === 'recover' && (
          <RecoverSection
            arms={arms}
            plans={plans}
            backendLinked={!!liveIncident}
            liveIncident={liveIncident}
            selectedArmId={selectedArmId}
            selectedIncidentId={selectedIncidentId}
            onApplySimulatedPlan={handleApplySimulatedPlan}
            onUpdatePlanChecklist={handleUpdatePlanChecklist}
          />
        )}

        {!loading && backendState.connected && liveIncident && activeSection === 'evidence' && (
          <EvidenceSection
            evidenceRecords={evidenceRecords}
            selectedArmId={selectedArmId}
            selectedIncidentId={selectedIncidentId}
            recoveryPlans={plans}
            liveIncident={liveIncident}
          />
        )}
      </main>

      {/* Industrial Footer with Exact Product Identity Strings */}
      <footer className="border-t border-slate-900 bg-slate-950 px-4 lg:px-8 py-4 text-xs font-mono text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <span className="text-white font-bold">RoboIQ Guardian</span>
          <span className="text-slate-700">·</span>
          <span className="text-slate-300">Embodied Intelligence for Robotic Recovery</span>
          <span className="text-slate-700">·</span>
          <span className="text-slate-400 italic">Beyond Detection. Toward Intelligent Recovery.</span>
        </div>

        <div className="text-[11px] text-slate-500">
          Workcell Focus: <strong className="text-cyan-400 font-mono">{selectedArmId}</strong> · Incident: <strong className="text-amber-400 font-mono">{selectedIncidentId}</strong>
        </div>
      </footer>
    </div>
  );
}
