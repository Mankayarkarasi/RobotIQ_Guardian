import { BackendState, RoboticArmUnit, ArmEventRecord } from '../types';

// Resolve base URL from environment variable or relative origin
const API_BASE = (import.meta.env.VITE_FASTAPI_URL || '').replace(/\/+$/, '');

export const BACKEND_CONFIG = {
  baseUrl: API_BASE || '/api',
  healthEndpoints: [
    `${API_BASE}/health`,
    `${API_BASE}/api/health`,
    `${API_BASE}/healthz`,
    `${API_BASE}/api/v1/health`
  ],
  armsEndpoints: [
    `${API_BASE}/fleet`,
    `${API_BASE}/api/arms`,
    `${API_BASE}/api/fleet`,
    `${API_BASE}/arms`,
    `${API_BASE}/api/v1/arms`
  ],
  eventsEndpoints: [
    `${API_BASE}/incidents`,
    `${API_BASE}/api/events`,
    `${API_BASE}/api/incidents`,
    `${API_BASE}/events`,
    `${API_BASE}/api/v1/events`
  ]
};

export async function checkFastApiHealth(): Promise<BackendState> {
  const startTime = performance.now();
  let lastError = 'No backend endpoint responded';

  // Try standard health endpoints sequentially
  for (const endpoint of BACKEND_CONFIG.healthEndpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1500);

      const res = await fetch(endpoint, {
        signal: controller.signal,
        headers: { 'Accept': 'application/json' }
      });
      clearTimeout(timeoutId);

      const latency = Math.round(performance.now() - startTime);

      if (res.ok) {
        return {
          connected: true,
          latencyMs: latency,
          url: endpoint,
          lastChecked: new Date().toLocaleTimeString()
        };
      } else {
        lastError = !API_BASE
          ? `HTTP ${res.status}: Route ${endpoint} is not served by Vite dev server. External FastAPI service required via VITE_FASTAPI_URL.`
          : `HTTP ${res.status}: ${res.statusText} at ${endpoint} from external FastAPI host.`;
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      lastError = msg.includes('abort') 
        ? `Connection timed out at ${endpoint}`
        : `Connection failed at ${endpoint} (${msg})`;
    }
  }

  return {
    connected: false,
    latencyMs: 0,
    url: BACKEND_CONFIG.baseUrl,
    lastChecked: new Date().toLocaleTimeString(),
    error: lastError
  };
}

export async function fetchRemoteArms(): Promise<RoboticArmUnit[] | null> {
  for (const endpoint of BACKEND_CONFIG.armsEndpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1500);
      const res = await fetch(endpoint, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Continue to next candidate
    }
  }
  return null;
}

export async function fetchRemoteEvents(): Promise<ArmEventRecord[] | null> {
  for (const endpoint of BACKEND_CONFIG.eventsEndpoints) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1500);
      const res = await fetch(endpoint, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Continue to next candidate
    }
  }
  return null;
}

// Verified backend-only integration. Never pretend missing sensor channels are measured.
export interface GuardianIncidentSummary {
  incident_id: string; cell_id: string; robot_id: string; state: string;
  severity: string; created_at: string;
  diagnosis?: { root_cause?: string; evidence_score?: number };
  recovery?: { status?: string; risk_level?: string; execution_status?: string | null };
}
export interface GuardianIncidentDetail extends GuardianIncidentSummary {
  telemetry_result?: { breached_signals?: Array<{signal:string;actual:number;threshold:number}> };
  robotics_er_result?: { generated_by?:string; cache_status?:string;summary?:string;observations?:Array<{timestamp_seconds:number;observation:string;confidence:number}> };
  adk_orchestration?: { execution_trace?:Array<{step:number;agent:string;tool:string;timestamp:string;action:string;status:string;output?:unknown}>;provenance?:{execution_mode?:string;runner_note?:string;visual_evidence?:string}; investigation_summary?:string };
  root_cause?: { root_cause?:{id:string;name:string};score?:number };
  recovery_plan?: { recommended_actions?:string[];risk_level?:string;human_approval_required?:boolean;reasoning_summary?:string };
  production_state?: string;
  recovery_prediction?: {recovery_success_score?:number;residual_risk?:string;score_type?:string;summary?:string;verification_requirements?:string[];cache_status?:string};
  state_history?: unknown[];
  analysis_status?: string;
  recommendation?: string;
  hypothesis_ranking?: unknown[];
  audit_log?:Array<{event_id:string;event:string;timestamp:string;source:string;entry_hash?:string;prev_hash?:string;details?:unknown}>;
  evidence?:Array<{evidence_id:string;type:string;description:string;signal?:string;value?:number;threshold?:number;timestamp_seconds?:number;confidence?:number}>;
}
export interface GuardianFleetCell { cell_id:string;robot_id:string;status:string;health_score:number;production_state:string;active_incident:string|null }
async function guardianGet<T>(route:string):Promise<T> {
  const res=await fetch(`${API_BASE}${route}`, {headers:{Accept:'application/json'}});
  if(!res.ok) throw new Error(`${route}: HTTP ${res.status}`);
  return res.json() as Promise<T>;
}
export async function fetchGuardianSnapshot():Promise<{fleet:GuardianFleetCell[];incident:GuardianIncidentDetail|null}> {
  const [fleetResponse, list] = await Promise.all([
    guardianGet<{fleet:GuardianFleetCell[]}>('/fleet'),
    guardianGet<{incidents:GuardianIncidentSummary[]}>('/incidents')
  ]);
  if(!Array.isArray(fleetResponse.fleet) || !Array.isArray(list.incidents)) throw new Error('Invalid FastAPI response');
  const summary=[...list.incidents].sort((a,b)=>(b.created_at||'').localeCompare(a.created_at||''))[0];
  const incident=summary ? await guardianGet<GuardianIncidentDetail>(`/incident/${encodeURIComponent(summary.incident_id)}`) : null;
  return {fleet:fleetResponse.fleet,incident};
}


// Historical synthetic episodes are explicitly separate from the live demo robots.
export interface HistoricalEpisode { episode_id: string; robot_id: string; scenario_type: string; start_timestamp?: string; end_timestamp?: string; }
export interface HistoricalTelemetryRecord { timestamp: string; cycle_time_s: number; joint_3_vibration_mm_s: number; motor_current_a: number; motor_temperature_c: number; position_error_mm: number; defect_rate_pct: number; machine_state?: string; }
export interface HistoricalTelemetryCatalog { source: string; total_records: number; robots: string[]; episodes: HistoricalEpisode[]; }
export interface HistoricalTelemetryHistory { source: string; robot_id: string; episode_id: string; scenario_type: string; total_matching_records: number; returned_records: number; records: HistoricalTelemetryRecord[]; }
export async function fetchTelemetryEpisodes(): Promise<HistoricalTelemetryCatalog> {
  const response = await fetch(`${API_BASE}/telemetry/episodes`);
  if (!response.ok) throw new Error(`Historical telemetry episodes: HTTP ${response.status}`);
  return response.json();
}
export async function fetchTelemetryHistory(robotId: string, episodeId: string, limit=240): Promise<HistoricalTelemetryHistory> {
  const query = new URLSearchParams({robot_id:robotId,episode_id:episodeId,limit:String(limit)});
  const response = await fetch(`${API_BASE}/telemetry/history?${query}`);
  if (!response.ok) throw new Error(`Historical telemetry history: HTTP ${response.status}`);
  return response.json();
}
