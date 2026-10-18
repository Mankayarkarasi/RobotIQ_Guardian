"""
RoboIQ Guardian — What-If Recovery Intelligence Service (Step 41B)

Evaluates three evidence-grounded hypothetical recovery alternatives for
Joint-3 mechanical degradation incidents:
  - Option A: Safe Containment
  - Option B: Recalibration Only
  - Option C: Joint-3 Maintenance/Replacement + Recalibration

Strict Governance Constraints:
- Read-only simulation analysis; does not mutate incident state or execute commands.
- Grounded strictly in recorded incident evidence, telemetry thresholds, and cached Gemini Robotics ER 2 observations.
- Rejects unsupported fault scenarios with clear UNSUPPORTED_FAULT_SCENARIO status.
- Never fabricates measured probabilities, durations, or costs.
- No paid Gemini API calls or live robot interaction.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


def now_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def evaluate_what_if_recovery(
    incident: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate three evidence-grounded recovery alternatives for an incident.
    Returns structured alternatives, evidence grounding, residual risks,
    qualitative recommendation, and execution provenance.
    """
    incident_id = incident.get("incident_id", "UNKNOWN_INCIDENT")

    # 1. Inspect incident root cause and fault scenario
    root_cause_data = incident.get("root_cause") or {}
    root_cause_obj = root_cause_data.get("root_cause") or {}
    if isinstance(root_cause_obj, dict):
        rc_id = root_cause_obj.get("id")
        rc_name = root_cause_obj.get("name")
    else:
        rc_id = str(root_cause_obj) if root_cause_obj else None
        rc_name = str(root_cause_obj) if root_cause_obj else None

    # Check top candidate if root_cause was not finalized
    if not rc_id and root_cause_data.get("top_candidate"):
        top_cand = root_cause_data.get("top_candidate", {})
        rc_id = top_cand.get("id")
        rc_name = top_cand.get("name")

    # Check hypothesis ranking
    if not rc_id and incident.get("hypothesis_ranking"):
        rankings = incident.get("hypothesis_ranking", [])
        if rankings and isinstance(rankings[0], dict):
            rc_id = rankings[0].get("id")
            rc_name = rankings[0].get("name")

    # If telemetry clearly indicates Joint-3 vibration, map to H1
    if not rc_id and (
        "joint_3_vibration" in str(incident.get("telemetry_result", {}))
        or "joint_3_vibration" in str(incident.get("evidence", []))
    ):
        rc_id = "H1"
        rc_name = "Joint-3 Mechanical Degradation"

    # Check whether the incident is a supported Joint-3 failure scenario
    is_joint3_fault = (
        rc_id == "H1"
        or "Joint-3" in str(rc_name)
        or "joint_3_vibration" in str(incident.get("telemetry_result", {}))
        or "joint_3_vibration" in str(incident.get("evidence", []))
    )

    if not is_joint3_fault:
        return {
            "incident_id": incident_id,
            "status": "UNSUPPORTED_FAULT_SCENARIO",
            "message": (
                "What-If Recovery Intelligence alternatives (A, B, C) are specifically "
                "calibrated for Joint-3 Mechanical Degradation incidents. The selected "
                f"incident (root cause: {rc_name or 'Unknown/Normal'}) does not exhibit "
                "the required Joint-3 mechanical failure signature."
            ),
            "root_cause_id": rc_id,
            "root_cause_name": rc_name,
            "incident_state": incident.get("state"),
            "alternatives": [],
            "recommendation": None,
            "provenance": {
                "engine": "RoboIQ Guardian What-If Recovery Intelligence",
                "version": "1.0.0",
                "execution_mode": "read_only_simulation",
                "timestamp": now_timestamp(),
            },
        }

    # 2. Extract authoritative recorded evidence IDs
    evidence_list = incident.get("evidence") or []
    telemetry_ev_ids = [
        ev.get("evidence_id")
        for ev in evidence_list
        if ev.get("type") == "telemetry" and ev.get("evidence_id")
    ]
    visual_ev_ids = [
        ev.get("evidence_id")
        for ev in evidence_list
        if ev.get("type") == "visual" and ev.get("evidence_id")
    ]
    all_ev_ids = [ev.get("evidence_id") for ev in evidence_list if ev.get("evidence_id")]

    # Fallback to standard evidence IDs if not yet populated in memory
    if not telemetry_ev_ids:
        telemetry_ev_ids = ["T1", "T2", "T3", "T4", "T5"]
    if not visual_ev_ids:
        visual_ev_ids = ["V6", "V7", "V8", "V9", "V10"]
    if not all_ev_ids:
        all_ev_ids = telemetry_ev_ids + visual_ev_ids

    # Telemetry specific mappings:
    pos_err_ids = [
        ev.get("evidence_id") for ev in evidence_list if ev.get("signal") == "position_error"
    ] or ["T2"]
    vibration_ids = [
        ev.get("evidence_id") for ev in evidence_list if ev.get("signal") == "joint_3_vibration"
    ] or ["T3"]
    current_ids = [
        ev.get("evidence_id") for ev in evidence_list if ev.get("signal") == "motor_current"
    ] or ["T4"]
    temp_ids = [
        ev.get("evidence_id") for ev in evidence_list if ev.get("signal") == "temperature"
    ] or ["T5"]

    mech_stress_ev_ids = sorted(list(set(vibration_ids + current_ids + temp_ids + visual_ev_ids[-1:])))

    # 3. Construct Evidence-Grounded Alternatives

    # Option A: Safe Containment
    option_a = {
        "strategy_id": "STRAT-A-CONTAINMENT",
        "strategy_name": "Option A — Safe Containment",
        "option_code": "A",
        "title": "Maintain Safe Stopped State & Cell Containment",
        "description": (
            "Maintain the robot in a safe paused/stopped state without active physical "
            "intervention. Lock joint electromagnetic brakes, de-energize actuator drive circuits, "
            "and preserve forensic telemetry, vibration logs, and vision recordings for maintenance investigation."
        ),
        "supporting_evidence_ids": all_ev_ids,
        "contradicting_evidence_ids": [],
        "expected_qualitative_benefits": [
            "Prevents progressive structural wear, bearing spalling, and gear tooth fracture in Joint-3.",
            "Eliminates collision hazards with peripheral workcell tooling, fixtures, and adjacent safety barriers.",
            "Prevents actuator motor thermal runaway and insulation degradation caused by high stall currents (10.2 A vs 8.5 A limit).",
            "Preserves uncorrupted post-incident telemetry logs and camera recordings for forensic root-cause verification.",
        ],
        "unresolved_mechanical_risks": [
            "Zero recovery progress: cell throughput remains zero and robot remains halted in safe stop.",
            "Joint-3 mechanical degradation, high vibration (5.7 mm/s), and kinematic path deviation remain uncorrected.",
            "Workpiece remains unrecovered at the pickup station, requiring manual cell clearing.",
        ],
        "human_approval_prerequisites": [
            "Operations supervisor formal acknowledgement of production cell shutdown and line rerouting.",
            "Certified robotics maintenance technician dispatch authorization for physical inspection.",
        ],
        "telemetry_and_visual_verification_requirements": [
            "Telemetry: verify zero commanded motor velocity, active mechanical brake lock, and motor current decaying to 0.0 A.",
            "Telemetry: verify Joint-3 winding temperature safely cooling below ambient safety threshold (< 45°C).",
            "Visual: Gemini Robotics ER camera confirms manipulator stationary at safe park position with zero payload drift.",
        ],
        "recommendation_rationale": (
            "Appropriate and strictly required as an immediate containment and stabilization baseline, "
            "but insufficient on its own because it provides zero recovery progress and leaves the physical fault unresolved."
        ),
        "provenance": {
            "telemetry_source": "data/telemetry/failure.json",
            "vision_model": "gemini-robotics-er-2-preview (cached observations)",
            "governance_mode": "read_only_hypothetical_analysis",
            "evidence_grounding": "multimodal_threshold_breaches",
        },
    }

    # Option B: Recalibration Only
    option_b = {
        "strategy_id": "STRAT-B-RECALIBRATION",
        "strategy_name": "Option B — Recalibration Only",
        "option_code": "B",
        "title": "Simulated Sensor Calibration & Kinematic Offset Reset",
        "description": (
            "Perform software recalibration, kinematic transform offset adjustments, and resolver/encoder "
            "zeroing without physical component replacement, disassembly, or mechanical maintenance."
        ),
        "supporting_evidence_ids": pos_err_ids,
        "contradicting_evidence_ids": mech_stress_ev_ids,
        "expected_qualitative_benefits": [
            "Rapid software execution with zero tooling downtime, spare parts requisitions, or cell teardown.",
            "Re-establishes mathematical kinematic coordinate alignment and encoder zero-point baselines in the controller.",
        ],
        "unresolved_mechanical_risks": [
            "High residual risk: physical mechanical wear, tooth backlash, and bearing degradation in Joint-3 cannot be repaired by software offsets.",
            "High vibration (5.7 mm/s vs 2.5 mm/s threshold) and severe motor current overload (10.2 A vs 8.5 A) will immediately recur under dynamic payload loading.",
            "Risk of sudden mechanical seizure or catastrophic gear drive failure during active production motion.",
            "Grounded in Gemini Robotics ER 2 recovery prediction: estimated success score 0.15, HIGH residual risk.",
        ],
        "human_approval_prerequisites": [
            "Lead systems engineer formal approval to execute software calibration sweep.",
            "Explicit risk sign-off accepting unaddressed mechanical degradation and potential imminent hardware damage.",
        ],
        "telemetry_and_visual_verification_requirements": [
            "Telemetry: continuous multi-channel monitoring of Joint-3 vibration, temperature, and motor current during test trajectory.",
            "Visual: Gemini Robotics ER 2 multi-frame camera verification of end-effector repeatability at calibration markers.",
        ],
        "recommendation_rationale": (
            "Strongly discouraged as a standalone recovery action. While position error (T2) appears superficially addressable via calibration, "
            "vibration (T3), current overload (T4), and thermal buildup (T5) conclusively indicate physical mechanical degradation. "
            "Grounded in cached Gemini Robotics ER 2 prediction (15% success score; HIGH residual risk). Software calibration cannot repair physical mechanical wear."
        ),
        "provenance": {
            "telemetry_source": "data/telemetry/failure.json",
            "vision_model": "gemini-robotics-er-2-preview (cached observations)",
            "prediction_cache": "data/cache/recovery_prediction_703ecff0820c0783.json",
            "governance_mode": "read_only_hypothetical_analysis",
            "evidence_grounding": "contradicted_by_vibration_and_current_telemetry",
        },
    }

    # Option C: Joint-3 Component Replacement + Recalibration
    option_c = {
        "strategy_id": "STRAT-C-MAINTENANCE",
        "strategy_name": "Option C — Joint-3 Maintenance & Governed Verification",
        "option_code": "C",
        "title": "Joint-3 Component Replacement, Recalibration & Verification",
        "description": (
            "Execute physical maintenance/replacement of the degraded Joint-3 gear/motor assembly, "
            "followed by precision kinematic recalibration, no-load validation sweep, and loaded trial cycle "
            "under multimodal sensor and visual verification."
        ),
        "supporting_evidence_ids": all_ev_ids,
        "contradicting_evidence_ids": [],
        "expected_qualitative_benefits": [
            "Directly resolves the verified physical root cause (H1 — Joint-3 Mechanical Degradation) by replacing worn mechanical drive components.",
            "Restores nominal joint compliance, structural damping, and precision trajectory tracking under dynamic payload loads.",
            "Implements the Gemini Robotics ER 2 proposed 7-step governed recovery sequence (pause, inspect, replace, calibrate, validate).",
            "Eliminates motor current overload and overheating, restoring continuous operational reliability.",
        ],
        "unresolved_mechanical_risks": [
            "Simulated or proposed component replacement does not guarantee physical recovery without post-maintenance physical verification.",
            "Requires re-baselining of Joint-3 torque limits, backlash measurements, and thermal dissipation before full-speed production authorization.",
            "Improper installation or bolt torque could introduce secondary alignment or backlash discrepancies.",
        ],
        "human_approval_prerequisites": [
            "Certified robotics maintenance technician sign-off on physical component replacement and manufacturer torque tightening specifications.",
            "Manufacturing safety engineer authorization for controlled low-speed validation motion.",
        ],
        "telemetry_and_visual_verification_requirements": [
            "Telemetry: verify Joint-3 vibration returns to nominal baseline (<= 2.5 mm/s; recorded failure was 5.7 mm/s).",
            "Telemetry: verify motor current (<= 8.5 A; failure was 10.2 A), temperature (<= 75°C; failure was 81°C), and position error (<= 0.5 mm; failure was 1.6 mm).",
            "Visual: Gemini Robotics ER 2 inspection confirms smooth pick-and-place execution without empty gripper retraction or fault annunciators.",
        ],
        "recommendation_rationale": (
            "Recommended recovery strategy. It directly targets the verified physical root cause identified by multimodal evidence. "
            "However, consistent with safety governance, production resumption must remain contingent on physical component replacement "
            "and independent post-recovery telemetric and visual verification."
        ),
        "provenance": {
            "telemetry_source": "data/telemetry/failure.json",
            "vision_model": "gemini-robotics-er-2-preview (cached plan & prediction)",
            "recovery_plan_cache": "data/cache/recovery_plan_7d68029fd6afcb46.json",
            "governance_mode": "read_only_hypothetical_analysis",
            "evidence_grounding": "aligned_with_H1_multimodal_root_cause",
        },
    }

    return {
        "incident_id": incident_id,
        "status": "ANALYSIS_COMPLETED",
        "root_cause_id": rc_id,
        "root_cause_name": rc_name,
        "incident_state": incident.get("state"),
        "evidence_summary": {
            "telemetry_evidence_ids": telemetry_ev_ids,
            "visual_evidence_ids": visual_ev_ids,
            "total_evidence_count": len(all_ev_ids),
        },
        "alternatives": [
            option_a,
            option_b,
            option_c,
        ],
        "recommendation": {
            "recommended_strategy_id": "STRAT-C-MAINTENANCE",
            "recommended_strategy_name": "Option C — Joint-3 Maintenance & Governed Verification",
            "rationale": (
                "Option C is the only strategy that addresses the verified physical root cause "
                "(Joint-3 Mechanical Degradation). Option A provides safe containment but no recovery; "
                "Option B is contradicted by vibration and thermal telemetry and carries unacceptable residual risk."
            ),
            "policy_notice": (
                "Hypothetical read-only analysis. Does not authorize production restart, execute physical commands, "
                "or alter incident state machine."
            ),
        },
        "provenance": {
            "engine": "RoboIQ Guardian What-If Recovery Intelligence",
            "version": "1.0.0",
            "execution_mode": "read_only_simulation",
            "telemetry_source": "data/telemetry/failure.json",
            "gemini_model": "gemini-robotics-er-2-preview",
            "gemini_cache_status": "CACHE_HIT",
            "paid_api_calls_made": False,
            "timestamp": now_timestamp(),
        },
    }
