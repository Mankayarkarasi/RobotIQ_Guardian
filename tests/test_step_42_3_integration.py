"""
Bounded API/UI Smoke Test for Step 42.3: Recovery Lab Integration
"""

import sys
sys.path.insert(0, "/app/applet/RoboIQ-Guardian")

from fastapi.testclient import TestClient
from backend.api.main import app, INCIDENTS

client = TestClient(app)

def run_smoke_test():
    print("=" * 65)
    print("RUNNING STEP 42.3 RECOVERY LAB INTEGRATION SMOKE TEST")
    print("=" * 65)

    test_inc = "INC-SMOKE-42-3"
    INCIDENTS[test_inc] = {
        "incident_id": test_inc,
        "state": "RECOVERY_PROPOSED",
        "version": 1,
        "severity": "CRITICAL",
        "root_cause": {"root_cause": {"id": "H1", "name": "Joint-3 Mechanical Degradation"}},
        "audit_log": [],
    }

    # 1. Test Initial Status (Pending Approval)
    get_res = client.get(f"/agent/recovery/approval/{test_inc}")
    assert get_res.status_code == 200
    assert get_res.json()["approval_status"] == "PENDING_APPROVAL"
    print("✓ 1: Initial state is PENDING_APPROVAL (PASS)")

    # 2. Test Execution is Blocked Before Approval
    exec_blocked = client.post(
        "/agent/recovery/execute",
        json={"incident_id": test_inc, "strategy_id": "STRAT-C-MAINTENANCE"},
    )
    assert exec_blocked.status_code == 400
    assert exec_blocked.json()["detail"]["error_code"] == "MISSING_APPROVAL"
    print("✓ 2: Execution blocked prior to human authorization (PASS)")

    # 3. Test Human Operator Approval
    appr_res = client.post(
        "/agent/recovery/approval",
        json={
            "incident_id": test_inc,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "decision": "APPROVED",
            "operator_id": "demo_supervisor",
            "operator_notes": "Recovery Lab operator authorization sign-off.",
        },
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["status"] == "APPROVED"
    assert appr_data["approval_status"] == "APPROVED_FOR_SIMULATION"
    assert appr_data["authorization_scope"] == "SIMULATION_ONLY"
    assert appr_data["governance_mode"] == "DEMO_APPROVAL_ONLY"
    assert appr_data["production_resumption_authorized"] is False
    print("✓ 3: Human approval granted: APPROVED_FOR_SIMULATION (PASS)")

    # 4. Verify Approval Status Updated via GET
    get_appr2 = client.get(f"/agent/recovery/approval/{test_inc}")
    assert get_appr2.status_code == 200
    assert get_appr2.json()["approval_status"] == "APPROVED_FOR_SIMULATION"
    assert get_appr2.json()["active_approval"]["strategy_id"] == "STRAT-C-MAINTENANCE"
    assert get_appr2.json()["audit_chain_summary"]["integrity_valid"] is True
    print("✓ 4: Authoritative GET confirms active approval record & audit integrity (PASS)")

    # 5. Start Approved Simulation Execution
    exec_res = client.post(
        "/agent/recovery/execute",
        json={
            "incident_id": test_inc,
            "strategy_id": "STRAT-C-MAINTENANCE",
            "approval_id": appr_data["approval_id"],
        },
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert exec_data["status"] == "COMPLETED"
    assert exec_data["execution_status"] == "SIMULATION_COMPLETED"
    assert exec_data["total_steps_executed"] == 4
    assert exec_data["safety_restrictions"]["production_resumption_authorized"] is False
    assert exec_data["safety_restrictions"]["physical_recovery_verified"] is False
    print(f"✓ 5: Simulated execution completed ({exec_data['total_steps_executed']} steps trace) (PASS)")

    # 6. Verify Execution Query Status via GET
    get_exec_res = client.get(f"/agent/recovery/execution/{test_inc}")
    assert get_exec_res.status_code == 200
    get_exec_data = get_exec_res.json()
    assert get_exec_data["execution_status"] == "SIMULATION_COMPLETED"
    assert len(get_exec_data["step_execution_trace"]) == 4
    print("✓ 6: GET execution confirms simulation trace & completed status (PASS)")

    # 7. Verify Approval is Now Consumed
    get_appr3 = client.get(f"/agent/recovery/approval/{test_inc}")
    assert get_appr3.status_code == 200
    assert get_appr3.json()["active_approval"]["approval_status"] == "CONSUMED"
    print("✓ 7: Approval record state is properly marked CONSUMED (PASS)")

    print("=" * 65)
    print("STEP 42.3 SMOKE TEST PASSED COMPLETELY!")
    print("=" * 65)

if __name__ == "__main__":
    run_smoke_test()
