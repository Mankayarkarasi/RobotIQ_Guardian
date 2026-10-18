"""
RoboIQ Guardian — Human Approval & Safety Governance Service (Step 42.1)

Governs human operator authorization for simulated recovery operations:
- Enforces mandatory human approval prior to simulated recovery execution.
- Prevents autonomous AI self-approval.
- Enforces SIMULATION_ONLY and DEMO_APPROVAL_ONLY governance boundaries.
- Validates incident IDs, recovery strategies, and incident version state.
- Detects and rejects invalid, duplicate, stale, revoked, or superseded decisions.
- Tracks governance states: APPROVED_FOR_SIMULATION, REJECTED, REVOKED, SUPERSEDED.
- Maintains a SHA-256 cryptographic audit chain with event IDs and integrity verification.
- Explicitly labels storage as in-memory non-durable.
"""

from datetime import datetime
import hashlib
import json
from typing import Any, Dict, List, Optional
import uuid

# In-memory governance stores (explicitly non-durable)
APPROVAL_REGISTRY: Dict[str, Dict[str, Any]] = {}
AUDIT_CHAINS: Dict[str, List[Dict[str, Any]]] = {}

# Canonical Step 41B What-If recovery strategies
CANONICAL_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "STRAT-A-CONTAINMENT": {
        "strategy_id": "STRAT-A-CONTAINMENT",
        "strategy_name": "Option A — Safe Containment",
        "option_code": "A",
        "title": "Maintain Safe Stopped State & Cell Containment",
        "risk_level": "LOW",
        "prerequisites": [
            "Operations supervisor formal acknowledgement of production cell shutdown and line rerouting.",
            "Certified robotics maintenance technician dispatch authorization for physical inspection.",
        ],
    },
    "STRAT-B-RECALIBRATION": {
        "strategy_id": "STRAT-B-RECALIBRATION",
        "strategy_name": "Option B — Recalibration Only",
        "option_code": "B",
        "title": "Simulated Sensor Calibration & Kinematic Offset Reset",
        "risk_level": "HIGH",
        "prerequisites": [
            "Lead systems engineer formal approval to execute software calibration sweep.",
            "Explicit risk sign-off accepting unaddressed mechanical degradation and potential imminent hardware damage.",
        ],
    },
    "STRAT-C-MAINTENANCE": {
        "strategy_id": "STRAT-C-MAINTENANCE",
        "strategy_name": "Option C — Joint-3 Maintenance & Governed Verification",
        "option_code": "C",
        "title": "Joint-3 Component Replacement, Recalibration & Verification",
        "risk_level": "MODERATE",
        "prerequisites": [
            "Certified robotics maintenance technician sign-off on physical component replacement and manufacturer torque tightening specifications.",
            "Manufacturing safety engineer authorization for controlled low-speed validation motion.",
        ],
    },
}

# Aliases for strategy resolution
STRATEGY_ALIASES: Dict[str, str] = {
    "a": "STRAT-A-CONTAINMENT",
    "opt-a": "STRAT-A-CONTAINMENT",
    "option a": "STRAT-A-CONTAINMENT",
    "option_a": "STRAT-A-CONTAINMENT",
    "strat-a": "STRAT-A-CONTAINMENT",
    "strat-a-containment": "STRAT-A-CONTAINMENT",
    "containment": "STRAT-A-CONTAINMENT",
    "b": "STRAT-B-RECALIBRATION",
    "opt-b": "STRAT-B-RECALIBRATION",
    "option b": "STRAT-B-RECALIBRATION",
    "option_b": "STRAT-B-RECALIBRATION",
    "strat-b": "STRAT-B-RECALIBRATION",
    "strat-b-recalibration": "STRAT-B-RECALIBRATION",
    "recalibration": "STRAT-B-RECALIBRATION",
    "c": "STRAT-C-MAINTENANCE",
    "opt-c": "STRAT-C-MAINTENANCE",
    "option c": "STRAT-C-MAINTENANCE",
    "option_c": "STRAT-C-MAINTENANCE",
    "strat-c": "STRAT-C-MAINTENANCE",
    "strat-c-maintenance": "STRAT-C-MAINTENANCE",
    "maintenance": "STRAT-C-MAINTENANCE",
}


