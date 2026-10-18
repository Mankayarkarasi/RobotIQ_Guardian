"""
RoboIQ Guardian — Simulated Recovery Execution Service (Step 42.2)

Executes a bounded, auditable, human-approved simulated recovery workflow:
- Strictly verifies Step 42.1 approval record (APPROVED_FOR_SIMULATION) before execution.
- Verifies SHA-256 cryptographic audit chain integrity prior to starting simulation.
- Rejects missing, rejected, stale, revoked, mismatched, or already-consumed approvals.
- Prevents duplicate or concurrent executions for an incident.
- Bounded simulated steps for Step 41B recovery alternatives (Options A, B, and C).
- Records step status, timestamps, evidence references, safety prerequisites, limitations, and audit event IDs.
- Tracks execution lifecycle: SIMULATION_RUNNING -> SIMULATION_COMPLETED (or BLOCKED/FAILED).
- Strictly maintains SIMULATION_ONLY and DEMO_APPROVAL_ONLY.
- NEVER performs physical robot actuation, marks physical recovery verified, authorizes production restart,
  or modifies PSR from simulated execution alone.
"""

from datetime import datetime
import time
from typing import Any, Dict, List, Optional
import uuid

from backend.services.approval_service import (
    APPROVAL_REGISTRY,
    get_incident_audit_chain,
    create_audit_event,
    verify_audit_chain,
    canonicalize_strategy_id,
    CANONICAL_STRATEGIES,
)

# In-memory execution store (explicitly non-durable)
EXECUTION_REGISTRY: Dict[str, Dict[str, Any]] = {}


def now_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


