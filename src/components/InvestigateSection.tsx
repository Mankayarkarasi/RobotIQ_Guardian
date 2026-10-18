import type { GuardianIncidentDetail } from '../services/api';
import React, { useState, useEffect } from 'react';
import { fetchTelemetryEpisodes, fetchTelemetryHistory } from '../services/api';
import type { HistoricalEpisode, HistoricalTelemetryHistory } from '../services/api';
import { 
  RoboticArmUnit, 
  VisualIntelligenceReport, 
  AdkInvestigationReport, 
  ArmEventRecord, 
  InvestigateTab 
} from '../types';
import { 
  ShieldAlert, Activity, Eye, Bot, Clock, AlertTriangle, 
  CheckCircle2, Cpu, Thermometer, Layers, ChevronRight, 
  Sliders, Info, Sparkles, Terminal, FileText, BarChart3
} from 'lucide-react';

interface InvestigateSectionProps {
  liveIncident?: GuardianIncidentDetail | null;
  arms: RoboticArmUnit[];
  selectedArmId: string;
  onSelectArm: (armId: string) => void;
  visualReport: VisualIntelligenceReport;
  adkReport: AdkInvestigationReport;
  events: ArmEventRecord[];
  activeTab?: InvestigateTab;
  onSelectTab?: (tab: InvestigateTab) => void;
}

