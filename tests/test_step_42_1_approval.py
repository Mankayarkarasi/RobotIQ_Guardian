"""
Offline verification test suite for Step 42.1 Human Approval & Safety Governance
"""

import sys
from pathlib import Path

# Ensure PYTHONPATH
sys.path.insert(0, "/app/applet/RoboIQ-Guardian")

from fastapi.testclient import TestClient
from backend.api.main import app, INCIDENTS
from backend.services.approval_service import (
    verify_audit_chain,
    get_incident_audit_chain,
    APPROVAL_REGISTRY,
)

client = TestClient(app)

def run_tests():
    print("=" * 60)
    print("RUNNING STEP 42.1 HUMAN APPROVAL & SAFETY GOVERNANCE TESTS")
    print("=" * 60)

    # Setup test incident in INCIDENTS
    test_inc_id = "INC-TEST-42-1"
    INCIDENTS[test_inc_id] = {
        "incident_id": test_inc_id,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {
            "root_cause": {
                "id": "H1",
                "name": "Joint-3 Mechanical Degradation",
            }
        },
        "audit_log": [],
    }

    # 1. Valid Approval (Option C - Maintenance)
    res = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": test_inc_id,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "decision": "APPROVED",
            "operator_id": "operator_chief_01",
            "operator_notes": "Approved for offline simulated validation only.",
        },
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["status"] == "APPROVED"
    assert data["approval_status"] == "APPROVED_FOR_SIMULATION"
    assert data["strategy_id"] == "STRAT-C-MAINTENANCE"
    assert data["authorization_scope"] == "SIMULATION_ONLY"
    assert data["governance_mode"] == "DEMO_APPROVAL_ONLY"
    assert data["production_resumption_authorized"] is False
    assert "audit_event_id" in data
    assert "entry_hash" in data
    assert INCIDENTS[test_inc_id]["state"] == "RECOVERY_APPROVED"
    print("✓ Test 1: Valid approval -> APPROVED_FOR_SIMULATION (PASS)")

    # 2. GET /agent/recovery/approval/{incident_id}
    res_get = client.get(f"/agent/recovery/approval/{test_inc_id}")
    assert res_get.status_code == 200, f"Expected 200, got {res_get.status_code}: {res_get.text}"
    get_data = res_get.json()
    assert get_data["approval_status"] == "APPROVED_FOR_SIMULATION"
    assert get_data["active_approval"]["strategy_id"] == "STRAT-C-MAINTENANCE"
    assert get_data["audit_chain_summary"]["integrity_valid"] is True
    assert get_data["governance_policy"]["authorization_scope"] == "SIMULATION_ONLY"
    print("✓ Test 2: GET approval record and integrity status (PASS)")

    # 3. Duplicate Approval Rejection
    res_dup = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": test_inc_id,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "decision": "APPROVED",
        },
    )
    assert res_dup.status_code == 409, f"Expected 409 Conflict for duplicate, got {res_dup.status_code}"
    assert res_dup.json()["detail"]["status"] == "DUPLICATE_DECISION"
    print("✓ Test 3: Duplicate approval rejected with 409 DUPLICATE_DECISION (PASS)")

    # 4. Superseding Approval (switch to Option A)
    res_super = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": test_inc_id,
            "strategy_id": "STRAT-A-CONTAINMENT",
            "decision": "APPROVED",
            "operator_id": "operator_chief_01",
            "operator_notes": "Switching to containment baseline first.",
        },
    )
    assert res_super.status_code == 200, f"Expected 200, got {res_super.status_code}"
    super_data = res_super.json()
    assert super_data["status"] == "APPROVED"
    assert super_data["strategy_id"] == "STRAT-A-CONTAINMENT"
    assert super_data["supersedes_approval_id"] is not None
    print("✓ Test 4: Superseding prior approval with new strategy (PASS)")

    # 5. Invalid Strategy Rejection
    res_inv = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": test_inc_id,
            "strategy_id": "INVALID-STRATEGY-OVERRIDE",
            "decision": "APPROVED",
        },
    )
    assert res_inv.status_code == 400, f"Expected 400, got {res_inv.status_code}"
    assert res_inv.json()["detail"]["error_code"] == "INVALID_STRATEGY_ID"
    print("✓ Test 5: Invalid strategy ID blocked with 400 (PASS)")

    # 6. Anti-AI Self-Approval Rejection
    res_ai = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": test_inc_id,
            "strategy_id": "STRAT-B-RECALIBRATION",
            "decision": "APPROVED",
            "caller_role": "ai",
            "operator_id": "gemini_robotics_er_agent",
        },
    )
    assert res_ai.status_code == 403, f"Expected 403, got {res_ai.status_code}"
    assert res_ai.json()["detail"]["error_code"] == "AI_SELF_APPROVAL_FORBIDDEN"
    print("✓ Test 6: AI self-approval blocked with 403 (PASS)")

    # 7. Stale Incident Version Rejection
    res_stale = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": test_inc_id,
            "strategy_id": "STRAT-B-RECALIBRATION",
            "decision": "APPROVED",
            "incident_version": 1,  # Version has advanced to 3 by now
        },
    )
    assert res_stale.status_code == 409, f"Expected 409, got {res_stale.status_code}"
    assert res_stale.json()["detail"]["error_code"] == "STALE_INCIDENT_VERSION"
    print("✓ Test 7: Stale incident version blocked with 409 (PASS)")

    # 8. Rejection Decision
    test_inc_id2 = "INC-TEST-42-2"
    INCIDENTS[test_inc_id2] = {
        "incident_id": test_inc_id2,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "HIGH",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }
    res_rej = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": test_inc_id2,
            "strategy_id": "STRAT-B-RECALIBRATION",
            "decision": "REJECTED",
            "operator_notes": "Recalibration alone carries unacceptably high mechanical risk.",
        },
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "REJECTED"
    assert res_rej.json()["approval_status"] == "REJECTED"
    print("✓ Test 8: Operator rejection tracked as REJECTED (PASS)")

    # 9. Cryptographic Audit Chain Integrity & Tamper Detection
    chain = get_incident_audit_chain(test_inc_id)
    verif = verify_audit_chain(chain)
    assert verif["is_valid"] is True, f"Chain invalid: {verif}"
    print(f"✓ Test 9a: SHA-256 audit chain verified ({verif['chain_length']} events) (PASS)")

    # Tamper test on deep copy/element
    original_event = chain[0]["event_type"]
    chain[0]["event_type"] = "MALICIOUS_TAMPER"
    tamper_verif = verify_audit_chain(chain)
    assert tamper_verif["is_valid"] is False
    chain[0]["event_type"] = original_event  # restore
    print("✓ Test 9b: SHA-256 tamper detection verified (PASS)")

    # 10. Existing What-If endpoint compatibility
    res_whatif = client.post("/agent/recovery/what-if", json={"incident_id": test_inc_id})
    assert res_whatif.status_code == 200
    whatif_data = res_whatif.json()
    assert whatif_data["status"] == "ANALYSIS_COMPLETED"
    assert len(whatif_data["alternatives"]) == 3
    print("✓ Test 10: Step 41B What-If endpoint operational (PASS)")

    print("=" * 60)
    print("ALL STEP 42.1 OFFLINE TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