BOUNDED_STRATEGY_STEPS: Dict[str, List[Dict[str, Any]]] = {
    "STRAT-A-CONTAINMENT": [
        {
            "step_id": "STEP-A1-SAFE-STOP",
            "step_name": "Emergency Cell Software Stop & Brake Engagement",
            "simulated_action_description": (
                "Simulated command issued to controller to halt manipulator trajectory, "
                "engage Joint-1 through Joint-6 electromagnetic holding brakes, and set commanded joint velocities to 0.0 rad/s."
            ),
            "evidence_references": ["T1", "T2", "T3", "T4", "T5"],
            "safety_prerequisites": [
                "Operations supervisor confirmation of cell emergency pause.",
                "Verify safety curtain and hardware interlock signals active.",
            ],
            "outcome_and_limitations": (
                "Manipulator halted in safe paused pose. Does not physically service or replace degraded Joint-3 drive."
            ),
        },
        {
            "step_id": "STEP-A2-PAYLOAD-STABILIZE",
            "step_name": "Actuator Power De-energization & Workpiece Hold",
            "simulated_action_description": (
                "Simulated de-energization of high-current motor drive inverters while maintaining "
                "gripper fail-safe mechanical clamping to secure workpiece."
            ),
            "evidence_references": ["T4", "T5", "V6", "V7"],
            "safety_prerequisites": [
                "Zero motor velocity verified prior to dropping drive bus voltage.",
                "Gripper pneumatic pressure and holding mechanism verified locked.",
            ],
            "outcome_and_limitations": (
                "Eliminates motor stall overheating (10.2 A -> 0.0 A). Payload held in place; manual cell clearing required."
            ),
        },
        {
            "step_id": "STEP-A3-FORENSIC-FREEZE",
            "step_name": "Telemetry Buffer Lock & Maintenance Dispatch Alert",
            "simulated_action_description": (
                "Snapshot and lock circular high-frequency vibration buffers, controller error logs, and camera clips "
                "for dispatching certified robotics maintenance personnel."
            ),
            "evidence_references": ["T3", "V8", "V9", "V10"],
            "safety_prerequisites": [
                "Incident forensic log channel isolated.",
            ],
            "outcome_and_limitations": (
                "Forensic evidence preserved without alteration. Zero production throughput; physical maintenance dispatch pending."
            ),
        },
    ],
    "STRAT-B-RECALIBRATION": [
        {
            "step_id": "STEP-B1-HOMING-SWEEP",
            "step_name": "Low-Velocity Sensor Homing & Kinematic Zeroing Sweep",
            "simulated_action_description": (
                "Simulated execution of controller software calibration routine: commanded slow-speed (5% velocity) "
                "homing sweep across mechanical limit switches and absolute optical encoders."
            ),
            "evidence_references": ["T2"],
            "safety_prerequisites": [
                "Lead systems engineer formal approval for software calibration sweep.",
                "Collision avoidance clearance verified along entire sweep envelope.",
            ],
            "outcome_and_limitations": (
                "Simulated kinematic homing completed. Cannot repair mechanical backlash or physical bearing spalling."
            ),
        },
        {
            "step_id": "STEP-B2-OFFSET-RESET",
            "step_name": "Kinematic Transform Offset Recalibration",
            "simulated_action_description": (
                "Update Denavit-Hartenberg parameter offsets in software controller based on simulated calibration readings."
            ),
            "evidence_references": ["T2"],
            "safety_prerequisites": [
                "Calibration reference datum verified in software.",
            ],
            "outcome_and_limitations": (
                "Software coordinate alignment reset. Mechanical degradation (high vibration T3: 5.7 mm/s) remains unaddressed."
            ),
        },
        {
            "step_id": "STEP-B3-RESIDUAL-RISK-ASSESSMENT",
            "step_name": "Residual Mechanical Stress & Re-occurrence Check",
            "simulated_action_description": (
                "Evaluate simulated dynamic response under nominal pick-and-place cycle. Detect persistent mechanical anomalies."
            ),
            "evidence_references": ["T3", "T4", "T5"],
            "safety_prerequisites": [
                "Real-time safety threshold triggers armed.",
            ],
            "outcome_and_limitations": (
                "HIGH residual risk flagged: mechanical wear persists; Gemini ER 2 prediction: 15% success score. Production restart blocked."
            ),
        },
    ],
    "STRAT-C-MAINTENANCE": [
        {
            "step_id": "STEP-C1-MAINTENANCE-PARK",
            "step_name": "Traverse to Dedicated Maintenance Inspection Orientation",
            "simulated_action_description": (
                "Simulated commanded traversal along collision-free trajectory to cell service opening, exposing Joint-3 access cover."
            ),
            "evidence_references": ["T1", "T2", "T3"],
            "safety_prerequisites": [
                "Maintenance technician lock-out/tag-out (LOTO) key engaged.",
                "Tooling clear of fixture clamps.",
            ],
            "outcome_and_limitations": (
                "Simulated park pose achieved. Physical technician intervention required for hardware replacement."
            ),
        },
        {
            "step_id": "STEP-C2-SIMULATED-PROCEDURE-DISPATCH",
            "step_name": "Dispatch Gemini ER 7-Step Replacement Checklist",
            "simulated_action_description": (
                "Transmit standardized physical replacement checklist (decouple harmonic drive, inspect gear teeth, mount replacement assembly, torque bolts to spec) to technician terminal."
            ),
            "evidence_references": ["T3", "T4", "T5", "V6", "V7", "V8", "V9", "V10"],
            "safety_prerequisites": [
                "OEM replacement joint assembly verified in stock.",
                "Calibrated torque wrench verified.",
            ],
            "outcome_and_limitations": (
                "Simulated procedure dispatch completed. Does NOT claim physical component replacement has occurred."
            ),
        },
        {
            "step_id": "STEP-C3-KINEMATIC-RECALIBRATION",
            "step_name": "Virtual Multi-Point Kinematic Calibration Sweep",
            "simulated_action_description": (
                "Simulate precision laser-tracker calibration sweep over 12 Cartesian reference points to confirm zero kinematic offset."
            ),
            "evidence_references": ["T2"],
            "safety_prerequisites": [
                "Virtual alignment baseline loaded.",
            ],
            "outcome_and_limitations": (
                "Simulation indicates nominal kinematic convergence. Physical post-maintenance verification still mandatory."
            ),
        },
        {
            "step_id": "STEP-C4-CONTROLLED-TRIAL-SWEEP",
            "step_name": "Simulated Bounded Low-Velocity Trial Cycle",
            "simulated_action_description": (
                "Execute single bounded simulated trial pick-and-place cycle at 20% speed to verify step sequence logic."
            ),
            "evidence_references": ["T1", "T2", "T3", "T4", "T5"],
            "safety_prerequisites": [
                "Cell perimeter safety interlocks engaged.",
                "Zero human presence inside safety cell.",
            ],
            "outcome_and_limitations": (
                "Simulated trial completed. Physical hardware inspection, independent telemetric verification, and supervisor sign-off strictly required before production clearance."
            ),
        },
    ],
}


