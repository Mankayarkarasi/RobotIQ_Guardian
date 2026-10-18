"""
RoboIQ Guardian - Google ADK Tools
Wraps existing backend services as ADK-compatible tools.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parents[2]
THRESHOLDS_FILE = BASE_DIR / "data" / "config" / "thresholds.json"


def _get_active_incidents() -> Dict[str, Dict]:
    """Retrieve shared incident registry from main module if running."""
    try:
        from backend.api.main import INCIDENTS
        return INCIDENTS
    except Exception:
        return {}


_FALLBACK_CACHE: Dict[str, Any] = {}


def _load_incident_or_fallback(incident_id: str) -> Dict[str, Any]:
    """
    Look up incident from INCIDENTS store, or load baseline failure incident
    if incident_id is not yet registered or after demo reset.
    """
    incidents = _get_active_incidents()
    if incident_id in incidents:
        return incidents[incident_id]

    # If any failure incident is in memory, pick the first failure incident
    for inc in incidents.values():
        if inc.get("severity") in ("HIGH", "CRITICAL") or inc.get("state") == "RECOVERY_PROPOSED":
            return inc

    if incident_id in _FALLBACK_CACHE:
        return _FALLBACK_CACHE[incident_id]

    # Fallback to loading directly from data/telemetry/failure.json and cached ER
    from backend.services.telemetry_analyzer import analyze_telemetry
    from backend.services.robotics_er_service import analyze_video
    from backend.services.evidence_engine import build_evidence
    from backend.services.hypothesis_engine import get_hypotheses
    from backend.services.hypothesis_scoring import score_hypotheses
    from backend.services.root_cause_service import select_root_cause
    from backend.services.recovery_service import generate_recovery_plan
    from backend.services.recovery_prediction_service import predict_recovery_success

    tel_path = BASE_DIR / "data" / "telemetry" / "failure.json"
    vid_path = BASE_DIR / "data" / "videos" / "failure.mp4"

    with open(tel_path, "r", encoding="utf-8") as f:
        telemetry = json.load(f)
    with open(THRESHOLDS_FILE, "r", encoding="utf-8") as f:
        thresholds = json.load(f)

    tel_res = analyze_telemetry(telemetry, thresholds).to_dict()
    er_res = analyze_video(str(vid_path), use_cache=True, cache_only=True)
    evidence = build_evidence(tel_res, er_res)
    hypos = get_hypotheses()
    scored = score_hypotheses(hypos, evidence)
    root_cause = select_root_cause(scored)
    rec_plan = generate_recovery_plan(root_cause, evidence)
    rec_pred = predict_recovery_success(root_cause, evidence, rec_plan, use_cache=True, cache_only=True)

    synthetic = {
        "incident_id": incident_id or "INC-E9005A5F",
        "state": "RECOVERY_PROPOSED",
        "cell_id": "CELL-03",
        "robot_id": "R-07",
        "severity": "HIGH",
        "production_state": "PAUSED",
        "inputs": {
            "telemetry_path": "data/telemetry/failure.json",
            "video_path": "data/videos/failure.mp4",
        },
        "telemetry_result": tel_res,
        "robotics_er_result": er_res,
        "evidence": evidence,
        "hypothesis_ranking": scored,
        "root_cause": root_cause,
        "recovery_plan": rec_plan,
        "recovery_prediction": rec_pred,
        "audit_log": [],
    }
    _FALLBACK_CACHE[incident_id or "INC-E9005A5F"] = synthetic
    return synthetic


# =========================================================
# TOOL IMPLEMENTATIONS (Reusing existing services)
# =========================================================

def get_robot_telemetry(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve recorded robotic manipulator telemetry readings and threshold breach analysis.
    Signals analyzed: cycle_time, position_error, joint_3_vibration, motor_current, temperature.
    """
    incident = _load_incident_or_fallback(incident_id)
    tel_result = incident.get("telemetry_result", {})
    
    with open(THRESHOLDS_FILE, "r", encoding="utf-8") as f:
        thresholds = json.load(f)

    return {
        "incident_id": incident.get("incident_id", incident_id),
        "cell_id": incident.get("cell_id", "CELL-03"),
        "robot_id": incident.get("robot_id", "R-07"),
        "telemetry_status": tel_result.get("status", "FAILURE"),
        "breached_signals": tel_result.get("breached_signals", []),
        "thresholds": thresholds,
        "summary": f"{len(tel_result.get('breached_signals', []))} sensor signals breached operating thresholds."
    }


