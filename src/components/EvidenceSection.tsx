import type { GuardianIncidentDetail } from '../services/api';
import React, { useState } from 'react';
import { PocEvidenceRecord, SimulatedRecoveryPlan } from '../types';
import { 
  FileText, Download, CheckCircle2, ShieldCheck, 
  Layers, Copy, Check, Info, FileCode, ChevronDown, ChevronUp, AlertTriangle, Clock, XCircle
} from 'lucide-react';

interface EvidenceSectionProps {
  liveIncident?: GuardianIncidentDetail | null;
  evidenceRecords: PocEvidenceRecord[];
  selectedArmId: string;
  selectedIncidentId: string;
  recoveryPlans?: SimulatedRecoveryPlan[];
}

export const EvidenceSection: React.FC<EvidenceSectionProps> = ({
  liveIncident,
  evidenceRecords,
  selectedArmId,
  selectedIncidentId,
  recoveryPlans = []
}) => {
  const [downloadSuccessId, setDownloadSuccessId] = useState<string | null>(null);
  const [expandedRecordId, setExpandedRecordId] = useState<string | null>('BACKEND-EVIDENCE'); // Default expand EVD-301 for immediate PoC visibility

  const toggleExpand = (recordId: string) => {
    setExpandedRecordId(prev => prev === recordId ? null : recordId);
  };

  const handleExportEvidence = (record: PocEvidenceRecord) => {
    const isBackendEvidence = record.id === 'BACKEND-EVIDENCE' && liveIncident?.incident_id === record.incidentId;
    const bundlePayload = isBackendEvidence && liveIncident ? {
      evidencePackageId: record.id, incidentId: record.incidentId,
      targetRoboticArm: record.armId, jointAxis: record.targetJoint,
      timestampUtc: record.timestamp, evidenceRecordCount: liveIncident.evidence?.length ?? 0,
      dataSourceProvenance: {
        telemetry: 'Backend synthetic incident telemetry',
        visualAnalysis: liveIncident.robotics_er_result?.cache_status === 'CACHE_HIT' ? 'Cached Gemini Robotics ER 2' : 'Backend visual observations',
        orchestrationMode: liveIncident.adk_orchestration?.provenance?.execution_mode || 'unverified',
        runnerNote: liveIncident.adk_orchestration?.provenance?.runner_note || null
      },
      telemetry_result: liveIncident.telemetry_result,
      robotics_er_result: liveIncident.robotics_er_result,
      evidence: liveIncident.evidence,
      hypothesis_ranking: liveIncident.hypothesis_ranking,
      root_cause: liveIncident.root_cause,
      adk_orchestration: liveIncident.adk_orchestration,
      recovery_plan: liveIncident.recovery_plan,
      recovery_prediction: liveIncident.recovery_prediction,
      recommendation: liveIncident.recommendation,
      production_state: liveIncident.production_state,
      analysis_status: liveIncident.analysis_status,
      state_history: liveIncident.state_history,
      audit_log: liveIncident.audit_log,
      exportTimestamp: new Date().toISOString()
    } : { evidencePackageId: record.id, incidentId: record.incidentId, summary: record.summary, source: 'Illustrative local UI package', exportTimestamp: new Date().toISOString() };

    const blob = new Blob([JSON.stringify(bundlePayload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `RoboIQ_Evidence_${record.armId}_${record.incidentId}_${record.id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setDownloadSuccessId(record.id);
    setTimeout(() => setDownloadSuccessId(null), 2500);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
          <span>DIAGNOSTIC EVIDENCE REPOSITORY</span>
          <span className="text-slate-600">·</span>
          <span>MULTIMODAL INVESTIGATION AUDIT</span>
          <span className="text-slate-600">·</span>
          <span className="text-slate-400">[Cached Model Artifacts & Synthetic Telemetry]</span>
        </div>
        <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white font-mono mt-0.5">
          Diagnostic Evidence & Investigation Archives
        </h1>
        <p className="text-xs text-slate-400 mt-1 max-w-3xl">
          Captured high-rate joint telemetry snapshots, Gemini Robotics ER 2 visual feature logs, and Google ADK diagnostic reasoning records for engineering analysis. Click any evidence package to inspect detailed audit summaries.
        </p>
      </div>

      {/* Scope Disclaimer Card */}
      <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono text-slate-300">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>
            <strong className="text-cyan-400">Selected Workcell:</strong> {selectedArmId} · Active Incident: <strong className="text-amber-400">{selectedIncidentId}</strong>.
          </span>
        </div>
        <span className="text-[11px] text-slate-400">
          Provenance: <span className="text-slate-300 font-semibold">{liveIncident ? "Backend telemetry + cached Gemini Robotics ER 2" : "Illustrative local artifacts"}</span>
        </span>
      </div>

      {/* Evidence Packages Grid */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            Investigation Telemetry Packages
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            {evidenceRecords.length} Bundles Ready for Export (Click package to expand audit details)
          </span>
        </div>

        <div className="divide-y divide-slate-800/80">
          {evidenceRecords.map((record) => {
            const isTargetMatch = record.armId === selectedArmId;
            const isExpanded = expandedRecordId === record.id;

            // Find matching recovery plan if any
            const matchingPlan = recoveryPlans.find(p => p.incidentId === record.incidentId);
            const planStatus = matchingPlan?.status || 'pending_approval';
            const isApproved = planStatus === 'simulation_applied';
            const isLiveBackend = record.id === 'BACKEND-EVIDENCE' && liveIncident?.incident_id === record.incidentId;

            return (
              <div 
                key={record.id} 
                className={`transition-colors ${
                  isTargetMatch ? 'bg-slate-900/90' : 'bg-slate-950/40'
                }`}
              >
                {/* Main Package Row - Clickable to expand */}
                <div 
                  onClick={() => toggleExpand(record.id)}
                  className={`p-4 cursor-pointer hover:bg-slate-850/60 flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-l-2 ${
                    isExpanded ? 'border-l-cyan-400 bg-slate-900/95' : isTargetMatch ? 'border-l-cyan-500/60' : 'border-l-transparent'
                  }`}
                >
                  <div className="space-y-1 font-mono text-xs">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-cyan-400 flex items-center gap-1.5">
                        {record.id}
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5 text-cyan-400" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-400" />}
                      </span>
                      <span className="text-slate-700">·</span>
                      <span className="text-amber-300 font-bold">Incident: {record.incidentId}</span>
                      <span className="text-slate-700">·</span>
                      <span className="text-white font-bold">{record.reportType}</span>
                      <span className="text-slate-700">·</span>
                      <span className="text-slate-400">{record.armId}</span>
                    </div>

                    <p className="text-slate-300 text-[11px] max-w-3xl mt-1 leading-relaxed">
                      {record.summary}
                    </p>

                    <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500 pt-1">
                      <span>Target: <strong className="text-slate-300">{record.targetJoint}</strong></span>
                      <span>·</span>
                      <span>ADK Trace: <strong className="text-slate-300">{record.adkTraceId}</strong></span>
                      <span>·</span>
                      <span>{record.id === 'BACKEND-EVIDENCE' ? 'Evidence records' : 'Frames'}: <strong className="text-slate-300">{record.telemetryFramesCount.toLocaleString()}</strong></span>
                      <span>·</span>
                      <span>Vision: <strong className="text-slate-300">{record.geminiModelVersion}</strong></span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0" onClick={e => e.stopPropagation()}>
                    <button
                      onClick={() => handleExportEvidence(record)}
                      className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white border border-slate-700 rounded font-mono text-xs flex items-center gap-2 transition-colors"
                    >
                      {downloadSuccessId === record.id ? (
                        <>
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Package Exported!</span>
                        </>
                      ) : (
                        <>
                          <Download className="w-3.5 h-3.5" />
                          <span>Export Evidence JSON</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Expandable Evidence Summary Panel */}
                {isExpanded && (
                  <div className="bg-slate-950/90 border-t border-b border-slate-800 p-4 lg:p-6 space-y-4 font-mono text-xs animate-fadeIn">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                      <div className="text-cyan-400 font-bold flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-cyan-400" />
                        Multimodal Evidence Summary & Audit Trace — {record.id}
                      </div>
                      <span className="text-[11px] text-slate-400">Timestamp: {record.timestamp}</span>
                    </div>

                    {/* Compact Status Row */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-slate-900/90 rounded border border-slate-800 text-[11px]">
                      <div className="flex items-center justify-between sm:justify-start gap-2">
                        <span className="text-slate-400">Human Approval:</span>
                        {isLiveBackend ? (
                          <span className="px-2 py-0.5 bg-amber-950/60 text-amber-300 border border-amber-800/60 rounded flex items-center gap-1">
                            <Clock className="w-3 h-3 text-amber-400" /> {liveIncident?.recommendation === 'AWAITING_HUMAN_APPROVAL' ? 'Pending — Human Authorization Required' : (liveIncident?.recommendation || 'Backend authorization status unavailable')}
                          </span>
                        ) : isApproved ? (
                          <span className="px-2 py-0.5 bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 rounded flex items-center gap-1 font-bold">
                            <Check className="w-3 h-3 text-emerald-400" /> Approved
                          </span>
                        ) : record.id === 'EVD-301' ? (
                          <span className="px-2 py-0.5 bg-amber-950/60 text-amber-300 border border-amber-800/60 rounded flex items-center gap-1">
                            <Clock className="w-3 h-3 text-amber-400" /> Pending Approval
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded">
                            Not Applicable (Baseline)
                          </span>
                        )}
                      </div>

                      <div className="flex items-center justify-between sm:justify-start gap-2">
                        <span className="text-slate-400">Recovery Simulation:</span>
                        {isLiveBackend ? (
                          <span className="px-2 py-0.5 bg-slate-800 text-amber-300 rounded">Not executed — backend approval required</span>
                        ) : record.id === 'EVD-301' ? (
                          <span className="px-2 py-0.5 bg-cyan-950/60 text-cyan-300 border border-cyan-800/60 rounded font-bold">
                            Available (Ready)
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-slate-800 text-slate-400 rounded">
                            Not Available — Pending Integration
                          </span>
                        )}
                      </div>

                      <div className="flex items-center justify-between sm:justify-start gap-2">
                        <span className="text-slate-400">Recovery Verification:</span>
                        {isLiveBackend ? (
                          <span className="px-2 py-0.5 bg-slate-800 text-amber-300 rounded">Pending — production paused</span>
                        ) : record.id === 'EVD-301' ? (
                          <span className="px-2 py-0.5 bg-slate-800 text-slate-300 border border-slate-700 rounded">
                            Pending Simulation Execution
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 bg-slate-800 text-slate-400 rounded">
                            Not Available — Pending Integration
                          </span>
                        )}
                      </div>
                    </div>

                    {/* 5 Categories Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      {/* 1. Telemetry Evidence */}
                      <div className="p-3 bg-slate-900 rounded border border-slate-800 space-y-1">
                        <div className="font-bold text-slate-200 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                          1. Telemetry Evidence
                        </div>
                        <p className="text-slate-300 text-[11px] leading-relaxed">
                          {isLiveBackend ? (
                            <>Five backend telemetry threshold breaches: {liveIncident?.telemetry_result?.breached_signals?.map(x => `${x.signal}: ${x.actual} (threshold ${x.threshold})`).join('; ') || 'No telemetry measurements available'}. Values are from the synthetic incident input; torque ripple and backlash were not measured.</>
                          ) : record.id === 'EVD-301' ? (
                            <>High-frequency 20Hz sensor stream captured torque ripple anomaly of <strong className="text-amber-300">16.8%</strong> (baseline &lt; 4.0%), backlash expansion to <strong className="text-amber-300">3.4 arcmin</strong>, and winding temperature rise to <strong className="text-amber-300">64.8°C</strong> on Joint-3.</>
                          ) : (
                            <>Nominal shift baseline telemetry recorded stable torque ripple (3.2%), minimal backlash (0.8 arcmin), and normal thermal equilibrium (42.0°C).</>
                          )}
                        </p>
                      </div>

                      {/* 2. Visual Intelligence */}
                      <div className="p-3 bg-slate-900 rounded border border-slate-800 space-y-1">
                        <div className="font-bold text-slate-200 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                          2. Visual Intelligence
                        </div>
                        <p className="text-slate-300 text-[11px] leading-relaxed">
                          {record.id === 'BACKEND-EVIDENCE' && liveIncident ? (<>{liveIncident.robotics_er_result?.summary || 'No visual summary'} (cached result: {liveIncident.robotics_er_result?.cache_status || 'unknown'}).</>) : record.id === 'EVD-301' ? (
                            <><strong className="text-cyan-300">Gemini Robotics ER 2</strong> ({record.geminiModelVersion}) detected grease weepage and dark particulate staining along lower labyrinth rim, with thermal concentration ring at 64.8°C (+18.2°C thermal delta). Confidence: 94.6%.</>
                          ) : (
                            <><strong className="text-cyan-300">Gemini Robotics ER 2</strong> confirmed nominal seal integrity, zero grease weeping, and uniform thermal distribution across Joint-3 casing.</>
                          )}
                        </p>
                      </div>

                      {/* 3. Agent Investigation */}
                      <div className="p-3 bg-slate-900 rounded border border-slate-800 space-y-1">
                        <div className="font-bold text-slate-200 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                          3. Agent Investigation
                        </div>
                        <p className="text-slate-300 text-[11px] leading-relaxed">
                          {record.id === 'BACKEND-EVIDENCE' && liveIncident ? (<>Execution mode: {liveIncident.adk_orchestration?.provenance?.execution_mode || 'unverified'}. Root cause: {liveIncident.root_cause?.root_cause?.name || 'unconfirmed'}. Five-agent backend trace is included in the JSON export.</>) : record.id === 'EVD-301' ? (
                            <><strong className="text-cyan-300">Google ADK Reasoning Trace</strong> ({record.adkTraceId}): Completed 5-step analysis ruling out external payload overload and isolating mechanical wave generator bearing fatigue. Confidence: 94.2%.</>
                          ) : (
                            <><strong className="text-cyan-300">Google ADK Reasoning Trace</strong> ({record.adkTraceId}): Shift A verification trace completed with zero anomalies or kinematic exceptions.</>
                          )}
                        </p>
                      </div>

                      {/* 4. Human Approval */}
                      <div className="p-3 bg-slate-900 rounded border border-slate-800 space-y-1">
                        <div className="font-bold text-slate-200 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                          4. Human Approval
                        </div>
                        <p className="text-slate-300 text-[11px] leading-relaxed">
                          {record.id === 'BACKEND-EVIDENCE' && liveIncident ? (<>Backend status: {liveIncident.recommendation || 'awaiting operator decision'}. Frontend approval is not authoritative.</>) : isApproved ? (
                            <><strong className="text-emerald-300">Approved</strong> by Authorized Lead Technician with work order reference logged. Ready for simulation execution.</>
                          ) : record.id === 'EVD-301' ? (
                            <>Pending human approval decision via Recover stage. Pre-simulation safety verification checklist active.</>
                          ) : (
                            <span className="text-slate-400">Not Available — Pending Integration</span>
                          )}
                        </p>
                      </div>

                      {/* 5. Recovery Verification */}
                      <div className="p-3 bg-slate-900 rounded border border-slate-800 space-y-1 md:col-span-2">
                        <div className="font-bold text-slate-200 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                          5. Recovery Verification
                        </div>
                        <p className="text-slate-300 text-[11px] leading-relaxed">
                          {record.id === 'BACKEND-EVIDENCE' && liveIncident ? (<>Verification pending. Residual risk: {liveIncident.recovery_prediction?.residual_risk || 'not provided'}. Success score: {liveIncident.recovery_prediction?.recovery_success_score ?? 'N/A'} (not calibrated). No production resumption authorized.</>) : record.id === 'EVD-301' ? (
                            <>Projected mitigation profile available: Capping Joint-3 acceleration to 60% and feed rate to 70% reduces contact stress by 38.5%. Post-simulation verification results pending simulation execution.</>
                          ) : (
                            <span className="text-slate-400">Not Available — Pending Integration</span>
                          )}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
