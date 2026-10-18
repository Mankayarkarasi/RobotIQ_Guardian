"""
Bounded Offline Verification Suite for Step 43:
- Recovery Verification (VERIFIED_SIMULATION_ONLY, INSUFFICIENT_EVIDENCE, VERIFICATION_FAILED)
- Learning Agent Integration
- Prevention Success Rate (PSR) calculation & N/A rules
- Strict Safety: production resumption unauthorized, zero live AI calls
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
from backend.services.recovery_verification_learning_service import (
    VERIFICATION_REGISTRY,
    LEARNING_REGISTRY,
)

client = TestClient(app)


def run_tests():
    print("=" * 65)
    print("RUNNING STEP 43 VERIFICATION, LEARNING & PSR TESTS")
    print("=" * 65)

    test_inc = "INC-STEP43-VERIF-01"
    INCIDENTS[test_inc] = {
        "incident_id": test_inc,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }

    # Step 1: Human Approval (Step 42.1)
    appr_res = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": test_inc,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "decision": "APPROVED",
            "operator_id": "test_operator",
        },
    )
    assert appr_res.status_code == 200
    approval_id = appr_res.json()["approval_id"]
    print("✓ 1: Step 42.1 Approval granted (PASS)")

    # Step 2: Simulated Execution (Step 42.2)
    exec_res = client.post(
        "/agent/recovery/execute",
        json={
            "incident_id": test_inc,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "approval_id": approval_id,
        },
    )
    assert exec_res.status_code == 200
    assert exec_res.json()["execution_status"] == "SIMULATION_COMPLETED"
    print("✓ 2: Step 42.2 Simulated execution completed (PASS)")

    # Step 3: Verification with Missing Post-Recovery Evidence -> INSUFFICIENT_EVIDENCE
    verif_missing = client.post(
        "/agent/recovery/verify",
        json={"incident_id": test_inc},
    )
    assert verif_missing.status_code == 200
    data_missing = verif_missing.json()
    assert data_missing["verification_status"] == "INSUFFICIENT_EVIDENCE"
    assert data_missing["physical_recovery_verified"] is False
    assert data_missing["production_resumption_authorized"] is False
    assert data_missing["evidence_sufficiency"]["evidence_sufficiency_status"] == "INSUFFICIENT_PHYSICAL_EVIDENCE"
    print("✓ 3: Missing physical evidence returns INSUFFICIENT_EVIDENCE (PASS)")

    # Step 4: Verification with Offline Baseline Evidence -> VERIFIED_SIMULATION_ONLY
    verif_sim = client.post(
        "/agent/recovery/verify",
        json={
            "incident_id": test_inc,
            "post_telemetry_path": "data/telemetry/normal.json",
            "post_video_path": "data/videos/normal.mp4",
        },
    )
    assert verif_sim.status_code == 200
    data_sim = verif_sim.json()
    assert data_sim["verification_status"] == "VERIFIED_SIMULATION_ONLY"
    assert data_sim["physical_recovery_verified"] is False
    assert data_sim["production_resumption_authorized"] is False
    assert "pre_recovery_evidence" in data_sim["evidence_breakdown"]
    assert "simulated_results" in data_sim["evidence_breakdown"]
    assert "post_recovery_evidence" in data_sim["evidence_breakdown"]
    print("✓ 4: Simulation-only verified with production restart blocked (PASS)")

    # Step 5: GET /agent/recovery/verification/{incident_id}
    get_verif = client.get(f"/agent/recovery/verification/{test_inc}")
    assert get_verif.status_code == 200
    assert get_verif.json()["verification_status"] == "VERIFIED_SIMULATION_ONLY"
    print("✓ 5: Authoritative GET verification endpoint (PASS)")

    # Step 6: Learning Agent Integration Record
    learn_res = client.get(f"/agent/learning/{test_inc}")
    assert learn_res.status_code == 200
    learn_data = learn_res.json()
    assert learn_data["incident_id"] == test_inc
    assert learn_data["root_cause_findings"]["root_cause_id"] == "H1"
    assert learn_data["selected_recovery_strategy"]["strategy_id"] == "STRAT-C-MAINTENANCE"
    assert "approval_id" in learn_data["human_approval_reference"]
    assert "execution_id" in learn_data["simulated_execution_result"]
    assert learn_data["verification_outcome"]["verification_status"] == "VERIFIED_SIMULATION_ONLY"
    assert len(learn_data["audit_event_references"]) > 0
    assert learn_data["agent_metadata"]["model_inference_performed"] is False
    print("✓ 6: Learning Agent record captured with full audit traceability & zero live AI (PASS)")

    # Step 7: Prevention Success Rate (PSR) = N/A
    psr_res = client.get("/agent/learning/psr")
    assert psr_res.status_code == 200
    psr_data = psr_res.json()
    assert psr_data["psr"] == "N/A"
    assert psr_data["psr_value"] is None
    assert psr_data["status"] == "N_A"
    assert psr_data["eligible_preventive_interventions"] == 0
    assert psr_data["excluded_simulated_executions_count"] >= 1
    print("✓ 7: PSR correctly returns N/A (simulations strictly excluded) (PASS)")

    # Step 8: Safety & Cryptographic Audit Verification
    chain = get_incident_audit_chain(test_inc)
    verif_chain = verify_audit_chain(chain)
    assert verif_chain["is_valid"] is True
    event_types = [e["event_type"] for e in chain]
    assert "RECOVERY_APPROVAL_GRANTED" in event_types
    assert "SIMULATION_STARTED" in event_types
    assert "SIMULATION_COMPLETED" in event_types
    assert "RECOVERY_VERIFICATION_EVALUATED" in event_types
    print(f"✓ 8: SHA-256 audit chain verified across full lifecycle ({len(chain)} events) (PASS)")

    print("=" * 65)
    print("ALL STEP 43 TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