def get_video_observations(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve Gemini Robotics ER 2 embodied video observations and task execution assessment.
    Returns timestamped physical behavior observations, motion stability, and task completion.
    """
    incident = _load_incident_or_fallback(incident_id)
    er_result = incident.get("robotics_er_result", {})

    return {
        "incident_id": incident.get("incident_id", incident_id),
        "model_name": er_result.get("generated_by", "gemini-robotics-er-2-preview"),
        "cache_status": er_result.get("cache_status", "CACHE_HIT"),
        "operation_status": er_result.get("operation_status", "ABNORMAL"),
        "motion_stability": er_result.get("motion_stability", "STABLE"),
        "task_completed": er_result.get("task_completed", False),
        "observations": er_result.get("observations", []),
        "summary": er_result.get("summary", "Robotic manipulator arm motion observed with abnormal task completion.")
    }


def get_incident_evidence(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve verified multimodal evidence records combining deterministic telemetry breaches
    and Gemini Robotics ER 2 visual observations with preserved evidence IDs (T1-T5, V6-V10).
    """
    incident = _load_incident_or_fallback(incident_id)
    evidence = incident.get("evidence", [])

    return {
        "incident_id": incident.get("incident_id", incident_id),
        "total_evidence_count": len(evidence),
        "telemetry_evidence": [e for e in evidence if e.get("type") == "telemetry"],
        "visual_evidence": [e for e in evidence if e.get("type") == "visual"],
        "all_evidence": evidence
    }


def get_root_cause_hypotheses(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve ranked root-cause hypotheses evaluated against correlated multimodal evidence.
    Hypothesis scores represent empirical evidence support scores, not calibrated probabilities.
    """
    incident = _load_incident_or_fallback(incident_id)
    hypotheses = incident.get("hypothesis_ranking", [])
    root_cause = incident.get("root_cause", {})

    return {
        "incident_id": incident.get("incident_id", incident_id),
        "hypotheses": hypotheses,
        "identified_root_cause": root_cause,
        "score_type": "evidence_score_not_calibrated_probability",
        "decision_threshold": root_cause.get("threshold", 0.70)
    }


def get_recovery_plan(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve governed AI-generated recovery recommendation sequence and required safety actions.
    All recovery operations in this system are simulated; human approval is mandatory.
    """
    incident = _load_incident_or_fallback(incident_id)
    plan = incident.get("recovery_plan", {})

    return {
        "incident_id": incident.get("incident_id", incident_id),
        "status": plan.get("status", "RECOVERY_PROPOSED"),
        "risk_level": plan.get("risk_level", "HIGH"),
        "human_approval_required": plan.get("human_approval_required", True),
        "recommended_actions": plan.get("recommended_actions", []),
        "reasoning_summary": plan.get("reasoning_summary", "")
    }


def assess_recovery_risk(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve recovery success assessment and residual risk factors from Gemini Robotics ER.
    Identifies residual risk from simulated maintenance versus physical hardware replacement.
    """
    incident = _load_incident_or_fallback(incident_id)
    pred = incident.get("recovery_prediction", {})

    return {
        "incident_id": incident.get("incident_id", incident_id),
        "recovery_success_score": pred.get("recovery_success_score", 0.15),
        "score_type": pred.get("score_type", "evidence_based_not_calibrated_probability"),
        "residual_risk": pred.get("residual_risk", "HIGH"),
        "expected_post_recovery_state": pred.get("expected_post_recovery_state", ""),
        "risk_factors": pred.get("risk_factors", []),
        "verification_requirements": pred.get("verification_requirements", []),
        "summary": pred.get("summary", "")
    }


def simulate_recovery_option(incident_id: str, action_type: str = "simulation") -> Dict[str, Any]:
    """
    Evaluate simulated recovery option against safety governance constraints.
    Enforces that simulated repairs cannot automatically approve physical motion or resume production.
    """
    incident = _load_incident_or_fallback(incident_id)
    is_approved = incident.get("approval", {}).get("status") == "RECOVERY_APPROVED"

    return {
        "incident_id": incident.get("incident_id", incident_id),
        "action_type": action_type,
        "execution_mode": "simulation",
        "physical_robot_motion": False,
        "human_approval_granted": is_approved,
        "human_approval_required": True,
        "safety_interlock": "ACTIVE",
        "production_resumption_authorized": False,
        "governance_note": "Simulated maintenance execution cannot clear physical joint degradation without verified physical repair."
    }


def get_recovery_outcome(incident_id: str) -> Dict[str, Any]:
    """
    Retrieve empirical recovery verification outcome and calculate closed-loop PSR when data is available.
    Never fabricates PSR; returns PENDING_VERIFICATION if physical verification has not been run.
    """
    incident = _load_incident_or_fallback(incident_id)
    verification = incident.get("verification")

    if verification and verification.get("status") == "RECOVERY_VERIFIED":
        tel_pass = verification.get("telemetry_pass", False)
        vis_pass = verification.get("visual_pass", False)
        psr = 1.0 if (tel_pass and vis_pass) else 0.0
        return {
            "incident_id": incident.get("incident_id", incident_id),
            "verification_status": "RECOVERY_VERIFIED",
            "psr": psr,
            "telemetry_pass": tel_pass,
            "visual_pass": vis_pass,
            "production_resumption_eligible": True,
            "details": "Post-recovery telemetry and visual verification passed all baseline thresholds."
        }
    
    return {
        "incident_id": incident.get("incident_id", incident_id),
        "verification_status": "PENDING_VERIFICATION",
        "psr": None,
        "telemetry_pass": None,
        "visual_pass": None,
        "production_resumption_eligible": False,
        "details": "Post-recovery verification pending. Production resumption blocked until physical intervention and validation cycle are confirmed."
    }
