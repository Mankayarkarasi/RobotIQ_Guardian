"""
Bounded Offline Verification Suite for Step 42.2: Simulated Recovery Execution
"""

import sys
sys.path.insert(0, "/app/applet/RoboIQ-Guardian")

from fastapi.testclient import TestClient
from backend.api.main import app, INCIDENTS
from backend.services.approval_service import (
    verify_audit_chain,
    get_incident_audit_chain,
    APPROVAL_REGISTRY,
)
from backend.services.recovery_simulation_service import EXECUTION_REGISTRY

client = TestClient(app)


def run_tests():
    print("=" * 65)
    print("RUNNING STEP 42.2 SIMULATED RECOVERY EXECUTION TESTS")
    print("=" * 65)

    # -------------------------------------------------------------
    # Scenario 1: Valid Approval -> Simulated Execution (Option C)
    # -------------------------------------------------------------
    inc_c = "INC-EXEC-TEST-OPT-C"
    INCIDENTS[inc_c] = {
        "incident_id": inc_c,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }

    # Step 1a: Approve Option C
    appr_res = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": inc_c,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "decision": "APPROVED",
            "operator_id": "chief_engineer",
            "operator_notes": "Option C approved for simulated verification sweep.",
        },
    )
    assert appr_res.status_code == 200, f"Approval failed: {appr_res.text}"
    appr_data = appr_res.json()
    approval_id = appr_data["approval_id"]
    assert appr_data["approval_status"] == "APPROVED_FOR_SIMULATION"
    print("✓ 1a: Approved Option C for simulation (PASS)")

    # Step 1b: Execute Simulated Recovery
    exec_res = client.post(
        "/agent/recovery/execute",
        json={
            "incident_id": inc_c,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "approval_id": approval_id,
            "incident_version": appr_data["incident_version"],
        },
    )
    assert exec_res.status_code == 200, f"Execution failed: {exec_res.text}"
    exec_data = exec_res.json()
    assert exec_data["status"] == "COMPLETED"
    assert exec_data["execution_status"] == "SIMULATION_COMPLETED"
    assert exec_data["strategy_id"] == "STRAT-C-MAINTENANCE"
    assert exec_data["authorization_scope"] == "SIMULATION_ONLY"
    assert exec_data["governance_mode"] == "DEMO_APPROVAL_ONLY"
    assert exec_data["total_steps_executed"] == 4

    # Verify safety restrictions
    safety = exec_data["safety_restrictions"]
    assert safety["production_resumption_authorized"] is False
    assert safety["physical_robot_motion_authorized"] is False
    assert safety["physical_recovery_verified"] is False
    assert safety["psr_updated"] is False

    # Verify each step structure
    for step in exec_data["step_execution_trace"]:
        assert "step_id" in step
        assert "start_time" in step
        assert "completed_time" in step
        assert step["simulation_status"] == "COMPLETED"
        assert len(step["evidence_references"]) > 0
        assert len(step["safety_prerequisites"]) > 0
        assert "outcome_and_limitations" in step
        assert "audit_event_id" in step
        assert "entry_hash" in step

    # Verify approval consumed
    reg_entry = APPROVAL_REGISTRY[inc_c]["active"]
    assert reg_entry["approval_status"] == "CONSUMED"
    print("✓ 1b: Valid simulated execution Option C (4 steps, safety restrictions preserved) (PASS)")

    # -------------------------------------------------------------
    # Scenario 2: GET /agent/recovery/execution/{incident_id}
    # -------------------------------------------------------------
    get_exec = client.get(f"/agent/recovery/execution/{inc_c}")
    assert get_exec.status_code == 200
    get_exec_data = get_exec.json()
    assert get_exec_data["execution_status"] == "SIMULATION_COMPLETED"
    assert get_exec_data["strategy_id"] == "STRAT-C-MAINTENANCE"
    assert get_exec_data["total_steps_executed"] == 4
    assert get_exec_data["safety_restrictions"]["production_resumption_authorized"] is False
    print("✓ 2: GET execution status and trace (PASS)")

    # -------------------------------------------------------------
    # Scenario 3: Prevent Duplicate Execution
    # -------------------------------------------------------------
    dup_res = client.post(
        "/agent/recovery/execute",
        json={
            "incident_id": inc_c,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "approval_id": approval_id,
        },
    )
    assert dup_res.status_code == 409, f"Expected 409 for duplicate execution, got {dup_res.status_code}"
    assert dup_res.json()["detail"]["status"] == "BLOCKED"
    print("✓ 3: Duplicate execution blocked with 409 (PASS)")

    # -------------------------------------------------------------
    # Scenario 4: Missing Approval Blocked
    # -------------------------------------------------------------
    inc_no_appr = "INC-NO-APPR-999"
    INCIDENTS[inc_no_appr] = {
        "incident_id": inc_no_appr,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }
    no_appr_res = client.post(
        "/agent/recovery/execute",
        json={
            "incident_id": inc_no_appr,
            "strategy_id": "STRAT-A-CONTAINMENT",
        },
    )
    assert no_appr_res.status_code == 400
    assert no_appr_res.json()["detail"]["error_code"] == "MISSING_APPROVAL"
    print("✓ 4: Execution without approval blocked with 400 MISSING_APPROVAL (PASS)")

    # -------------------------------------------------------------
    # Scenario 5: Rejected Approval Blocked
    # -------------------------------------------------------------
    inc_rej = "INC-REJ-999"
    INCIDENTS[inc_rej] = {
        "incident_id": inc_rej,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }
    client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": inc_rej,
            "strategy_id": "STRAT-B-RECALIBRATION",
            "decision": "REJECTED",
        },
    )
    rej_exec = client.post(
        "/agent/recovery/execute",
        json={
            "incident_id": inc_rej,
            "strategy_id": "STRAT-B-RECALIBRATION",
        },
    )
    assert rej_exec.status_code == 400
    assert rej_exec.json()["detail"]["error_code"] == "APPROVAL_REJECTED"
    print("✓ 5: Execution of rejected approval blocked with 400 APPROVAL_REJECTED (PASS)")

    # -------------------------------------------------------------
    # Scenario 6: Strategy Mismatch Blocked
    # -------------------------------------------------------------
    inc_mismatch = "INC-MISMATCH-999"
    INCIDENTS[inc_mismatch] = {
        "incident_id": inc_mismatch,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }
    client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": inc_mismatch,
            "strategy_id": "STRAT-A-CONTAINMENT",
            "decision": "APPROVED",
        },
    )
    # Approved for A, but attempts to execute C
    mismatch_res = client.post(
        "/agent/recovery/execute",
        json={
            "incident_id": inc_mismatch,
            "strategy_id": "STRAT-C-MAINTENANCE",
        },
    )
    assert mismatch_res.status_code == 400
    assert mismatch_res.json()["detail"]["error_code"] == "STRATEGY_MISMATCH"
    print("✓ 6: Strategy mismatch blocked with 400 STRATEGY_MISMATCH (PASS)")

    # -------------------------------------------------------------
    # Scenario 7: Stale Version Blocked
    # -------------------------------------------------------------
    inc_stale = "INC-STALE-EXEC"
    INCIDENTS[inc_stale] = {
        "incident_id": inc_stale,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }
    client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": inc_stale,
            "strategy_id": "STRAT-A-CONTAINMENT",
            "decision": "APPROVED",
        },
    )
    stale_res = client.post(
        "/agent/recovery/execute",
        json={
            "incident_id": inc_stale,
            "strategy_id": "STRAT-A-CONTAINMENT",
            "incident_version": 999,  # Mismatched version
        },
    )
    assert stale_res.status_code == 409
    assert stale_res.json()["detail"]["error_code"] == "STALE_INCIDENT_VERSION"
    print("✓ 7: Stale incident version blocked with 409 STALE_INCIDENT_VERSION (PASS)")

    # -------------------------------------------------------------
    # Scenario 8: Option A (Containment) Execution
    # -------------------------------------------------------------
    inc_a = "INC-OPT-A-EXEC"
    INCIDENTS[inc_a] = {
        "incident_id": inc_a,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }
    client.post(
        "/agent/recovery/approval",
        json={"incident_id": inc_a, "strategy_id": "STRAT-A-CONTAINMENT", "decision": "APPROVED"},
    )
    exec_a = client.post(
        "/agent/recovery/execute",
        json={"incident_id": inc_a, "strategy_id": "STRAT-A-CONTAINMENT"},
    )
    assert exec_a.status_code == 200
    assert exec_a.json()["total_steps_executed"] == 3
    print("✓ 8: Option A (Containment) executed (3 steps) (PASS)")

    # -------------------------------------------------------------
    # Scenario 9: Option B (Recalibration) Execution
    # -------------------------------------------------------------
    inc_b = "INC-OPT-B-EXEC"
    INCIDENTS[inc_b] = {
        "incident_id": inc_b,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }
    client.post(
        "/agent/recovery/approval",
        json={"incident_id": inc_b, "strategy_id": "STRAT-B-RECALIBRATION", "decision": "APPROVED"},
    )
    exec_b = client.post(
        "/agent/recovery/execute",
        json={"incident_id": inc_b, "strategy_id": "STRAT-B-RECALIBRATION"},
    )
    assert exec_b.status_code == 200
    assert exec_b.json()["total_steps_executed"] == 3
    print("✓ 9: Option B (Recalibration) executed (3 steps) (PASS)")

    # -------------------------------------------------------------
    # Scenario 10: Cryptographic Audit Chain Integrity Check
    # -------------------------------------------------------------
    chain_c = get_incident_audit_chain(inc_c)
    verif = verify_audit_chain(chain_c)
    assert verif["is_valid"] is True, f"Audit chain broken: {verif}"
    # Verify expected event types in chain
    event_types = [e["event_type"] for e in chain_c]
    assert "RECOVERY_APPROVAL_GRANTED" in event_types
    assert "SIMULATION_STARTED" in event_types
    assert "SIMULATED_STEP_EXECUTED" in event_types
    assert "SIMULATION_COMPLETED" in event_types
    print(f"✓ 10a: SHA-256 audit chain verified ({len(chain_c)} events linked) (PASS)")

    # Tamper test blocks execution
    inc_tamper = "INC-TAMPER-TEST"
    INCIDENTS[inc_tamper] = {
        "incident_id": inc_tamper,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }
    client.post(
        "/agent/recovery/approval",
        json={"incident_id": inc_tamper, "strategy_id": "STRAT-A-CONTAINMENT", "decision": "APPROVED"},
    )
    # Intentionally tamper with the audit chain
    chain_tamper = get_incident_audit_chain(inc_tamper)
    chain_tamper[0]["payload_digest"] = "f" * 64
    tamper_exec = client.post(
        "/agent/recovery/execute",
        json={"incident_id": inc_tamper, "strategy_id": "STRAT-A-CONTAINMENT"},
    )
    assert tamper_exec.status_code == 400
    assert tamper_exec.json()["detail"]["error_code"] == "AUDIT_CHAIN_INTEGRITY_COMPROMISED"
    print("✓ 10b: Tampered audit chain blocks execution with 400 AUDIT_CHAIN_INTEGRITY_COMPROMISED (PASS)")

    print("=" * 65)
    print("ALL STEP 42.2 TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