def now_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def hash_payload(data: Any) -> str:
    """Compute deterministic SHA-256 hash of arbitrary data structures."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def canonicalize_strategy_id(
    strategy_id: str,
    incident: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Resolve given strategy_id against canonical What-If alternatives
    or incident recovery plan. Returns canonical ID or None if invalid.
    """
    if not strategy_id:
        return None

    normalized = str(strategy_id).strip()
    lower = normalized.lower()

    if normalized in CANONICAL_STRATEGIES:
        return normalized

    if lower in STRATEGY_ALIASES:
        return STRATEGY_ALIASES[lower]

    # Check incident recovery plan if present
    if incident and incident.get("recovery_plan"):
        plan_strat = incident["recovery_plan"].get("strategy_id") or incident["recovery_plan"].get("id")
        if plan_strat and (plan_strat == normalized or str(plan_strat).lower() == lower):
            return normalized

    return None


def get_incident_audit_chain(incident_id: str) -> List[Dict[str, Any]]:
    """Retrieve or initialize the audit chain for an incident."""
    if incident_id not in AUDIT_CHAINS:
        AUDIT_CHAINS[incident_id] = []
    return AUDIT_CHAINS[incident_id]


def create_audit_event(
    incident_id: str,
    event_type: str,
    actor: str,
    decision: str,
    strategy_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create and append a cryptographically chained SHA-256 audit entry.
    Each event links to prev_hash, forming a tamper-evident hash chain.
    """
    chain = get_incident_audit_chain(incident_id)
    prev_hash = chain[-1]["entry_hash"] if chain else "0" * 64

    event_id = f"AUD-{uuid.uuid4().hex[:12].upper()}"
    ts = now_timestamp()
    details_dict = details or {}

    payload_for_digest = {
        "incident_id": incident_id,
        "event_id": event_id,
        "event_type": event_type,
        "actor": actor,
        "strategy_id": strategy_id,
        "decision": decision,
        "details": details_dict,
        "timestamp": ts,
    }
    payload_digest = hash_payload(payload_for_digest)

    chain_content = f"{prev_hash}:{ts}:{event_id}:{event_type}:{payload_digest}"
    entry_hash = hashlib.sha256(chain_content.encode("utf-8")).hexdigest()

    entry = {
        "event_id": event_id,
        "incident_id": incident_id,
        "timestamp": ts,
        "event_type": event_type,
        "actor": actor,
        "strategy_id": strategy_id,
        "decision": decision,
        "details": details_dict,
        "payload_digest": payload_digest,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash,
        "storage_durability": "in-memory-non-durable",
    }

    chain.append(entry)
    return entry


def verify_audit_chain(chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Verify the cryptographic integrity of a SHA-256 audit chain.
    Ensures every link's prev_hash, payload digest, and entry_hash match.
    """
    if not chain:
        return {
            "is_valid": True,
            "chain_length": 0,
            "message": "Audit chain is empty.",
            "head_hash": "0" * 64,
        }

    expected_prev = "0" * 64
    for idx, entry in enumerate(chain):
        # 1. Verify prev_hash link
        if entry.get("prev_hash") != expected_prev:
            return {
                "is_valid": False,
                "chain_length": len(chain),
                "broken_index": idx,
                "broken_event_id": entry.get("event_id"),
                "reason": (
                    f"prev_hash mismatch at index {idx}: expected {expected_prev}, "
                    f"got {entry.get('prev_hash')}"
                ),
            }

        # 2. Recompute payload digest
        payload_for_digest = {
            "incident_id": entry.get("incident_id"),
            "event_id": entry.get("event_id"),
            "event_type": entry.get("event_type"),
            "actor": entry.get("actor"),
            "strategy_id": entry.get("strategy_id"),
            "decision": entry.get("decision"),
            "details": entry.get("details", {}),
            "timestamp": entry.get("timestamp"),
        }
        recomputed_payload_digest = hash_payload(payload_for_digest)
        if recomputed_payload_digest != entry.get("payload_digest"):
            return {
                "is_valid": False,
                "chain_length": len(chain),
                "broken_index": idx,
                "broken_event_id": entry.get("event_id"),
                "reason": f"Payload digest mismatch at index {idx}",
            }

        # 3. Recompute entry hash
        chain_content = (
            f"{expected_prev}:{entry.get('timestamp')}:{entry.get('event_id')}:"
            f"{entry.get('event_type')}:{recomputed_payload_digest}"
        )
        recomputed_entry_hash = hashlib.sha256(chain_content.encode("utf-8")).hexdigest()
        if recomputed_entry_hash != entry.get("entry_hash"):
            return {
                "is_valid": False,
                "chain_length": len(chain),
                "broken_index": idx,
                "broken_event_id": entry.get("event_id"),
                "reason": f"Entry hash mismatch at index {idx}",
            }

        expected_prev = entry.get("entry_hash")

    return {
        "is_valid": True,
        "chain_length": len(chain),
        "head_hash": expected_prev,
        "message": "Cryptographic audit chain verified successfully (SHA-256 tamper-evident).",
    }


def process_recovery_approval(
    incident: Dict[str, Any],
    request_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate and apply a human approval decision for an incident recovery strategy.

    Enforces:
    1. Incident ID & strategy ID validity.
    2. Incident state and version verification.
    3. Anti-AI self-approval guardrail.
    4. SIMULATION_ONLY and DEMO_APPROVAL_ONLY governance constraints.
    5. Duplicate, stale, revoked, and superseded decision handling.
    6. SHA-256 chained audit recording.
    """
    incident_id = incident.get("incident_id", "UNKNOWN_INCIDENT")
    raw_strategy_id = request_data.get("strategy_id")
    raw_decision = (
        request_data.get("decision")
        or ("APPROVED" if request_data.get("approved") is True else "REJECTED" if request_data.get("approved") is False else "APPROVED")
    )
    decision = str(raw_decision).strip().upper()
    if decision in ("TRUE", "APPROVE"):
        decision = "APPROVED"
    elif decision in ("FALSE", "REJECT"):
        decision = "REJECTED"

    caller_role = (request_data.get("caller_role") or "").strip().lower()
    operator_id = (request_data.get("operator_id") or "").strip()

    # 1. Anti-AI self-approval guardrail
    ai_role_markers = {"ai", "agent", "gemini", "autonomous", "system_auto", "bot", "llm"}
    if caller_role in ai_role_markers or any(m in operator_id.lower() for m in ["gemini", "autonomous", "ai_bot"]):
        return {
            "status": "BLOCKED",
            "error_code": "AI_SELF_APPROVAL_FORBIDDEN",
            "message": (
                "Safety Policy Violation: Human operator approval is mandatory for recovery. "
                "Autonomous agents and AI systems are strictly prohibited from self-approving recovery plans."
            ),
            "incident_id": incident_id,
            "strategy_id": raw_strategy_id,
            "governance_mode": "DEMO_APPROVAL_ONLY",
            "authorization_scope": "SIMULATION_ONLY",
        }

    # 2. Strategy validation
    canonical_strat = canonicalize_strategy_id(raw_strategy_id, incident=incident)
    if not canonical_strat:
        return {
            "status": "BLOCKED",
            "error_code": "INVALID_STRATEGY_ID",
            "message": (
                f"Unknown or invalid recovery strategy: '{raw_strategy_id}'. "
                f"Supported Step 41B strategies: {list(CANONICAL_STRATEGIES.keys())}"
            ),
            "incident_id": incident_id,
            "strategy_id": raw_strategy_id,
            "governance_mode": "DEMO_APPROVAL_ONLY",
            "authorization_scope": "SIMULATION_ONLY",
        }

    strategy_meta = CANONICAL_STRATEGIES.get(canonical_strat, {
        "strategy_id": canonical_strat,
        "strategy_name": canonical_strat,
        "risk_level": "MODERATE",
        "prerequisites": [],
    })

    # 3. Incident version validation (prevent stale approvals)
    current_version = incident.get("version", 1)
    req_version = request_data.get("incident_version")
    if req_version is not None and int(req_version) != current_version:
        return {
            "status": "BLOCKED",
            "error_code": "STALE_INCIDENT_VERSION",
            "message": (
                f"Approval rejected: requested incident version {req_version} is stale. "
                f"Current incident version is {current_version}."
            ),
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "current_incident_version": current_version,
            "requested_incident_version": req_version,
        }

    # 4. Incident state validation
    incident_state = incident.get("state", "UNKNOWN")
    allowed_states = {
        "RECOVERY_PROPOSED",
        "ROOT_CAUSE_IDENTIFIED",
        "INVESTIGATING",
        "RECOVERY_APPROVED",
    }
    if incident_state not in allowed_states:
        return {
            "status": "BLOCKED",
            "error_code": "INVALID_INCIDENT_STATE",
            "message": (
                f"Incident '{incident_id}' is in state '{incident_state}', which cannot "
                "accept recovery approval decisions."
            ),
            "incident_id": incident_id,
            "current_state": incident_state,
        }

    # 5. Check existing approval records in registry
    registry_entry = APPROVAL_REGISTRY.get(incident_id, {"active": None, "history": []})
    active_approval = registry_entry.get("active")

    # Handle REVOCATION decision
    if decision == "REVOKED":
        if not active_approval or active_approval.get("approval_status") != "APPROVED_FOR_SIMULATION":
            return {
                "status": "BLOCKED",
                "error_code": "NOTHING_TO_REVOKE",
                "message": f"No active simulation approval found to revoke for incident '{incident_id}'.",
                "incident_id": incident_id,
            }

        active_approval["approval_status"] = "REVOKED"
        active_approval["revoked_at"] = now_timestamp()
        active_approval["revocation_reason"] = request_data.get("operator_notes") or "Operator requested revocation."

        # Audit event
        audit_event = create_audit_event(
            incident_id=incident_id,
            event_type="RECOVERY_APPROVAL_REVOKED",
            actor=f"{operator_id or 'DEMO_OPERATOR'} (DEMO_APPROVAL_ONLY)",
            decision="REVOKED",
            strategy_id=canonical_strat,
            details={
                "previous_approval_id": active_approval.get("approval_id"),
                "reason": active_approval["revocation_reason"],
            },
        )

        incident["state"] = "RECOVERY_PROPOSED"
        incident["recommendation"] = "RECOVERY_APPROVAL_REVOKED"
        incident["approval"] = active_approval
        registry_entry["history"].append(dict(active_approval))
        registry_entry["active"] = None
        APPROVAL_REGISTRY[incident_id] = registry_entry

        return {
            "status": "REVOKED",
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "approval_status": "REVOKED",
            "audit_event_id": audit_event["event_id"],
            "entry_hash": audit_event["entry_hash"],
            "authorization_scope": "SIMULATION_ONLY",
            "governance_mode": "DEMO_APPROVAL_ONLY",
            "production_resumption_authorized": False,
            "storage_durability": "in-memory-non-durable",
        }

    # Handle REJECTION decision
    if decision == "REJECTED":
        approval_id = f"APP-{uuid.uuid4().hex[:12].upper()}"
        approval_record = {
            "approval_id": approval_id,
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "strategy_name": strategy_meta.get("strategy_name"),
            "approval_status": "REJECTED",
            "approved": False,
            "decision": "REJECTED",
            "incident_version": current_version,
            "operator_id": operator_id or "DEMO_OPERATOR_UNAUTHENTICATED",
            "operator_role": "DEMO_OPERATOR",
            "operator_notes": request_data.get("operator_notes") or "Operator rejected recovery strategy.",
            "authorization_scope": "SIMULATION_ONLY",
            "governance_mode": "DEMO_APPROVAL_ONLY",
            "production_resumption_authorized": False,
            "physical_robot_motion_authorized": False,
            "storage_durability": "in-memory-non-durable",
            "created_at": now_timestamp(),
        }

        audit_event = create_audit_event(
            incident_id=incident_id,
            event_type="RECOVERY_APPROVAL_REJECTED",
            actor=f"{approval_record['operator_id']} (DEMO_APPROVAL_ONLY)",
            decision="REJECTED",
            strategy_id=canonical_strat,
            details={
                "approval_id": approval_id,
                "notes": approval_record["operator_notes"],
                "strategy_name": strategy_meta.get("strategy_name"),
            },
        )
        approval_record["audit_event_id"] = audit_event["event_id"]
        approval_record["entry_hash"] = audit_event["entry_hash"]

        if active_approval:
            active_approval["approval_status"] = "SUPERSEDED"
            registry_entry["history"].append(dict(active_approval))

        registry_entry["active"] = approval_record
        registry_entry["history"].append(dict(approval_record))
        APPROVAL_REGISTRY[incident_id] = registry_entry

        incident["approval"] = approval_record
        incident["recommendation"] = "RECOVERY_REJECTED_BY_OPERATOR"

        return {
            "status": "REJECTED",
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "approval_id": approval_id,
            "approval_status": "REJECTED",
            "audit_event_id": audit_event["event_id"],
            "entry_hash": audit_event["entry_hash"],
            "authorization_scope": "SIMULATION_ONLY",
            "governance_mode": "DEMO_APPROVAL_ONLY",
            "production_resumption_authorized": False,
            "storage_durability": "in-memory-non-durable",
            "message": "Recovery proposal rejected by operator.",
        }

    # Handle APPROVAL decision
    if decision == "APPROVED":
        # Check duplicate decision
        if (
            active_approval
            and active_approval.get("approval_status") == "APPROVED_FOR_SIMULATION"
            and active_approval.get("strategy_id") == canonical_strat
        ):
            return {
                "status": "DUPLICATE_DECISION",
                "message": (
                    f"Strategy '{canonical_strat}' is already approved for simulation "
                    f"under approval ID '{active_approval.get('approval_id')}'."
                ),
                "incident_id": incident_id,
                "strategy_id": canonical_strat,
                "approval_id": active_approval.get("approval_id"),
                "approval_status": "APPROVED_FOR_SIMULATION",
                "audit_event_id": active_approval.get("audit_event_id"),
                "entry_hash": active_approval.get("entry_hash"),
                "authorization_scope": "SIMULATION_ONLY",
                "governance_mode": "DEMO_APPROVAL_ONLY",
                "production_resumption_authorized": False,
                "storage_durability": "in-memory-non-durable",
            }

        # Check if superseding a prior active approval
        superseded_id = None
        if active_approval and active_approval.get("approval_status") == "APPROVED_FOR_SIMULATION":
            superseded_id = active_approval.get("approval_id")
            active_approval["approval_status"] = "SUPERSEDED"
            active_approval["superseded_at"] = now_timestamp()
            registry_entry["history"].append(dict(active_approval))

            # Audit event for superseded
            create_audit_event(
                incident_id=incident_id,
                event_type="RECOVERY_APPROVAL_SUPERSEDED",
                actor=f"{operator_id or 'DEMO_OPERATOR'} (DEMO_APPROVAL_ONLY)",
                decision="SUPERSEDED",
                strategy_id=active_approval.get("strategy_id"),
                details={
                    "superseded_approval_id": superseded_id,
                    "superseded_strategy_id": active_approval.get("strategy_id"),
                    "new_strategy_id": canonical_strat,
                },
            )

        # Build fresh approval record
        approval_id = f"APP-{uuid.uuid4().hex[:12].upper()}"
        effective_operator = operator_id or "DEMO_OPERATOR_UNAUTHENTICATED"

        approval_record = {
            "approval_id": approval_id,
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "strategy_name": strategy_meta.get("strategy_name"),
            "approval_status": "APPROVED_FOR_SIMULATION",
            "approved": True,
            "decision": "APPROVED",
            "incident_version": current_version,
            "operator_id": effective_operator,
            "operator_role": "DEMO_OPERATOR",
            "operator_notes": request_data.get("operator_notes") or "Approved for offline simulation only.",
            "authorization_scope": "SIMULATION_ONLY",
            "governance_mode": "DEMO_APPROVAL_ONLY",
            "production_resumption_authorized": False,
            "physical_robot_motion_authorized": False,
            "live_execution_permitted": False,
            "storage_durability": "in-memory-non-durable",
            "prerequisites": strategy_meta.get("prerequisites", []),
            "created_at": now_timestamp(),
            "supersedes_approval_id": superseded_id,
        }

        # Cryptographic audit event
        audit_event = create_audit_event(
            incident_id=incident_id,
            event_type="RECOVERY_APPROVAL_GRANTED",
            actor=f"{effective_operator} (DEMO_APPROVAL_ONLY)",
            decision="APPROVED",
            strategy_id=canonical_strat,
            details={
                "approval_id": approval_id,
                "strategy_id": canonical_strat,
                "strategy_name": strategy_meta.get("strategy_name"),
                "authorization_scope": "SIMULATION_ONLY",
                "governance_mode": "DEMO_APPROVAL_ONLY",
                "supersedes_approval_id": superseded_id,
                "incident_version": current_version,
                "prerequisites_acknowledged": strategy_meta.get("prerequisites", []),
            },
        )
        approval_record["audit_event_id"] = audit_event["event_id"]
        approval_record["entry_hash"] = audit_event["entry_hash"]

        registry_entry["active"] = approval_record
        registry_entry["history"].append(dict(approval_record))
        APPROVAL_REGISTRY[incident_id] = registry_entry

        # Update incident in-memory state
        incident["approval"] = approval_record
        incident["state"] = "RECOVERY_APPROVED"
        incident["recommendation"] = "APPROVED_FOR_SIMULATION_ONLY"
        incident["version"] = current_version + 1

        return {
            "status": "APPROVED",
            "incident_id": incident_id,
            "strategy_id": canonical_strat,
            "strategy_name": strategy_meta.get("strategy_name"),
            "approval_id": approval_id,
            "approval_status": "APPROVED_FOR_SIMULATION",
            "incident_version": current_version,
            "audit_event_id": audit_event["event_id"],
            "entry_hash": audit_event["entry_hash"],
            "prev_hash": audit_event["prev_hash"],
            "authorization_scope": "SIMULATION_ONLY",
            "governance_mode": "DEMO_APPROVAL_ONLY",
            "production_resumption_authorized": False,
            "physical_robot_motion_authorized": False,
            "storage_durability": "in-memory-non-durable",
            "durability_warning": (
                "Approval records and cryptographic audit trail are stored in volatile memory "
                "and are non-durable across service restarts."
            ),
            "supersedes_approval_id": superseded_id,
        }

    return {
        "status": "BLOCKED",
        "error_code": "UNKNOWN_DECISION",
        "message": f"Unsupported approval decision '{raw_decision}'. Must be APPROVED, REJECTED, or REVOKED.",
        "incident_id": incident_id,
    }


def get_recovery_approval(
    incident_id: str,
    incident: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Query authoritative human approval record, history, and audit chain integrity.
    """
    registry_entry = APPROVAL_REGISTRY.get(incident_id, {"active": None, "history": []})
    active = registry_entry.get("active")
    history = registry_entry.get("history", [])

    # If registry has no entry but incident has legacy approval dict
    if not active and incident and incident.get("approval"):
        legacy = incident.get("approval")
        if legacy.get("status") == "RECOVERY_APPROVED" or legacy.get("approved") is True:
            active = {
                "approval_id": "APP-LEGACY-001",
                "incident_id": incident_id,
                "strategy_id": "STRAT-C-MAINTENANCE",
                "strategy_name": "Option C — Joint-3 Maintenance & Governed Verification",
                "approval_status": "APPROVED_FOR_SIMULATION",
                "approved": True,
                "decision": "APPROVED",
                "authorization_scope": "SIMULATION_ONLY",
                "governance_mode": "DEMO_APPROVAL_ONLY",
                "production_resumption_authorized": False,
                "storage_durability": "in-memory-non-durable",
                "created_at": incident.get("updated_at") or now_timestamp(),
            }

    chain = get_incident_audit_chain(incident_id)
    verification = verify_audit_chain(chain)

    return {
        "incident_id": incident_id,
        "approval_status": active.get("approval_status") if active else "PENDING_APPROVAL",
        "active_approval": active,
        "history_count": len(history),
        "history": history,
        "audit_chain_summary": {
            "total_events": len(chain),
            "head_hash": verification.get("head_hash"),
            "integrity_valid": verification.get("is_valid", True),
            "verification_message": verification.get("message"),
        },
        "governance_policy": {
            "authorization_scope": "SIMULATION_ONLY",
            "governance_mode": "DEMO_APPROVAL_ONLY",
            "production_resumption_authorized": False,
            "physical_robot_motion_authorized": False,
            "ai_self_approval_allowed": False,
            "storage_durability": "in-memory-non-durable",
            "durability_warning": (
                "Audit trail and approval records are stored in volatile memory and do not "
                "persist across server restarts."
            ),
        },
    }


# =========================================================
# BACKWARDS COMPATIBILITY FOR PREVIOUS STEP CALLERS
# =========================================================

def approve_recovery(
    recovery_plan: Dict[str, Any],
    approved: bool,
) -> Dict[str, Any]:
    """
    Legacy approval wrapper preserved for backward compatibility.
    """
    if recovery_plan.get("status") != "RECOVERY_PROPOSED":
        return {
            "status": "INVALID_STATE",
            "message": "Recovery plan is not in proposed state.",
        }

    actions = recovery_plan.get("actions")
    if actions is None:
        actions = recovery_plan.get("recommended_actions", [])

    if approved:
        return {
            "status": "RECOVERY_APPROVED",
            "approved": True,
            "root_cause": recovery_plan.get("root_cause"),
            "risk_level": recovery_plan.get("risk_level"),
            "actions": actions,
            "governance_mode": "DEMO_APPROVAL_ONLY",
            "authorization_scope": "SIMULATION_ONLY",
            "storage_durability": "in-memory-non-durable",
        }

    return {
        "status": "RECOVERY_REJECTED",
        "approved": False,
        "root_cause": recovery_plan.get("root_cause"),
        "risk_level": recovery_plan.get("risk_level"),
        "actions": [],
        "governance_mode": "DEMO_APPROVAL_ONLY",
        "authorization_scope": "SIMULATION_ONLY",
        "storage_durability": "in-memory-non-durable",
    }


if __name__ == "__main__":
    print("--- Testing RoboIQ Guardian Approval Service ---")
    mock_incident = {
        "incident_id": "INC-TEST-001",
        "state": "RECOVERY_PROPOSED",
        "version": 1,
    }

    # Test 1: Valid Approval
    res1 = process_recovery_approval(
        mock_incident,
        {
            "strategy_id": "STRAT-C-MAINTENANCE",
            "decision": "APPROVED",
            "operator_id": "operator_42",
        },
    )
    print("Test 1 (Valid Approval):", res1["status"], res1["approval_status"])
    assert res1["status"] == "APPROVED"
    assert res1["approval_status"] == "APPROVED_FOR_SIMULATION"
    assert res1["authorization_scope"] == "SIMULATION_ONLY"

    # Test 2: Duplicate Approval
    res2 = process_recovery_approval(
        mock_incident,
        {
            "strategy_id": "STRAT-C-MAINTENANCE",
            "decision": "APPROVED",
        },
    )
    print("Test 2 (Duplicate):", res2["status"])
    assert res2["status"] == "DUPLICATE_DECISION"

    # Test 3: Superseding Approval with Option A
    res3 = process_recovery_approval(
        mock_incident,
        {
            "strategy_id": "STRAT-A-CONTAINMENT",
            "decision": "APPROVED",
        },
    )
    print("Test 3 (Supersede):", res3["status"], "Supersedes:", res3.get("supersedes_approval_id"))
    assert res3["status"] == "APPROVED"
    assert res3.get("supersedes_approval_id") is not None

    # Test 4: AI self-approval blocked
    res4 = process_recovery_approval(
        mock_incident,
        {
            "strategy_id": "STRAT-B-RECALIBRATION",
            "caller_role": "ai",
        },
    )
    print("Test 4 (AI Blocked):", res4["status"], res4.get("error_code"))
    assert res4["status"] == "BLOCKED"
    assert res4.get("error_code") == "AI_SELF_APPROVAL_FORBIDDEN"

    # Test 5: Invalid Strategy
    res5 = process_recovery_approval(
        mock_incident,
        {
            "strategy_id": "STRAT-INVALID-999",
            "decision": "APPROVED",
        },
    )
    print("Test 5 (Invalid Strategy):", res5["status"], res5.get("error_code"))
    assert res5["status"] == "BLOCKED"
    assert res5.get("error_code") == "INVALID_STRATEGY_ID"

    # Test 6: Audit Chain Integrity
    chain = get_incident_audit_chain("INC-TEST-001")
    verif = verify_audit_chain(chain)
    print("Test 6 (Audit Integrity):", verif["is_valid"], "Events:", verif["chain_length"])
    assert verif["is_valid"] is True
    assert verif["chain_length"] >= 3

    # Tamper test
    chain[0]["details"]["tampered"] = True
    tamper_verif = verify_audit_chain(chain)
    print("Test 7 (Tamper Detection):", not tamper_verif["is_valid"], tamper_verif.get("reason"))
    assert tamper_verif["is_valid"] is False

    print("ALL TESTS PASSED SUCCESSFULLY!")