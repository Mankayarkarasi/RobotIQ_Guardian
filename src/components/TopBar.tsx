import React from 'react';
import { NavSection, BackendState } from '../types';
import { ShieldAlert, RefreshCw, Layers, User, Activity } from 'lucide-react';

interface TopBarProps {
  activeSection: NavSection;
  onSelectSection: (section: NavSection) => void;
  backendState: BackendState;
  onRefreshBackend: () => void;
  advisoryCount: number;
}

export const TopBar: React.FC<TopBarProps> = ({
  activeSection,
  onSelectSection,
  backendState,
  onRefreshBackend,
  advisoryCount
}) => {
  return (
    <header className="sticky top-0 z-50 w-full bg-slate-950/95 backdrop-blur-md border-b border-slate-800/80 px-4 lg:px-8 py-2.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-6">
        {/* Zone 1: Official Product Branding with approved high-res PNG */}
        <div className="flex items-center gap-3.5 shrink-0">
          <img
            src="/roboiq-shield.png"
            alt="RoboIQ Guardian"
            className="h-14 w-14 object-contain drop-shadow-[0_0_12px_rgba(56,189,248,0.35)]"
          />
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight text-white">
                RoboIQ <span className="text-cyan-400">Guardian</span>
              </span>
            </div>
            <span className="text-xs font-medium text-slate-300 tracking-normal">
              Embodied Intelligence for Robotic Recovery
            </span>
            <span className="text-[10px] text-slate-500 tracking-tight hidden sm:block">
              Beyond Detection. Toward Intelligent Recovery.
            </span>
          </div>
        </div>

        {/* Zone 2: Exactly 4 Primary Navigation Items with Cyan Active Underline */}
        <nav className="hidden md:flex items-center gap-1 lg:gap-2">
          <button
            onClick={() => onSelectSection('fleet')}
            className={`px-4 py-2 text-sm font-semibold rounded-md transition-all whitespace-nowrap shrink-0 relative flex items-center gap-2 ${
              activeSection === 'fleet'
                ? 'text-cyan-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>Fleet</span>
            {activeSection === 'fleet' && (
              <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)] rounded-full" />
            )}
          </button>

          <button
            onClick={() => onSelectSection('investigate')}
            className={`px-4 py-2 text-sm font-semibold rounded-md transition-all whitespace-nowrap shrink-0 relative flex items-center gap-2 ${
              activeSection === 'investigate'
                ? 'text-cyan-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>Investigate</span>
            {advisoryCount > 0 && (
              <span className="ml-1.5 px-1.5 py-0.2 text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded">
                {advisoryCount} Alert
              </span>
            )}
            {activeSection === 'investigate' && (
              <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)] rounded-full" />
            )}
          </button>

          <button
            onClick={() => onSelectSection('recover')}
            className={`px-4 py-2 text-sm font-semibold rounded-md transition-all whitespace-nowrap shrink-0 relative flex items-center gap-2 ${
              activeSection === 'recover'
                ? 'text-cyan-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
            }`}
          >
            <RefreshCw className="w-4 h-4" />
            <span>Recover</span>
            {activeSection === 'recover' && (
              <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)] rounded-full" />
            )}
          </button>

          <button
            onClick={() => onSelectSection('evidence')}
            className={`px-4 py-2 text-sm font-semibold rounded-md transition-all whitespace-nowrap shrink-0 relative flex items-center gap-2 ${
              activeSection === 'evidence'
                ? 'text-cyan-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
            }`}
          >
            <Activity className="w-4 h-4" />
            <span>Evidence</span>
            {activeSection === 'evidence' && (
              <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)] rounded-full" />
            )}
          </button>
        </nav>

        {/* Zone 3: Demo Mode Indicator & User Profile */}
        <div className="flex items-center gap-3 shrink-0">
          {/* Demo Mode Indicator */}
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900/90 border border-slate-800 text-xs text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
            <span className="text-[11px] font-medium text-slate-300">Demo Mode</span>
          </div>

          {/* Backend Connection Indicator */}
          <button
            onClick={onRefreshBackend}
            title={backendState.connected ? `FastAPI Telemetry: Connected (${backendState.latencyMs}ms)` : `FastAPI Telemetry: Standalone PoC Mode`}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                backendState.connected ? 'bg-emerald-400' : 'bg-cyan-400'
              }`}
            />
            <span className="text-[11px] font-mono hidden md:inline">
              {backendState.connected ? `${backendState.latencyMs}ms` : 'PoC Node'}
            </span>
            <RefreshCw className="w-3 h-3 text-slate-500" />
          </button>

          {/* User/Operator Profile */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
            <div className="w-8 h-8 rounded-full bg-slate-900 border border-slate-700 flex items-center justify-center text-cyan-400 shadow-inner">
              <User className="w-4 h-4" />
            </div>
            <div className="hidden lg:flex flex-col text-left leading-tight">
              <span className="text-xs font-semibold text-white">Siddarth Kumar</span>
              <span className="text-[10px] text-slate-500 font-mono">Lead Robotics Engineer</span>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile nav fallback */}
      <div className="flex md:hidden items-center justify-around pt-2.5 border-t border-slate-900 mt-2">
        {(['fleet', 'investigate', 'recover', 'evidence'] as NavSection[]).map((sec) => (
          <button
            key={sec}
            onClick={() => onSelectSection(sec)}
            className={`px-3 py-1 text-xs font-medium capitalize ${
              activeSection === sec ? 'text-cyan-400 font-bold border-b-2 border-cyan-400' : 'text-slate-400'
            }`}
          >
            {sec}
          </button>
        ))}
      </div>
    </header>
  );
};