def execute_simulated_recovery(
    incident: Dict[str, Any],
    request_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate approval, verify cryptographic audit chain, and execute bounded simulated recovery.
    """
    incident_id = incident.get("incident_id", "UNKNOWN_INCIDENT")
    raw_strategy_id = request_data.get("strategy_id")
    req_approval_id = request_data.get("approval_id")
    req_version = request_data.get("incident_version")

    # 1. Strategy Canonicalization & Validation
    canonical_strat = canonicalize_strategy_id(raw_strategy_id, incident=incident)
    if not canonical_strat:
        return {
            "status": "BLOCKED",
            "error_code": "INVALID_STRATEGY_ID",
            "message": f"Unknown or invalid recovery strategy: '{raw_strategy_id}'.",
            "incident_id": incident_id,
            "strategy_id": raw_strategy_id,
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    # 2. Authoritative Approval Validation
    registry_entry = APPROVAL_REGISTRY.get(incident_id, {"active": None, "history": []})
    active_approval = registry_entry.get("active")

    # Fallback to incident['approval'] if not yet populated in registry
    if not active_approval and incident.get("approval"):
        active_approval = incident.get("approval")

    if not active_approval:
        return {
            "status": "BLOCKED",
            "error_code": "MISSING_APPROVAL",
            "message": f"Execution blocked: no human approval record found for incident '{incident_id}'. Human approval is mandatory.",
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    approval_status = active_approval.get("approval_status")
    if approval_status == "REJECTED":
        return {
            "status": "BLOCKED",
            "error_code": "APPROVAL_REJECTED",
            "message": "Execution blocked: human operator rejected the recovery proposal.",
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "approval_id": active_approval.get("approval_id"),
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    if approval_status == "REVOKED":
        return {
            "status": "BLOCKED",
            "error_code": "APPROVAL_REVOKED",
            "message": "Execution blocked: recovery approval has been revoked.",
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "approval_id": active_approval.get("approval_id"),
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    if approval_status == "SUPERSEDED":
        return {
            "status": "BLOCKED",
            "error_code": "APPROVAL_SUPERSEDED",
            "message": "Execution blocked: approval has been superseded by a newer decision.",
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "approval_id": active_approval.get("approval_id"),
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    if approval_status == "CONSUMED":
        return {
            "status": "BLOCKED",
            "error_code": "APPROVAL_ALREADY_CONSUMED",
            "message": "Execution blocked: this approval record has already been consumed by a prior simulation run.",
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "approval_id": active_approval.get("approval_id"),
            "consumed_by_execution_id": active_approval.get("consumed_by_execution_id"),
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    if approval_status != "APPROVED_FOR_SIMULATION" and active_approval.get("status") != "RECOVERY_APPROVED":
        return {
            "status": "BLOCKED",
            "error_code": "NOT_APPROVED_FOR_SIMULATION",
            "message": f"Execution blocked: approval record is in invalid state '{approval_status}'.",
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    # 3. Strategy Mismatch Check
    approved_strat = active_approval.get("strategy_id")
    if approved_strat and approved_strat != canonical_strat:
        return {
            "status": "BLOCKED",
            "error_code": "STRATEGY_MISMATCH",
            "message": (
                f"Execution blocked: approval '{active_approval.get('approval_id')}' was granted for "
                f"strategy '{approved_strat}', but execution requested strategy '{canonical_strat}'."
            ),
            "incident_id": incident_id,
            "approved_strategy_id": approved_strat,
            "requested_strategy_id": canonical_strat,
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    # 4. Approval ID Mismatch Check (if provided)
    if req_approval_id and req_approval_id != active_approval.get("approval_id"):
        return {
            "status": "BLOCKED",
            "error_code": "APPROVAL_ID_MISMATCH",
            "message": (
                f"Execution blocked: requested approval_id '{req_approval_id}' does not match "
                f"active approval_id '{active_approval.get('approval_id')}'."
            ),
            "incident_id": incident_id,
            "requested_approval_id": req_approval_id,
            "active_approval_id": active_approval.get("approval_id"),
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    # 5. Incident Version Stale Check (if provided)
    approved_version = active_approval.get("incident_version")
    if req_version is not None and approved_version is not None and int(req_version) != approved_version:
        return {
            "status": "BLOCKED",
            "error_code": "STALE_INCIDENT_VERSION",
            "message": f"Execution blocked: requested version {req_version} does not match approved version {approved_version}.",
            "incident_id": incident_id,
            "approved_version": approved_version,
            "requested_version": req_version,
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    # 6. Cryptographic Audit Chain Integrity Verification
    chain = get_incident_audit_chain(incident_id)
    audit_verif = verify_audit_chain(chain)
    if not audit_verif.get("is_valid"):
        return {
            "status": "BLOCKED",
            "error_code": "AUDIT_CHAIN_INTEGRITY_COMPROMISED",
            "message": f"Execution blocked: SHA-256 audit chain integrity check failed ({audit_verif.get('reason')}).",
            "incident_id": incident_id,
            "audit_verification": audit_verif,
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    # 7. Concurrency & Duplicate Execution Guard
    existing_execution = EXECUTION_REGISTRY.get(incident_id)
    if existing_execution and existing_execution.get("execution_status") == "SIMULATION_RUNNING":
        return {
            "status": "BLOCKED",
            "error_code": "SIMULATION_ALREADY_RUNNING",
            "message": f"Execution blocked: a simulation is already running for incident '{incident_id}'.",
            "incident_id": incident_id,
            "execution_id": existing_execution.get("execution_id"),
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    if existing_execution and existing_execution.get("approval_id") == active_approval.get("approval_id"):
        return {
            "status": "BLOCKED",
            "error_code": "DUPLICATE_EXECUTION",
            "message": f"Duplicate execution blocked: approval '{active_approval.get('approval_id')}' has already been executed under execution ID '{existing_execution.get('execution_id')}'.",
            "incident_id": incident_id,
            "existing_execution_id": existing_execution.get("existing_execution_id") or existing_execution.get("execution_id"),
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    # 8. Start Simulated Execution
    execution_id = f"EXEC-{uuid.uuid4().hex[:12].upper()}"
    active_approval_id = active_approval.get("approval_id", "APP-UNKNOWN")

    # Record SIMULATION_STARTED audit event
    start_audit_event = create_audit_event(
        incident_id=incident_id,
        event_type="SIMULATION_STARTED",
        actor=f"{active_approval.get('operator_id', 'DEMO_OPERATOR')} (DEMO_APPROVAL_ONLY)",
        decision="EXECUTE_SIMULATION",
        strategy_id=canonical_strat,
        details={
            "execution_id": execution_id,
            "approval_id": active_approval_id,
            "strategy_id": canonical_strat,
            "governance_mode": "DEMO_APPROVAL_ONLY",
            "authorization_scope": "SIMULATION_ONLY",
        },
    )

    # Initialize execution record in SIMULATION_RUNNING state
    exec_record: Dict[str, Any] = {
        "execution_id": execution_id,
        "incident_id": incident_id,
        "strategy_id": canonical_strat,
        "approval_id": active_approval_id,
        "execution_status": "SIMULATION_RUNNING",
        "authorization_scope": "SIMULATION_ONLY",
        "governance_mode": "DEMO_APPROVAL_ONLY",
        "started_at": now_timestamp(),
        "completed_at": None,
        "step_execution_trace": [],
        "audit_event_references": [start_audit_event["event_id"]],
        "safety_restrictions": {
            "production_resumption_authorized": False,
            "physical_robot_motion_authorized": False,
            "physical_recovery_verified": False,
            "psr_updated": False,
            "live_execution_permitted": False,
        },
        "storage_durability": "in-memory-non-durable",
    }
    EXECUTION_REGISTRY[incident_id] = exec_record

    # Update incident state machine
    incident["state"] = "RECOVERING"

    # 9. Execute Bounded Simulation Steps
    raw_steps = BOUNDED_STRATEGY_STEPS.get(canonical_strat, [])
    step_trace: List[Dict[str, Any]] = []

    for step_def in raw_steps:
        step_start = now_timestamp()

        # Step audit event
        step_audit = create_audit_event(
            incident_id=incident_id,
            event_type="SIMULATED_STEP_EXECUTED",
            actor="Simulation Engine (SIMULATION_ONLY)",
            decision="SIMULATION_STEP_SUCCESS",
            strategy_id=canonical_strat,
            details={
                "execution_id": execution_id,
                "step_id": step_def["step_id"],
                "step_name": step_def["step_name"],
                "evidence_references": step_def["evidence_references"],
            },
        )

        step_result = {
            "step_id": step_def["step_id"],
            "step_name": step_def["step_name"],
            "start_time": step_start,
            "completed_time": now_timestamp(),
            "simulation_status": "COMPLETED",
            "simulated_action_description": step_def["simulated_action_description"],
            "evidence_references": step_def["evidence_references"],
            "safety_prerequisites": step_def["safety_prerequisites"],
            "outcome_and_limitations": step_def["outcome_and_limitations"],
            "audit_event_id": step_audit["event_id"],
            "entry_hash": step_audit["entry_hash"],
        }
        step_trace.append(step_result)
        exec_record["audit_event_references"].append(step_audit["event_id"])

    # 10. Complete Simulated Execution
    completion_audit = create_audit_event(
        incident_id=incident_id,
        event_type="SIMULATION_COMPLETED",
        actor="Simulation Engine (SIMULATION_ONLY)",
        decision="SIMULATION_FINISHED",
        strategy_id=canonical_strat,
        details={
            "execution_id": execution_id,
            "steps_count": len(step_trace),
            "production_resumption_authorized": False,
            "physical_recovery_verified": False,
            "note": "SIMULATION_COMPLETED does not authorize production or physical verification.",
        },
    )
    exec_record["audit_event_references"].append(completion_audit["event_id"])

    exec_record["execution_status"] = "SIMULATION_COMPLETED"
    exec_record["completed_at"] = now_timestamp()
    exec_record["step_execution_trace"] = step_trace
    exec_record["current_simulated_step"] = None

    # Consume the approval record so it cannot be run twice
    active_approval["approval_status"] = "CONSUMED"
    active_approval["consumed_by_execution_id"] = execution_id
    active_approval["consumed_at"] = now_timestamp()

    # Update incident state
    incident["recommendation"] = "SIMULATION_COMPLETED_AWAITING_PHYSICAL_VERIFICATION"
    incident["execution"] = exec_record

    return {
        "status": "COMPLETED",
        "execution_id": execution_id,
        "incident_id": incident_id,
        "strategy_id": canonical_strat,
        "approval_id": active_approval_id,
        "execution_status": "SIMULATION_COMPLETED",
        "authorization_scope": "SIMULATION_ONLY",
        "governance_mode": "DEMO_APPROVAL_ONLY",
        "current_simulated_step": None,
        "total_steps_executed": len(step_trace),
        "step_execution_trace": step_trace,
        "safety_restrictions": {
            "production_resumption_authorized": False,
            "physical_robot_motion_authorized": False,
            "physical_recovery_verified": False,
            "psr_updated": False,
            "live_execution_permitted": False,
        },
        "audit_event_references": exec_record["audit_event_references"],
        "storage_durability": "in-memory-non-durable",
        "durability_warning": (
            "Simulation execution trace and audit records are held in volatile memory "
            "and are non-durable across service restarts."
        ),
    }


def get_recovery_execution(
    incident_id: str,
    incident: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Read-only query of authoritative simulated recovery execution status.
    """
    record = EXECUTION_REGISTRY.get(incident_id)
    if not record and incident and incident.get("execution"):
        record = incident.get("execution")

    if not record:
        return {
            "incident_id": incident_id,
            "execution_status": "NO_EXECUTION_RECORD",
            "message": f"No simulation execution record found for incident '{incident_id}'.",
            "authorization_scope": "SIMULATION_ONLY",
            "production_resumption_authorized": False,
        }

    return {
        "incident_id": incident_id,
        "execution_id": record.get("execution_id"),
        "strategy_id": record.get("strategy_id"),
        "approval_id": record.get("approval_id"),
        "execution_status": record.get("execution_status"),
        "authorization_scope": "SIMULATION_ONLY",
        "governance_mode": "DEMO_APPROVAL_ONLY",
        "started_at": record.get("started_at"),
        "completed_at": record.get("completed_at"),
        "total_steps_executed": len(record.get("step_execution_trace", [])),
        "step_execution_trace": record.get("step_execution_trace", []),
        "safety_restrictions": record.get("safety_restrictions", {
            "production_resumption_authorized": False,
            "physical_robot_motion_authorized": False,
            "physical_recovery_verified": False,
            "psr_updated": False,
        }),
        "audit_event_references": record.get("audit_event_references", []),
        "storage_durability": "in-memory-non-durable",
    }
