import type { GuardianIncidentDetail } from '../services/api';
import React, { useState, useMemo } from 'react';
import { RoboticArmUnit, VisualIntelligenceReport, AdkInvestigationReport, InvestigateTab, SimulatedRecoveryPlan } from '../types';
import { 
  Search, AlertTriangle, CheckCircle2, ChevronRight, 
  Activity, Thermometer, Gauge, Clock, Eye, Bot, 
  Cpu, Sparkles, Sliders, ArrowUpRight, ShieldCheck, Check,
  CornerDownRight, Zap, RefreshCw
} from 'lucide-react';
import armCellPhoto from '../assets/images/robotic_arm_cell_1792255228722.jpeg';

interface FleetSectionProps {
  liveIncident?: GuardianIncidentDetail | null;
  arms: RoboticArmUnit[];
  selectedArmId: string;
  onSelectArm: (armId: string) => void;
  onInvestigateArm: (armId: string, targetTab?: InvestigateTab) => void;
  visualReport: VisualIntelligenceReport;
  adkReport: AdkInvestigationReport;
  recoveryPlans?: SimulatedRecoveryPlan[];
}

export const FleetSection: React.FC<FleetSectionProps> = ({
  liveIncident,
  arms,
  selectedArmId,
  onSelectArm,
  onInvestigateArm,
  visualReport,
  adkReport,
  recoveryPlans = []
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'nominal' | 'degraded'>('all');
  const [lineFilter, setLineFilter] = useState<string>('all');
  const [showAllIssues, setShowAllIssues] = useState<boolean>(false);

  // 1. Simplified Fleet Health Summary - Exactly 4 dynamic KPI cards
  const totalCells = arms.length;
  const healthyCount = arms.filter(a => a.status === 'nominal').length;
  const needsAttentionCount = arms.filter(a => a.status !== 'nominal' || a.activeIncidentId).length;
  const avgCellHealth = Math.round(arms.reduce((acc, a) => acc + a.joint3HealthScore, 0) / (totalCells || 1));

  // Derive Attention Required active issues from real data & state machine
  const activeIssues = useMemo(() => {
    const issues = [];
    for (const arm of arms) {
      if (arm.status !== 'nominal' || arm.activeIncidentId) {
        const plan = recoveryPlans.find(p => p.targetArmId === arm.id);
        
        let workflowStatus = 'Pending Human Approval (backend validation required)';
        let statusBadgeColor = 'bg-amber-950/80 border-amber-600/80 text-amber-300';

        if (plan?.status === 'simulation_applied') {
          workflowStatus = 'Simulated Mitigation Applied (Derated 70%)';
          statusBadgeColor = 'bg-emerald-950/80 border-emerald-600/80 text-emerald-300';
        } else if (plan?.status === 'simulating') {
          workflowStatus = 'Kinematic Simulation In Progress';
          statusBadgeColor = 'bg-cyan-950/80 border-cyan-600/80 text-cyan-300';
        }

        const nextAction = liveIncident?.cell_id === arm.workcell
          ? (liveIncident.recovery_plan?.reasoning_summary || 'No backend recommendation provided')
          : 'Backend recommendation not available';

        issues.push({
          incidentId: arm.activeIncidentId || 'No active incident',
          robotId: arm.id,
          workcell: arm.workcell,
          description: liveIncident?.cell_id === arm.workcell
            ? (liveIncident.root_cause?.root_cause?.name || 'Backend-detected failure')
            : 'Backend workcell advisory (details unavailable)',
          severity: 'High-priority advisory',
          workflowStatus,
          statusBadgeColor,
          nextAction,
          timestamp: arm.lastInspectionTimestamp,
          healthScore: arm.joint3HealthScore
        });
      }
    }
    return issues;
  }, [arms, recoveryPlans, adkReport]);

  const displayedIssues = showAllIssues ? activeIssues : activeIssues.slice(0, 3);

  // Filtered fleet table list
  const filteredArms = useMemo(() => {
    return arms.filter(arm => {
      const matchesSearch = 
        arm.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        arm.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        arm.workcell.toLowerCase().includes(searchQuery.toLowerCase()) ||
        arm.line.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus = 
        statusFilter === 'all' ? true :
        statusFilter === 'nominal' ? arm.status === 'nominal' :
        arm.status === 'degraded' || arm.status === 'maintenance_required';

      const matchesLine = 
        lineFilter === 'all' ? true : arm.line.includes(lineFilter);

      return matchesSearch && matchesStatus && matchesLine;
    });
  }, [arms, searchQuery, statusFilter, lineFilter]);

  const selectedArm = arms.find(a => a.id === selectedArmId) || arms[0];
  const isSelectedDegraded = selectedArm.status === 'degraded' || selectedArm.status === 'maintenance_required';
  const joint3 = selectedArm.joints.find(j => j.axis === 'J3');
  const selectedArmPlan = recoveryPlans.find(p => p.targetArmId === selectedArm.id);

  return (
    <div className="space-y-6">
      {/* 1. SIMPLIFIED FLEET HEALTH SUMMARY - Exactly 4 KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Card 1: Total Workcells */}
        <div className="bg-gradient-to-b from-slate-900/90 to-slate-950/90 border border-slate-800/80 rounded-xl p-4 shadow-sm hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="font-medium text-slate-400">Total Workcells</span>
            <Cpu className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 font-mono tabular-nums">
            {totalCells}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">6-Axis Articulated Robots</div>
        </div>

        {/* Card 2: Healthy Workcells */}
        <div className="bg-gradient-to-b from-slate-900/90 to-slate-950/90 border border-slate-800/80 rounded-xl p-4 shadow-sm hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="font-medium text-slate-400">Healthy Workcells</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 mt-2 font-mono tabular-nums">
            {healthyCount}
          </div>
          <div className="text-[11px] text-emerald-500/80 mt-1">Backend Workcell Status</div>
        </div>

        {/* Card 3: Needs Attention */}
        <div className={`bg-gradient-to-b from-slate-900/90 to-slate-950/90 rounded-xl p-4 shadow-sm transition-colors ${
          needsAttentionCount > 0 
            ? 'border border-amber-500/50 shadow-[0_0_12px_rgba(245,158,11,0.1)]' 
            : 'border border-slate-800/80'
        }`}>
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="font-medium text-amber-300">Needs Attention</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-2 font-mono tabular-nums">
            {needsAttentionCount}
          </div>
          <div className="text-[11px] text-amber-400/80 mt-1">Joint-3 advisory (backend-linked when available)</div>
        </div>

        {/* Card 4: Fleet Health Index */}
        <div className="bg-gradient-to-b from-slate-900/90 to-slate-950/90 border border-slate-800/80 rounded-xl p-4 shadow-sm hover:border-slate-700 transition-colors">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="font-medium text-slate-400">Fleet Health Index</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-cyan-400 mt-2 font-mono tabular-nums">
            {avgCellHealth}%
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Fleet Mean Kinematic Score</div>
        </div>
      </div>

      {/* 2. ATTENTION REQUIRED - Compact Section Below KPI Cards */}
      {activeIssues.length > 0 && (
        <div className="bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-amber-500/30 rounded-xl p-4 lg:p-5 shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
              </span>
              <h2 className="text-sm font-bold text-white tracking-wider uppercase font-mono">
                Attention Required
              </h2>
              <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded-full bg-amber-950/70 text-amber-300 border border-amber-700/60">
                {activeIssues.length} Active {activeIssues.length === 1 ? 'Anomaly' : 'Anomalies'}
              </span>
            </div>
            <span className="text-xs text-slate-400 font-sans">
              Prioritized manufacturing advisories requiring operator evaluation &amp; human signoff
            </span>
          </div>

          <div className="space-y-3">
            {displayedIssues.map((issue) => (
              <div
                key={`${issue.robotId}-${issue.incidentId}`}
                onClick={() => {
                  onSelectArm(issue.robotId);
                  onInvestigateArm(issue.robotId);
                }}
                className="bg-slate-950/80 border border-slate-800/90 hover:border-amber-500/60 rounded-lg p-3.5 transition-all cursor-pointer group flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                {/* Left: Identifiers & Description */}
                <div className="space-y-1.5 flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
                    <span className="font-bold text-white px-2 py-0.5 rounded bg-slate-900 border border-slate-700 group-hover:border-cyan-500/60 transition-colors">
                      {issue.robotId}
                    </span>
                    <span className="text-cyan-400 font-bold px-2 py-0.5 rounded bg-cyan-950/50 border border-cyan-800/60">
                      {issue.incidentId}
                    </span>
                    <span className="text-slate-500">·</span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-950/80 text-amber-300 border border-amber-700/80">
                      {issue.severity}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${issue.statusBadgeColor}`}>
                      {issue.workflowStatus}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 font-sans font-medium">
                    {issue.description}
                  </p>

                  <div className="flex items-center gap-1.5 text-xs text-slate-400 font-sans">
                    <span className="text-cyan-400 font-mono font-semibold">Recommended Next Action:</span>
                    <span className="text-slate-300">{issue.nextAction}</span>
                  </div>
                </div>

                {/* Right: Review Incident CTA */}
                <div className="shrink-0 flex items-center gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectArm(issue.robotId);
                      onInvestigateArm(issue.robotId);
                    }}
                    className="px-3.5 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 shadow-md shadow-cyan-500/20 font-mono"
                  >
                    <span>Review Incident</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {activeIssues.length > 3 && (
            <div className="text-center pt-1">
              <button
                onClick={() => setShowAllIssues(!showAllIssues)}
                className="text-xs font-mono text-cyan-400 hover:text-cyan-300 underline underline-offset-4"
              >
                {showAllIssues ? 'Show Less' : `View All ${activeIssues.length} Issues`}
              </button>
            </div>
          )}
        </div>
      )}

      {/* 2. ENTERPRISE FLEET OVERVIEW TABLE */}
      <div className="bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/80 rounded-xl overflow-hidden shadow-sm">
        {/* Table Controls Header */}
        <div className="p-4 lg:p-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white tracking-wider uppercase font-mono">
                Fleet Overview
              </h2>
              <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/50 border border-cyan-800/60 px-2 py-0.5 rounded-full">
                {filteredArms.length} Workcells Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Live joint kinematic tracking, line assignments, and anomaly triage. Select any cell to focus workspace.
            </p>
          </div>

          {/* Search & Filters */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search robot ID, workcell, production line..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-64 transition-colors"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Statuses</option>
              <option value="nominal">Nominal</option>
              <option value="degraded">Degradation Advisory</option>
            </select>

            {/* Line Filter */}
            <select
              value={lineFilter}
              onChange={(e) => setLineFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Lines</option>
              <option value="Line A">Line A (Machining/Weld)</option>
              <option value="Line B">Line B (Powertrain)</option>
              <option value="Line C">Line C (Logistics)</option>
            </select>
          </div>
        </div>

        {/* Compact Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800/80 bg-slate-950/70 text-slate-400 font-semibold uppercase text-[11px]">
                <th className="py-3 px-4">Robot / Cell</th>
                <th className="py-3 px-4">Production Line</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Cell Health</th>
                <th className="py-3 px-4">Last Incident</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredArms.map((arm) => {
                const isArmDegraded = arm.status === 'degraded' || arm.status === 'maintenance_required';
                const isArmSelected = arm.id === selectedArmId;

                return (
                  <tr
                    key={arm.id}
                    onClick={() => onSelectArm(arm.id)}
                    className={`cursor-pointer transition-colors ${
                      isArmSelected
                        ? 'bg-slate-800/80 border-l-2 border-l-cyan-400'
                        : 'hover:bg-slate-900/60'
                    }`}
                  >
                    {/* Robot / Cell */}
                    <td className="py-3 px-4">
                      <div className="font-bold text-white flex items-center gap-2">
                        <span>{arm.id}</span>
                        <span className="text-slate-500 font-normal">· {arm.name.split(' ')[0]} {arm.name.split(' ')[1]}</span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-sans mt-0.5 line-clamp-1">
                        {arm.workcell}
                      </div>
                    </td>

                    {/* Production Line */}
                    <td className="py-3 px-4 text-slate-300 font-sans">
                      {arm.line}
                    </td>

                    {/* Status */}
                    <td className="py-3 px-4">
                      {isArmDegraded ? (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold bg-amber-950/80 text-amber-300 border border-amber-700/80">
                          <AlertTriangle className="w-3 h-3 text-amber-400" />
                          Degradation Advisory
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-950/50 text-emerald-300 border border-emerald-800/50">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                          Nominal
                        </span>
                      )}
                    </td>

                    {/* Cell Health */}
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${arm.joint3HealthScore < 60 ? 'bg-amber-400' : 'bg-emerald-400'}`}
                            style={{ width: `${arm.joint3HealthScore}%` }}
                          />
                        </div>
                        <span className={`font-bold tabular-nums ${arm.joint3HealthScore < 60 ? 'text-amber-400' : 'text-slate-200'}`}>
                          {arm.joint3HealthScore}%
                        </span>
                      </div>
                    </td>

                    {/* Last Incident */}
                    <td className="py-3 px-4 font-sans text-xs">
                      {isArmDegraded ? (
                        <span className="text-amber-300 font-mono text-[11px]">{arm.activeIncidentId || 'Incident not provided'}</span>
                      ) : (
                        <span className="text-slate-500 font-mono text-[11px]">None (Nominal)</span>
                      )}
                    </td>

                    {/* Action */}
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectArm(arm.id);
                        }}
                        className={`px-2.5 py-1 text-xs rounded transition-all font-mono ${
                          isArmSelected
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/60 font-semibold shadow-sm'
                            : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'
                        }`}
                      >
                        {isArmSelected ? 'Selected' : 'Select'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. SELECTED ROBOT CONTEXTUAL WORKSPACE (Three Coordinated Panels) */}
      <div className="space-y-4">
        {/* Workspace Title Ribbon */}
        <div className="flex items-center justify-between pb-1">
          <div className="flex items-center gap-2.5 font-mono">
            <span className="text-lg font-bold text-white tracking-tight">
              {selectedArm.id} · {selectedArm.name}
            </span>
            <span className="text-slate-600">·</span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${
              isSelectedDegraded 
                ? 'bg-amber-950/80 border-amber-700 text-amber-300' 
                : 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
            }`}>
              {isSelectedDegraded ? 'Joint-3 Mechanical Degradation' : 'Normal Operational Context'}
            </span>
          </div>

          <span className="text-xs text-slate-400 font-mono hidden sm:inline">
            Active Workpiece: <strong className="text-slate-200">{selectedArm.activeWorkpiece}</strong>
          </span>
        </div>

        {/* The 3 Coordinated Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* PANEL 1: LEFT — ROBOT / CELL VIEW */}
          <div className="bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/80 rounded-xl overflow-hidden flex flex-col justify-between">
            <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-mono text-cyan-400 uppercase tracking-wider block">
                  Workcell View
                </span>
                <h3 className="text-sm font-bold text-white font-mono mt-0.5">
                  {selectedArm.id} · {selectedArm.workcell}
                </h3>
              </div>
              <span className="text-[10px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                Line B
              </span>
            </div>

            {/* Industrial Robotic Arm Visual with Anomaly Marker */}
            <div className="relative aspect-[4/3] w-full bg-slate-950 overflow-hidden">
              <img
                src={armCellPhoto}
                alt={`${selectedArm.name} Workcell`}
                className="w-full h-full object-cover brightness-95 contrast-105"
              />

              {/* Restrained Joint-3 Anomaly Marker */}
              {isSelectedDegraded && (
                <div className="absolute top-[38%] left-[48%] flex flex-col items-center">
                  <div className="relative flex items-center justify-center">
                    <span className="absolute w-8 h-8 rounded-full bg-amber-400/30 animate-ping" />
                    <span className="w-4 h-4 rounded-full bg-amber-500 border-2 border-white shadow-[0_0_10px_rgba(245,158,11,0.9)]" />
                  </div>
                  <div className="mt-1.5 px-2 py-0.5 rounded bg-slate-950/90 border border-amber-500/80 text-[10px] font-mono text-amber-300 font-bold tracking-tight shadow-md">
                    Joint-3 Advisory (illustrative image)
                  </div>
                </div>
              )}

              {/* Source attribution stamp */}
              <div className="absolute bottom-2 left-2 text-[10px] font-mono text-slate-400 bg-slate-950/80 px-2 py-0.5 rounded border border-slate-800 backdrop-blur-sm">
                Illustrative Workcell Image ({selectedArm.id})
              </div>
            </div>

            {/* Cell Metadata Strip */}
            <div className="p-3.5 bg-slate-950/70 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-xs font-mono">
              <div>
                <span className="text-slate-500 text-[11px] block">Model:</span>
                <span className="text-slate-200 truncate block">{liveIncident ? 'Not provided' : selectedArm.model}</span>
              </div>
              <div>
                <span className="text-slate-500 text-[11px] block">Rated Payload:</span>
                <span className="text-slate-200 block">{liveIncident ? 'Not provided' : `${selectedArm.payloadKg} / ${selectedArm.maxPayloadKg} kg`}</span>
              </div>
            </div>
          </div>

          {/* PANEL 2: CENTER — CURRENT ANOMALY TRIAGE */}
          <div className="bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/80 rounded-xl p-5 flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <span className="text-[11px] font-mono text-amber-400 uppercase tracking-wider font-semibold">
                  Current Anomaly Triage {selectedArm.activeIncidentId ? `· Incident: ${selectedArm.activeIncidentId}` : ''}
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  {selectedArm.lastInspectionTimestamp}
                </span>
              </div>

              {isSelectedDegraded ? (
                <div className="mt-3 space-y-3 font-mono">
                  <div>
                    <h3 className="text-sm font-bold text-white font-sans">
                      {liveIncident ? (liveIncident.root_cause?.root_cause?.name || 'Joint-3 Failure') : 'Joint-3 Harmonic Drive Degradation'}
                    </h3>
                    <p className="text-xs text-slate-400 mt-1 font-sans leading-relaxed">
                      {liveIncident ? 'Backend telemetry threshold breaches and failed pick-and-place detected. No torque ripple or backlash measurements supplied.' : 'No backend anomaly details available.'}
                    </p>
                  </div>

                  <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800/80 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Severity:</span>
                      <span className="text-amber-400 font-bold">{liveIncident ? liveIncident.severity : 'Stage II Progressive Wear'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Current Action Status:</span>
                      <span className={`font-bold ${
                        selectedArmPlan?.status === 'simulation_applied'
                          ? 'text-emerald-400'
                          : selectedArmPlan?.status === 'simulating'
                          ? 'text-cyan-400'
                          : 'text-amber-300'
                      }`}>
                        {selectedArmPlan?.status === 'simulation_applied'
                          ? 'Simulated Mitigation Applied (Derated 70%)'
                          : selectedArmPlan?.status === 'simulating'
                          ? 'Kinematic Simulation In Progress'
                          : 'Pending Human Approval (backend validation required)'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Overall Cell Health (backend):</span>
                      <span className="text-amber-400 font-bold tabular-nums">{selectedArm.joint3HealthScore}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">J3 Vibration:</span>
                      <span className="text-white font-bold tabular-nums">{liveIncident?.telemetry_result?.breached_signals?.find(x=>x.signal==='joint_3_vibration')?.actual ?? 'N/A'} mm/s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Position Error:</span>
                      <span className="text-white font-bold tabular-nums">{liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='position_error')?.actual ?? 'N/A'} mm` : 'N/A'}</span>
                    </div>
                    <div className="flex justify-between pt-1 border-t border-slate-900">
                      <span className="text-slate-500">Last Telemetry Update:</span>
                      <span className="text-slate-300 tabular-nums">{selectedArm.lastInspectionTimestamp}</span>
                    </div>
                  </div>

                  {/* Recommended Next Action from Agent Investigation */}
                  <div className="p-2.5 bg-slate-950/90 rounded-lg border border-cyan-900/40 text-xs space-y-1">
                    <div className="flex items-center gap-1.5 text-cyan-400 font-bold">
                      <Zap className="w-3.5 h-3.5" />
                      <span className="font-mono uppercase text-[10px] tracking-wider">Recommended Next Action</span>
                    </div>
                    <p className="text-[11px] text-slate-300 font-sans leading-relaxed">
                      {adkReport?.recommendedMitigation || 'No backend recovery recommendation available'}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="mt-6 text-center space-y-2 py-4">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                  <h3 className="text-sm font-bold text-white font-sans">
                    All Workcell Systems Nominal
                  </h3>
                  <p className="text-xs text-slate-400 font-sans max-w-xs mx-auto">
                    {selectedArm.id} operates within standard factory kinematic limits. No anomalies detected on any axis.
                  </p>
                </div>
              )}
            </div>

            {/* Primary CTA */}
            <div>
              {isSelectedDegraded ? (
                <button
                  onClick={() => onInvestigateArm(selectedArm.id)}
                  className="w-full py-2.5 px-4 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20"
                >
                  <span>Investigate Incident</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={() => onInvestigateArm(selectedArm.id)}
                  className="w-full py-2 px-4 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5"
                >
                  <span>View Arm Diagnostics</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* PANEL 3: RIGHT — VISUAL INTELLIGENCE (Gemini Robotics ER 2) */}
          <div className="bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/80 rounded-xl p-5 flex flex-col justify-between space-y-4">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Eye className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-bold text-white tracking-wide uppercase font-mono">
                    Visual Intelligence
                  </span>
                </div>
                <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950 border border-cyan-800 px-2 py-0.5 rounded">
                  Gemini Robotics ER 2
                </span>
              </div>

              {isSelectedDegraded ? (
                <div className="mt-3 space-y-3 font-mono text-xs">
                  <div className="text-[11px] text-slate-400 font-sans">
                    Cached visual model inference for Joint-3 elbow housing:
                  </div>

                  <div className="space-y-2">
                    {visualReport.observations.map((obs) => (
                      <div
                        key={obs.id}
                        className="p-2.5 bg-slate-950/80 border border-slate-800/90 rounded-lg space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white">{obs.label}</span>
                          <span className="text-[10px] text-cyan-400 font-bold">{obs.confidence}%</span>
                        </div>
                        <p className="text-[11px] text-slate-400 font-sans line-clamp-2">
                          {obs.description}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* Evidence Provenance Label */}
                  <div className="p-2 bg-slate-950/90 rounded border border-slate-800 flex items-center justify-between text-[10px] font-mono">
                    <span className="text-slate-500 uppercase tracking-wider">Provenance:</span>
                    <span className="text-cyan-400 font-semibold truncate ml-2">
                      Cached Gemini Robotics ER 2 observations (not a joint macro inspection)
                    </span>
                  </div>
                </div>
              ) : (
                <div className="mt-6 text-center space-y-2 py-4">
                  <ShieldCheck className="w-8 h-8 text-cyan-400 mx-auto" />
                  <h4 className="text-xs font-bold text-white font-sans">No Incident-Level Visual Evidence</h4>
                  <p className="text-xs text-slate-400 font-sans max-w-xs mx-auto">
                    No backend video-based joint seal or gear inspection is provided.
                  </p>
                </div>
              )}
            </div>

            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span>Confidence Score:</span>
              <span className="text-cyan-400 font-bold">{isSelectedDegraded ? `${visualReport.confidenceScore}%` : 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4. COMPACT TELEMETRY SUMMARY */}
      <div className="bg-gradient-to-b from-slate-900/90 to-slate-950/90 border border-slate-800/80 rounded-xl p-4 lg:p-5">
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider">
              {selectedArm.id} Joint-3 Telemetry Summary
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            {'Backend incident sample · frequency not specified'}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 font-mono text-xs">
          {/* Vibration */}
          <div className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-lg">
            <div className="text-[10px] text-slate-500 uppercase">J3 Vibration</div>
            <div className={`text-base font-bold mt-1 tabular-nums ${
              selectedArm.joint3Telemetry.vibrationAccelerationG > 0.4 ? 'text-amber-400' : 'text-slate-200'
            }`}>
              {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='joint_3_vibration')?.actual ?? 'N/A'} mm/s` : 'N/A'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">{liveIncident ? 'Measured channel · alert threshold 2.5 mm/s' : 'Illustrative 120 Hz Mesh Harmonic'}</div>
          </div>

          {/* Motor Torque */}
          <div className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-lg">
            <div className="text-[10px] text-slate-500 uppercase">{liveIncident ? 'Motor Current' : 'J3 Motor Torque'}</div>
            <div className="text-base font-bold text-white mt-1 tabular-nums">
              {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='motor_current')?.actual ?? 'N/A'} A` : `${joint3?.torqueNm.toFixed(1)} / ${joint3?.ratedTorqueNm} Nm`}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">{liveIncident ? 'Alert threshold 8.5 A' : `${((joint3?.torqueNm || 0) / (joint3?.ratedTorqueNm || 1) * 100).toFixed(0)}% Load Ratio`}</div>
          </div>

          {/* Temperature */}
          <div className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-lg">
            <div className="text-[10px] text-slate-500 uppercase">{liveIncident ? 'Temperature (sensor)' : 'Winding Temperature'}</div>
            <div className={`text-base font-bold mt-1 tabular-nums ${
              selectedArm.joint3Telemetry.motorWindingTempC > 55 ? 'text-amber-400' : 'text-slate-200'
            }`}>
              {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='temperature')?.actual ?? 'N/A'}°C` : 'N/A'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">{liveIncident ? 'Alert threshold 75°C' : '+18.2°C above ambient'}</div>
          </div>

          {/* Position Error */}
          <div className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-lg">
            <div className="text-[10px] text-slate-500 uppercase">{liveIncident ? 'Position Error' : 'Tracking Error / Backlash'}</div>
            <div className={`text-base font-bold mt-1 tabular-nums ${
              selectedArm.joint3Telemetry.backlashArcmin > 2 ? 'text-amber-400' : 'text-slate-200'
            }`}>
              {liveIncident ? `${liveIncident.telemetry_result?.breached_signals?.find(x=>x.signal==='position_error')?.actual ?? 'N/A'} mm` : 'N/A'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">{liveIncident ? 'Alert threshold 0.5 mm' : 'Illustrative baseline: < 1.0 arcmin'}</div>
          </div>

          {/* Cycle Time */}
          <div className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-lg">
            <div className="text-[10px] text-slate-500 uppercase">Cycle Duration</div>
            <div className="text-base font-bold text-white mt-1 tabular-nums">
              {selectedArm.cycleTimeSeconds ? `${selectedArm.cycleTimeSeconds}s` : 'N/A'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">{liveIncident ? 'Alert threshold 45 s' : `Cycle #${selectedArm.dailyCycleCount}`}</div>
          </div>
        </div>
      </div>

      {/* 5. AGENTIC INVESTIGATION SUMMARY (Google ADK) */}
      <div className="bg-gradient-to-b from-slate-900/95 to-slate-950/95 border border-slate-800/80 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <Bot className="w-5 h-5 text-cyan-400" />
            <div>
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Agentic Investigation Summary
              </h3>
              <span className="text-[11px] text-slate-400 font-sans">
                {liveIncident ? <>Backend five-agent trace — <strong>{liveIncident.adk_orchestration?.provenance?.execution_mode || 'unverified execution mode'}</strong></> : <>Illustrative reasoning view</>}
              </span>
            </div>
          </div>

          <button
            onClick={() => onInvestigateArm(selectedArm.id, 'agentic_investigation')}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white border border-slate-700 rounded-lg text-xs font-mono font-medium flex items-center gap-1.5 transition-colors self-start sm:self-auto"
          >
            <span>View Investigation Details</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* 3 Core Pillars: OBSERVE - REASON - RECOMMEND */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          {/* OBSERVE */}
          <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-2">
            <div className="text-[11px] font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              01. Observe
            </div>
            <p className="text-slate-300 font-sans text-xs leading-relaxed">
              {liveIncident ? '5 telemetry limits breached. Cached Gemini Robotics ER 2 video observed a failed pick-and-place operation.' : 'Illustrative agent summary — no active backend finding.'}
            </p>
          </div>

          {/* REASON */}
          <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-2">
            <div className="text-[11px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              02. Reason
            </div>
            <p className="text-slate-300 font-sans text-xs leading-relaxed">
              {liveIncident ? 'Joint-3 Mechanical Degradation ranked highest (evidence score 0.70); fixture misalignment and conveyor instability remain alternatives.' : 'Illustrative agent summary — no active backend finding.'}
            </p>
          </div>

          {/* RECOMMEND */}
          <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-2">
            <div className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              03. Recommend
            </div>
            <p className="text-slate-300 font-sans text-xs leading-relaxed">
              {liveIncident ? `${liveIncident.cell_id}: ${liveIncident.production_state}. ${liveIncident.recovery_plan?.recommended_actions?.length || 0}-step recovery proposal requires human approval and verification.` : 'No backend incident or agent analysis available.'}
            </p>
          </div>
        </div>

        <div className="text-[10px] font-mono text-slate-500 pt-1">
          {liveIncident ? `Source: backend incident ${liveIncident.incident_id} · ${liveIncident.adk_orchestration?.provenance?.execution_mode || 'execution unverified'}` : 'Illustrative agent summary'}
        </div>
      </div>
    </div>
  );
};