export const InvestigateSection: React.FC<InvestigateSectionProps> = ({
  liveIncident,
  arms,
  selectedArmId,
  onSelectArm,
  visualReport,
  adkReport,
  events,
  activeTab: controlledActiveTab,
  onSelectTab: controlledOnSelectTab
}) => {
  const [internalActiveTab, setInternalActiveTab] = useState<InvestigateTab>('overview');
  const activeTab = controlledActiveTab !== undefined ? controlledActiveTab : internalActiveTab;
  const setActiveTab = (tab: InvestigateTab) => {
    setInternalActiveTab(tab);
    controlledOnSelectTab?.(tab);
  };
  const [selectedRegionId, setSelectedRegionId] = useState<string>('OBS-01');
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [historicalEpisodes, setHistoricalEpisodes] = useState<HistoricalEpisode[]>([]);
  const [historicalSelection, setHistoricalSelection] = useState('');
  const [historicalData, setHistoricalData] = useState<HistoricalTelemetryHistory | null>(null);
  const [historicalError, setHistoricalError] = useState('');
  useEffect(() => {
    if (activeTab !== 'telemetry') return;
    let active = true;
    fetchTelemetryEpisodes().then(result => {
      if (!active) return;
      setHistoricalEpisodes(result.episodes);
      setHistoricalSelection(value => value || result.episodes.find(e => e.scenario_type === 'degrading')?.episode_id || result.episodes[0]?.episode_id || '');
    }).catch(error => { if (active) setHistoricalError(String(error)); });
    return () => { active = false; };
  }, [activeTab]);
  useEffect(() => {
    const episode = historicalEpisodes.find(e => e.episode_id === historicalSelection);
    if (activeTab !== 'telemetry' || !episode) return;
    let active = true;
    setHistoricalData(null); setHistoricalError('');
    fetchTelemetryHistory(episode.robot_id, episode.episode_id).then(result => {if(active) setHistoricalData(result);}).catch(error => {if(active) setHistoricalError(String(error));});
    return () => {active=false;};
  }, [historicalEpisodes, historicalSelection, activeTab]);


  const currentArm = arms.find(a => a.id === selectedArmId) || arms[0];
  const joint3 = currentArm.joints.find(j => j.axis === 'J3');

  const tabs: { id: InvestigateTab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <Layers className="w-3.5 h-3.5" /> },
    { id: 'telemetry', label: 'Telemetry Analysis', icon: <Activity className="w-3.5 h-3.5" /> },
    { id: 'visual_intelligence', label: 'Visual Intelligence', icon: <Eye className="w-3.5 h-3.5" /> },
    { id: 'agentic_investigation', label: 'Agentic Investigation', icon: <Bot className="w-3.5 h-3.5" /> },
    { id: 'events_timeline', label: 'Events Timeline', icon: <Clock className="w-3.5 h-3.5" /> }
  ];

  return (
    <div className="space-y-6">
      {/* Investigation Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-cyan-400">
            <span>TARGET DIAGNOSTICS</span>
            <span className="text-slate-600">·</span>
            <span>BACKEND-LINKED MULTIMODAL INVESTIGATION</span>
            <span className="text-slate-600">·</span>
            <span className="text-amber-400 font-bold">INCIDENT: {currentArm.activeIncidentId || 'NOMINAL-STATE'}</span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white font-mono mt-0.5">
            Robotic Arm Joint-3 Degradation Investigation
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-3xl">
            Multimodal root-cause diagnosis using backend telemetry, Gemini Robotics ER 2 visual understanding, and Google ADK-assisted reasoning.
          </p>
        </div>

        {/* Arm Unit Selector */}
        <div className="flex items-center gap-3 shrink-0">
          <label className="text-xs text-slate-400 font-mono">Workcell Arm:</label>
          <select
            value={selectedArmId}
            onChange={(e) => onSelectArm(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-white text-xs font-mono rounded px-3 py-1.5 focus:outline-none focus:border-cyan-500"
          >
            {arms.map((arm) => (
              <option key={arm.id} value={arm.id}>
                {arm.id} ({arm.status === 'degraded' ? 'Degraded - Joint 3' : 'Nominal'})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Target Unit Status Ribbon */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-4 font-mono text-xs">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-amber-950/80 border border-amber-700 text-amber-300">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2 font-bold text-white">
              <span>{currentArm.id}: {currentArm.name}</span>
              <span className="text-slate-500">[{currentArm.workcell}]</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Active Task: <span className="text-slate-300">{currentArm.application}</span> ({currentArm.activeWorkpiece})
            </div>
          </div>
        </div>

        <div className="flex items-center gap-5 shrink-0 text-[11px]">
          <div>
            <span className="text-slate-500">Cell Health (overall):</span>{' '}
            <span className={`font-bold tabular-nums ${currentArm.joint3HealthScore < 60 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {currentArm.joint3HealthScore}%
            </span>
          </div>
          <span className="text-slate-700">·</span>
          <div>
            <span className="text-slate-500">J3 Vibration:</span>{' '}
            <span className="text-amber-400 font-bold tabular-nums">
              {liveIncident?.telemetry_result?.breached_signals?.find(x=>x.signal==='joint_3_vibration')?.actual ?? 'N/A'} mm/s
            </span>
          </div>
          <span className="text-slate-700">·</span>
          <div>
            <span className="text-slate-500">Motor Current:</span>{' '}
            <span className="text-amber-400 font-bold tabular-nums">
              {liveIncident?.telemetry_result?.breached_signals?.find(x=>x.signal==='motor_current')?.actual ?? 'N/A'} A
            </span>
          </div>
          <span className="text-slate-700">·</span>
          <div>
            <span className="text-slate-500">Temperature:</span>{' '}
            <span className="text-white font-bold tabular-nums">
              {liveIncident?.telemetry_result?.breached_signals?.find(x=>x.signal==='temperature')?.actual ?? 'N/A'}°C
            </span>
          </div>
        </div>
      </div>

      {/* THE FIVE APPROVED INVESTIGATE TABS */}
      <div className="border-b border-slate-800 flex items-center gap-1 overflow-x-auto pb-0.5">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-xs font-mono font-semibold rounded-t transition-colors whitespace-nowrap flex items-center gap-2 border-b-2 ${
              activeTab === tab.id
                ? 'bg-slate-900 text-cyan-400 border-cyan-400'
                : 'text-slate-400 hover:text-slate-200 border-transparent hover:bg-slate-900/40'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          {/* Executive Diagnostic Synopsis */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-5 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <span className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider">
                  Diagnostic Executive Summary
                </span>
                <h2 className="text-base font-bold text-white font-mono mt-0.5">
                  {liveIncident ? (liveIncident.root_cause?.root_cause?.name || 'Mechanical degradation under investigation') : 'Illustrative Harmonic Reducer Diagnosis'}
                </h2>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed max-w-3xl">
                  {liveIncident ? liveIncident.adk_orchestration?.investigation_summary || 'Telemetry and cached Robotics ER visual observations indicate failed pick-and-place. Hardware inspection is required before production resumption.' : 'Illustrative local telemetry investigation.'}
                </p>
              </div>

              <div className="px-3 py-1.5 rounded bg-amber-950/70 border border-amber-700 text-amber-300 font-mono text-xs text-right shrink-0">
                <div className="text-[10px] text-amber-400 uppercase">Degradation Phase</div>
                <div className="font-bold text-sm">{liveIncident ? (liveIncident.severity || 'Severity unverified') : 'Illustrative Stage II'}</div>
              </div>
            </div>

            {/* Tri-Pillar Investigation Highlights */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
              {/* Telemetry Pillar */}
              <div className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
                <div className="flex items-center gap-2 text-xs font-mono font-bold text-white">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  <span>Telemetry Indicators</span>
                </div>
                <ul className="text-xs text-slate-400 space-y-1 font-mono text-[11px]">
                  <li>• Joint-3 vibration: {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='joint_3_vibration')?.actual ?? 'N/A'} mm/s` : 'Illustrative'}</li>
                  <li>• Motor current: {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='motor_current')?.actual ?? 'N/A'} A` : 'Illustrative'}</li>
                  <li>• Temperature: {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='temperature')?.actual ?? 'N/A'}°C` : 'Illustrative'}</li>
                </ul>
              </div>

              {/* Visual Intelligence Pillar */}
              <div className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
                <div className="flex items-center gap-2 text-xs font-mono font-bold text-white">
                  <Eye className="w-4 h-4 text-cyan-400" />
                  <span>Gemini Robotics ER 2</span>
                </div>
                <ul className="text-xs text-slate-400 space-y-1 font-mono text-[11px]">
                  <li>• {liveIncident ? 'Video: empty gripper at 6 seconds' : 'Illustrative visual assessment'}</li>
                  <li>• {liveIncident ? 'Flashing red warning light observed' : 'No live thermal measurement'}</li>
                  <li>• {liveIncident ? 'No joint macro/grease inspection available' : 'No backend visual data'}</li>
                </ul>
              </div>

              {/* Agentic Investigation Pillar */}
              <div className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-lg space-y-2">
                <div className="flex items-center gap-2 text-xs font-mono font-bold text-white">
                  <Bot className="w-4 h-4 text-cyan-400" />
                  <span>Google ADK Reasoning</span>
                </div>
                <ul className="text-xs text-slate-400 space-y-1 font-mono text-[11px]">
                  <li>• {liveIncident ? 'Five threshold breaches correlated' : 'No verified payload analysis'}</li>
                  <li>• Root cause: {liveIncident ? liveIncident.root_cause?.root_cause?.name : 'Not linked'}</li>
                  <li>• {liveIncident ? 'PAUSED; human approval and inspection required' : 'No backend mitigation'}</li>
                </ul>
              </div>
            </div>

            {/* Immediate Action Advisory */}
            <div className="p-3 rounded bg-cyan-950/40 border border-cyan-800/80 text-xs font-mono text-cyan-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-cyan-400 shrink-0" />
                <span>{liveIncident ? 'Backend recovery proposal awaiting human approval — see ' : 'Illustrative mitigation plan under '}<strong>Recover</strong> tab.</span>
              </div>
              <span className="text-[11px] text-slate-400">{liveIncident ? 'Remaining cycles: not established' : 'Illustrative cycle estimate'}</span>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: TELEMETRY ANALYSIS */}
      {activeTab === 'telemetry' && (
        <div className="space-y-4">

          {/* Historical telemetry: real JSONL rows retrieved from FastAPI; not the active incident. */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-xs font-mono font-bold text-white uppercase">Historical Telemetry Trends — Synthetic Dataset</h3>
                <p className="text-[11px] text-slate-400 mt-1">Historical robots RB-001/002/003 are not mapped to live demo robot IDs. Select an episode explicitly.</p>
              </div>
              <select aria-label="Historical telemetry episode" value={historicalSelection} onChange={e=>setHistoricalSelection(e.target.value)} className="bg-slate-950 text-cyan-300 border border-slate-700 rounded px-3 py-2 text-xs font-mono">
                {historicalEpisodes.map(ep=><option key={ep.episode_id} value={ep.episode_id}>{ep.robot_id} · {ep.episode_id} · {ep.scenario_type}</option>)}
              </select>
            </div>
            {historicalError && <p role="alert" className="text-amber-300 text-xs">Historical telemetry unavailable: {historicalError}</p>}
            {!historicalError && !historicalData && <p className="text-slate-400 text-xs">Loading historical telemetry…</p>}
            {historicalData && <>
              <div className="text-[11px] text-slate-400 font-mono">{historicalData.total_matching_records.toLocaleString()} records in episode · {historicalData.returned_records} plotted · 10-second synthetic sampling · independent of live incident</div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                {([['joint_3_vibration_mm_s','Joint-3 vibration','mm/s'],['motor_temperature_c','Motor temperature','°C'],['motor_current_a','Motor current','A'],['position_error_mm','Position error','mm'],['cycle_time_s','Cycle time','s']] as const).map(([key,label,unit]) => {
                  const values = historicalData.records.map(row=>row[key]).filter(Number.isFinite);
                  const min = Math.min(...values), max=Math.max(...values), range=max-min || 1;
                  const coordinates = values.map((value,i)=>`${(i / Math.max(1,values.length-1)*320).toFixed(1)},${(92-(value-min)/range*80).toFixed(1)}`).join(' ');
                  return <div key={key} className="rounded border border-slate-800 bg-slate-950/60 p-3">
                    <div className="flex items-center justify-between gap-2 text-xs font-mono"><span className="text-cyan-300">{label}</span><span className="text-slate-400">{values.length ? `${min.toFixed(2)}–${max.toFixed(2)} ${unit}` : 'N/A'}</span></div>
                    <svg viewBox="0 0 320 100" role="img" aria-label={`${label} historical trend`} className="w-full mt-2" preserveAspectRatio="none">
                      <path d="M0 92 H320" stroke="#334155" fill="none"/>
                      <polyline points={coordinates} stroke="#22d3ee" fill="none" strokeWidth="1.8" vectorEffect="non-scaling-stroke"/>
                    </svg>
                    <div className="flex justify-between text-[10px] text-slate-500 font-mono"><span>{historicalData.records[0]?.timestamp?.slice(0,16)}</span><span>{historicalData.records[historicalData.records.length-1]?.timestamp?.slice(0,16)}</span></div>
                  </div>;
                })}
              </div>
            </>}
          </div>

          {/* Kinematic Chain Joint Comparison */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-mono font-bold text-white uppercase flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-cyan-400" />
                6-Axis Kinematic Load & Thermal Profile ({currentArm.name})
              </h3>
              <span className="text-[11px] font-mono text-slate-400">Workpiece: {liveIncident ? 'N/A — not in backend response' : 'N/A'}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {currentArm.joints.map((joint) => {
                const isJ3 = joint.axis === 'J3';
                const loadPercent = 0; // Joint torque/load was not supplied by the backend

                return (
                  <div
                    key={joint.id}
                    className={`p-3 rounded border font-mono text-xs ${
                      isJ3
                        ? 'bg-amber-950/40 border-amber-600 shadow-[0_0_10px_rgba(245,158,11,0.1)]'
                        : 'bg-slate-950/60 border-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-white flex items-center gap-1.5">
                        <span className={`px-1.5 py-0.2 rounded text-[10px] ${
                          isJ3 ? 'bg-amber-900 text-amber-200' : 'bg-slate-800 text-slate-300'
                        }`}>
                          {joint.axis}
                        </span>
                        <span>{joint.name}</span>
                      </div>
                      <span className={`text-[10px] font-bold uppercase ${
                        isJ3 ? 'text-amber-400' : 'text-emerald-400'
                      }`}>
                        {isJ3 ? (liveIncident?.telemetry_result?.status==='FAILURE' ? 'alert' : 'N/A') : 'N/A'}
                      </span>
                    </div>

                    <div className="mt-2.5 space-y-1.5 text-[11px]">
                      <div className="flex justify-between text-slate-400">
                        <span>Torque:</span>
                        <span className="text-white font-semibold tabular-nums">
                          N/A — no joint torque reading
                        </span>
                      </div>
                      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${isJ3 ? 'bg-amber-400' : 'bg-cyan-400'}`}
                          style={{ width: '0%' }}
                        />
                      </div>

                      <div className="flex justify-between text-slate-400 pt-1 text-[11px]">
                        <span>Temp: <strong className={joint.temperatureC > 50 ? "text-amber-400" : "text-white"}>{isJ3 && liveIncident?.telemetry_result?.breached_signals?.some(x=>x.signal==='temperature') ? `${liveIncident.telemetry_result.breached_signals.find(x=>x.signal==='temperature')?.actual}°C` : 'N/A'}</strong></span>
                        <span>Vibration: <strong className={joint.vibrationRms > 2 ? "text-amber-400" : "text-white"}>{isJ3 && liveIncident?.telemetry_result?.breached_signals?.some(x=>x.signal==='joint_3_vibration') ? `${liveIncident.telemetry_result.breached_signals.find(x=>x.signal==='joint_3_vibration')?.actual} mm/s` : 'N/A'}</strong></span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Joint-3 Deep-Dive Spectral & Backlash Telemetry */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-4 space-y-4">
            <h3 className="text-xs font-mono font-bold text-white uppercase flex items-center gap-2">
              <Activity className="w-4 h-4 text-amber-400" />
              Joint-3 High-Rate Telemetry Breakdown vs Nominal Baseline
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 font-mono text-xs">
              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded">
                <div className="text-[10px] text-slate-500 uppercase">{liveIncident ? 'Position Error' : 'Torque Ripple'}</div>
                <div className="text-lg font-bold text-amber-400 mt-1 tabular-nums">
                  {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='position_error')?.actual ?? 'N/A'} mm` : `$'N/A'`}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">{liveIncident ? 'Alert threshold 0.5 mm' : 'Illustrative baseline'}</div>
              </div>

              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded">
                <div className="text-[10px] text-slate-500 uppercase">{liveIncident ? 'Motor Current' : 'Angular Backlash'}</div>
                <div className="text-lg font-bold text-amber-400 mt-1 tabular-nums">
                  {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='motor_current')?.actual ?? 'N/A'} A` : `$'N/A'`}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">{liveIncident ? 'Alert threshold 8.5 A' : 'Illustrative baseline'}</div>
              </div>

              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded">
                <div className="text-[10px] text-slate-500 uppercase">{liveIncident ? 'Joint-3 Vibration' : 'Gear Mesh Harmonic'}</div>
                <div className="text-lg font-bold text-white mt-1 tabular-nums">
                  {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='joint_3_vibration')?.actual ?? 'N/A'} mm/s` : 'N/A'}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">{liveIncident ? 'Alert threshold 2.5 mm/s' : 'Illustrative 0.68 G acceleration'}</div>
              </div>

              <div className="p-3 bg-slate-950/70 border border-slate-800 rounded">
                <div className="text-[10px] text-slate-500 uppercase">{liveIncident ? 'Temperature' : 'Lubricant Degradation'}</div>
                <div className="text-lg font-bold text-amber-400 mt-1 tabular-nums">
                  {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='temperature')?.actual ?? 'N/A'}°C` : 'N/A'}
                </div>
                <div className="text-[10px] text-slate-400 mt-0.5">{liveIncident ? 'Alert threshold 75°C' : 'Illustrative viscosity threshold'}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: VISUAL INTELLIGENCE (Gemini Robotics ER 2) */}
      {activeTab === 'visual_intelligence' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Visual Feed Simulation with Bounding Boxes */}
          <div className="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Eye className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-mono font-bold text-white uppercase">
                  {visualReport.modelName} Visual Understanding
                </h3>
              </div>
              <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800 px-2 py-0.5 rounded">
                {liveIncident ? 'Mean observation confidence: ' : 'Confidence: '}{visualReport.confidenceScore}%
              </span>
            </div>

            {/* Industrial Camera Viewport */}
            <div className="relative aspect-video w-full bg-slate-950 rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center">
              {/* Graphic Representation of Joint-3 Elbow Housing */}
              <svg className="w-full h-full" viewBox="0 0 600 340">
                <defs>
                  <radialGradient id="jointHeat" cx="45%" cy="40%" r="35%">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.45" />
                    <stop offset="60%" stopColor="#ef4444" stopOpacity="0.15" />
                    <stop offset="100%" stopColor="#0f172a" stopOpacity="0" />
                  </radialGradient>
                </defs>

                {/* Arm Upper Boom Link */}
                <path d="M 120 70 L 260 110 L 250 170 L 100 130 Z" fill="#1e293b" stroke="#334155" strokeWidth="2" />
                
                {/* Joint-3 Elbow Harmonic Drive Housing Cylinder */}
                <rect x="230" y="90" width="160" height="150" rx="16" fill="#0f172a" stroke="#475569" strokeWidth="2" />
                <circle cx="310" cy="165" r="54" fill="#1e293b" stroke="#64748b" strokeWidth="2" />
                
                {/* Harmonic Drive Wave Generator Inner Bearing */}
                <circle cx="310" cy="165" r="32" fill="#090e17" stroke="#0ea5e9" strokeWidth="1.5" strokeDasharray="4 2" />
                <circle cx="310" cy="165" r="14" fill="#38bdf8" fillOpacity="0.8" />

                {/* Thermal Gradient Heatmap Overlay */}
                <circle cx="310" cy="165" r="75" fill="url(#jointHeat)" />

                {/* Forearm Link Outfeed */}
                <path d="M 370 140 L 510 200 L 490 260 L 350 200 Z" fill="#1e293b" stroke="#334155" strokeWidth="2" />

                {/* Diagram only; no video evidence of grease or measured hub temperature */}
                {!liveIncident && <>
                {/* Simulated Oil Weepage Streak */}
                <path d="M 285 200 Q 295 240 305 255" stroke="#f59e0b" strokeWidth="3" strokeLinecap="round" fill="none" opacity="0.85" />
                <circle cx="305" cy="256" r="3" fill="#f59e0b" />

                {/* Bounding Box 1: Seal Weepage */}
                <rect x="260" y="190" width="100" height="75" fill="none" stroke="#f59e0b" strokeWidth="2" strokeDasharray="3 3" />
                <text x="265" y="185" fill="#f59e0b" fontSize="10" fontFamily="monospace">Illustrative diagram — no grease inspection</text>

                {/* Bounding Box 2: Wave Generator Thermal Hub */}
                <rect x="275" y="130" width="70" height="70" fill="none" stroke="#ef4444" strokeWidth="2" strokeDasharray="3 3" />
                <text x="280" y="125" fill="#ef4444" fontSize="10" fontFamily="monospace">No measured thermal hub imagery</text>
                </>}
              </svg>

              {/* Viewport Meta overlay */}
              <div className="absolute top-2 left-2 text-[10px] font-mono text-slate-400 bg-slate-950/80 px-2 py-1 rounded border border-slate-800">
                {visualReport.simulatedCaptureLabel}
              </div>
              <div className="absolute bottom-2 right-2 text-[10px] font-mono text-cyan-400 bg-slate-950/80 px-2 py-1 rounded border border-slate-800">
                Model: {visualReport.modelVersion}
              </div>
            </div>

            {/* Model Assessment Text */}
            <div className="p-3 bg-slate-950/70 border border-slate-800 rounded font-mono text-xs text-slate-300 leading-relaxed">
              <span className="text-cyan-400 font-bold">Gemini Robotics ER 2 Reasoning: </span>
              {visualReport.overallWearAssessment}
            </div>
          </div>

          {/* Observations Breakdown Panel */}
          <div className="space-y-3">
            <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
              Detected Visual Features
            </div>

            <div className="space-y-2">
              {visualReport.observations.map((obs) => (
                <div
                  key={obs.id}
                  onClick={() => setSelectedRegionId(obs.id)}
                  className={`p-3 rounded border font-mono text-xs cursor-pointer transition-all ${
                    selectedRegionId === obs.id
                      ? 'bg-slate-800 border-cyan-500/80 shadow-sm'
                      : 'bg-slate-900/80 border-slate-800 hover:bg-slate-850'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white">{obs.id}</span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded border uppercase font-bold ${
                      obs.status === 'alert'
                        ? 'bg-rose-950/80 border-rose-800 text-rose-300'
                        : obs.status === 'warning'
                        ? 'bg-amber-950/80 border-amber-800 text-amber-300'
                        : 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                    }`}>
                      {obs.status}
                    </span>
                  </div>

                  <div className="font-semibold text-slate-200 mt-1">{obs.label}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{obs.region}</div>
                  <p className="text-[11px] text-slate-400 mt-2 line-clamp-3">{obs.description}</p>

                  <div className="mt-2 text-[10px] text-cyan-400">
                    Detection Confidence: {obs.confidence}%
                  </div>
                </div>
              ))}
            </div>

            <div className="p-3 bg-slate-950/50 border border-slate-800 rounded text-[11px] font-mono text-slate-400">
              <span className="text-slate-300 font-semibold">Optical Note:</span> {visualReport.opticalWearNotes}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: AGENTIC INVESTIGATION (Google ADK) */}
      {activeTab === 'agentic_investigation' && (
        <div className="space-y-4">
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-mono font-bold text-white uppercase">
                    {adkReport.framework}
                  </span>
                </div>
                <div className="text-xs text-slate-400 font-mono mt-0.5">
                  Agent: <span className="text-slate-200 font-semibold">{adkReport.agentName}</span>
                </div>
              </div>

              <div className="px-3 py-1 rounded bg-cyan-950/70 border border-cyan-800 text-cyan-300 font-mono text-xs flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                <span>Synthesis Confidence: {adkReport.confidence}%</span>
              </div>
            </div>

            {/* Synthesized Hypothesis Box */}
            <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-1.5 font-mono text-xs">
              <span className="text-cyan-400 font-bold uppercase text-[11px]">Primary Diagnostic Hypothesis:</span>
              <p className="text-slate-200 leading-relaxed">{adkReport.primaryHypothesis}</p>
            </div>

            {/* Step-by-Step Reasoning Trace */}
            <div className="space-y-2.5">
              <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider">
                Multi-Step Reasoning Trace & Tool Invocation Ledger
              </div>

              {adkReport.steps.map((step) => {
                const isExpanded = expandedStep === step.stepNumber;

                return (
                  <div
                    key={step.stepNumber}
                    className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950/60 font-mono text-xs"
                  >
                    <div
                      onClick={() => setExpandedStep(isExpanded ? null : step.stepNumber)}
                      className="p-3 bg-slate-900/80 hover:bg-slate-850 cursor-pointer flex items-center justify-between transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-5 h-5 rounded-full bg-cyan-950 border border-cyan-700 text-cyan-300 flex items-center justify-center text-[10px] font-bold">
                          {step.stepNumber}
                        </span>
                        <div>
                          <span className="font-bold text-white">{step.phase}: </span>
                          <span className="text-slate-300">{step.title}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 text-[11px] text-slate-400">
                        <span>{step.timestamp}</span>
                        <ChevronRight className={`w-3.5 h-3.5 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                      </div>
                    </div>

                    <div className="p-3.5 space-y-2 border-t border-slate-800/80 text-[11px] text-slate-300">
                      {step.toolInvoked && (
                        <div className="p-2 bg-slate-900 rounded border border-slate-800 text-cyan-300 font-mono flex items-center gap-1.5">
                          <Terminal className="w-3.5 h-3.5 text-slate-500" />
                          <span>Tool: {step.toolInvoked}</span>
                        </div>
                      )}
                      <div>
                        <strong className="text-slate-400">Agent Reasoning: </strong>
                        <span>{step.reasoning}</span>
                      </div>
                      <div className="pt-1 text-slate-200">
                        <strong className="text-cyan-400">Empirical Findings: </strong>
                        <span>{step.findings}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: EVENTS TIMELINE */}
      {activeTab === 'events_timeline' && (
        <div className="bg-slate-900/90 border border-slate-800 rounded-lg p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 className="text-xs font-mono font-bold text-white uppercase flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              Workcell Cycle Chronology (Transmission Assembly Batch)
            </h3>
            <span className="text-[11px] font-mono text-slate-400">
              {events.length} Diagnostic Events Captured
            </span>
          </div>

          <div className="space-y-2.5 font-mono text-xs">
            {events.map((evt) => (
              <div
                key={evt.id}
                className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <span className="text-cyan-400 font-bold shrink-0">{evt.timestamp}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{evt.category}</span>
                      <span className="text-slate-600">·</span>
                      <span className="text-slate-400 text-[11px]">Cycle #{evt.cycleNumber}</span>
                      <span className="text-slate-600">·</span>
                      <span className="text-amber-400 text-[11px] font-bold">{evt.joint}</span>
                    </div>
                    <p className="text-slate-300 text-[11px] mt-0.5">{evt.summary}</p>
                  </div>
                </div>

                {evt.metricValue && (
                  <span className="text-[11px] bg-slate-900 px-2.5 py-1 rounded border border-slate-800 text-slate-300 shrink-0 self-start sm:self-auto">
                    {evt.metricValue}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
