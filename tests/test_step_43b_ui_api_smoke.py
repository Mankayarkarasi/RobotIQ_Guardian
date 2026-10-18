"""
RoboIQ Guardian — Step 43B Verification & Learning UI / API Smoke Test

Verifies:
1. POST /agent/recovery/verify with baseline evidence -> VERIFIED_SIMULATION_ONLY
2. GET /agent/recovery/verification/{incident_id}
3. GET /agent/learning/{incident_id}
4. GET /agent/learning/records
5. GET /agent/learning/psr returns 'N/A' (simulations strictly excluded)
6. Zero live AI model calls (model_inference_performed: False)
7. Production resumption remains strictly prohibited
"""

import sys
sys.path.insert(0, "/app/applet/RoboIQ-Guardian")

from fastapi.testclient import TestClient
from backend.api.main import app, INCIDENTS

client = TestClient(app)


def test_step_43b_full_lifecycle():
    print("=" * 65)
    print("RUNNING STEP 43B UI / API SMOKE TEST")
    print("=" * 65)

    test_id = "INC-STEP43B-UI-SMOKE"
    INCIDENTS[test_id] = {
        "incident_id": test_id,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }

    # 1. Human Approval for Simulation (Step 42.1)
    appr_res = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": test_id,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "decision": "APPROVED",
            "operator_id": "operator_43b",
        },
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["status"] == "APPROVED"
    print("✓ 1: Human Approval Granted for Simulation (PASS)")

    # 2. Governed Simulation Execution (Step 42.2)
    exec_res = client.post(
        "/agent/recovery/execute",
        json={
            "incident_id": test_id,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "approval_id": appr_data["approval_id"],
        },
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["execution_status"] == "SIMULATION_COMPLETED"
    assert exec_data["safety_restrictions"]["production_resumption_authorized"] is False
    print("✓ 2: Governed Simulation Completed with Safety Restrictions Preserved (PASS)")

    # 3. Independent Recovery Verification (Step 43)
    verif_res = client.post(
        "/agent/recovery/verify",
        json={
            "incident_id": test_id,
            "post_telemetry_path": "data/telemetry/normal.json",
            "post_video_path": "data/videos/normal.mp4",
        },
    )
    assert verif_res.status_code == 200
    verif_data = verif_res.json()
    assert verif_data["verification_status"] == "VERIFIED_SIMULATION_ONLY"
    assert verif_data["physical_recovery_verified"] is False
    assert verif_data["production_resumption_authorized"] is False
    assert len(verif_data["unresolved_risks"]) > 0
    assert "evidence_sufficiency" in verif_data
    assert "evidence_breakdown" in verif_data
    print("✓ 3: Recovery Verification Evaluated (VERIFIED_SIMULATION_ONLY, Resumption Prohibited) (PASS)")

    # 4. GET /agent/recovery/verification/{incident_id}
    get_verif_res = client.get(f"/agent/recovery/verification/{test_id}")
    assert get_verif_res.status_code == 200
    assert get_verif_res.json()["verification_id"] == verif_data["verification_id"]
    print("✓ 4: GET Verification Record matches authoritative evaluation (PASS)")

    # 5. GET /agent/learning/{incident_id}
    learn_res = client.get(f"/agent/learning/{test_id}")
    assert learn_res.status_code == 200
    learn_data = learn_res.json()
    assert learn_data["incident_id"] == test_id
    assert learn_data["root_cause_findings"]["root_cause_id"] == "H1"
    assert learn_data["selected_recovery_strategy"]["strategy_id"] == "STRAT-C-MAINTENANCE"
    assert learn_data["human_approval_reference"]["approval_id"] == appr_data["approval_id"]
    assert learn_data["simulated_execution_result"]["execution_id"] == exec_data["execution_id"]
    assert learn_data["verification_outcome"]["verification_status"] == "VERIFIED_SIMULATION_ONLY"
    assert learn_data["agent_metadata"]["model_inference_performed"] is False
    print("✓ 5: Learning Agent Record accurately captured closed-loop findings & zero live AI (PASS)")

    # 6. GET /agent/learning/records
    records_res = client.get("/agent/learning/records")
    assert records_res.status_code == 200
    records_data = records_res.json()
    assert records_data["count"] >= 1
    assert any(r["incident_id"] == test_id for r in records_data["records"])
    print(f"✓ 6: GET Learning Records returned {records_data['count']} closed-loop records (PASS)")

    # 7. GET /agent/learning/psr
    psr_res = client.get("/agent/learning/psr")
    assert psr_res.status_code == 200
    psr_data = psr_res.json()
    assert psr_data["status"] == "N_A"
    assert psr_data["psr"] == "N/A"
    assert psr_data["psr_value"] is None
    assert psr_data["eligible_preventive_interventions"] == 0
    assert psr_data["excluded_simulated_executions_count"] >= 1
    print("✓ 7: Prevention Success Rate (PSR) strictly evaluates to N/A (simulations excluded) (PASS)")

    print("=" * 65)
    print("ALL STEP 43B SMOKE TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    test_step_43b_full_lifecycle()
