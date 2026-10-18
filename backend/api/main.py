"""
RoboIQ Guardian - FastAPI Backend

RoboIQ Guardian is an embodied manufacturing recovery
intelligence platform.

Gemini Robotics ER 2 acts as the embodied reasoning brain.

The Guardian backend provides:
- telemetry analysis
- multimodal evidence correlation
- hypothesis ranking
- root-cause decision
- governed recovery recommendation
- recovery success assessment
- human approval
- simulated recovery execution
- Gemini ER progress verification
- final recovery verification
- incident lifecycle management
- UI-support APIs
"""

import json



from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4

from backend.services.adk_offline_workflow import run_guardian_workflow

from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import (
    CORSMiddleware
)

from pydantic import BaseModel


# =========================================================
# SERVICE IMPORTS
# =========================================================

from backend.services.telemetry_analyzer import (
    analyze_telemetry
)

from backend.services.robotics_er_service import (
    analyze_video
)

from backend.services.evidence_engine import (
    build_evidence
)

from backend.services.hypothesis_engine import (
    get_hypotheses
)

from backend.services.hypothesis_scoring import (
    score_hypotheses
)

from backend.services.root_cause_service import (
    select_root_cause
)

from backend.services.recovery_service import (
    generate_recovery_plan
)

from backend.services.recovery_prediction_service import (
    predict_recovery_success
)

from backend.services.approval_service import (
    approve_recovery,
    process_recovery_approval,
    get_recovery_approval,
    create_audit_event,
    verify_audit_chain,
)

from backend.services.recovery_executor import (
    execute_recovery,
    execute_simulated_recovery,
    get_recovery_execution,
)

from backend.services.recovery_verifier import (
    verify_recovery
)

from backend.services.recovery_verification_learning_service import (
    evaluate_recovery_verification,
    get_recovery_verification,
    record_learning_outcome,
    get_learning_record,
    calculate_psr,
    LEARNING_REGISTRY,
)

from backend.services.incident_state_machine import (
    transition_state
)

try:
    from backend.services.adk_coordinator import orchestrate_investigation
    ADK_IMPORT_ERROR = None
except ImportError as exc:
    orchestrate_investigation = None
    ADK_IMPORT_ERROR = str(exc)

from backend.services.what_if_service import (
    evaluate_what_if_recovery
)
from backend.services.adk_tools import (
    _load_incident_or_fallback
)


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="RoboIQ Guardian API",
    version="1.0.0",
    description=(
        "Autonomous Embodied Manufacturing Failure "
        "Investigation & Recovery Intelligence"
    )
)


# =========================================================
# CORS
# =========================================================
#
# Required for React/Vite frontend.
#
# For hackathon PoC, allow all origins.
# Restrict this in a production deployment.
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

THRESHOLDS_FILE = (
    BASE_DIR
    / "data"
    / "config"
    / "thresholds.json"
)


# =========================================================
# INCIDENT STORE
# =========================================================
#
# In-memory store for hackathon PoC.
#
# Future:
# BigQuery / Firestore / Cloud SQL / PostgreSQL
# =========================================================

INCIDENTS: Dict[str, Dict] = {}


# =========================================================
# REQUEST MODELS
# =========================================================

class AnalysisRequest(BaseModel):
    telemetry_path: str
    video_path: str


class ApprovalRequest(BaseModel):
    approved: bool


class RecoveryApprovalRequest(BaseModel):
    incident_id: str
    strategy_id: str
    decision: Optional[str] = "APPROVED"
    approved: Optional[bool] = None
    incident_version: Optional[int] = None
    operator_id: Optional[str] = None
    operator_notes: Optional[str] = None
    caller_role: Optional[str] = None


class RecoveryExecutionRequest(BaseModel):
    incident_id: str
    strategy_id: str
    approval_id: Optional[str] = None
    incident_version: Optional[int] = None


class AgentRecoveryVerificationRequest(BaseModel):
    incident_id: str
    post_telemetry_path: Optional[str] = None
    post_video_path: Optional[str] = None
    verify_mode: Optional[str] = "standard"


class ExecutionRequest(BaseModel):
    progress_video_path: Optional[str] = None


class VerificationRequest(BaseModel):
    telemetry_path: str
    video_path: str


class DemoRunRequest(BaseModel):
    scenario: str


class OrchestrationRequest(BaseModel):
    mode: Optional[str] = "auto"


class AdkOrchestrateRequest(BaseModel):
    incident_id: Optional[str] = None
    mode: Optional[str] = "auto"


class WhatIfRequest(BaseModel):
    incident_id: Optional[str] = None


# =========================================================
# UTILITY FUNCTIONS
# =========================================================

def now_timestamp() -> str:
    """
    Return ISO timestamp for incident/audit records.
    """

    return datetime.now().isoformat(
        timespec="seconds"
    )


def load_json(
    path: Path
) -> Dict:
    """
    Load JSON file safely.
    """

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail=f"File not found: {path}"
        )

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except json.JSONDecodeError as exc:

        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON file: {path}"
        ) from exc


def resolve_project_path(
    relative_path: str
) -> Path:
    """
    Resolve project-relative path safely.

    Prevents accessing files outside the
    RoboIQ Guardian project directory.
    """

    path = (
        BASE_DIR
        / relative_path
    ).resolve()

    if (
        BASE_DIR not in path.parents
        and path != BASE_DIR
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Path must remain inside "
                "the RoboIQ Guardian project."
            )
        )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"File not found: "
                f"{relative_path}"
            )
        )

    return path


# =========================================================
# AUDIT / STATE HISTORY
# =========================================================

def append_state_history(
    incident: Dict,
    state: str
) -> None:
    """
    Record every incident state transition.
    """

    incident.setdefault(
        "state_history",
        []
    ).append({
        "state": state,
        "timestamp": now_timestamp()
    })


def append_audit_log(
    incident: Dict,
    event: str,
    source: str,
    details: Optional[Dict] = None
) -> None:
    """
    Add an audit event for UI, traceability, and SHA-256 cryptographic integrity.
    """
    incident_id = incident.get("incident_id", "UNKNOWN_INCIDENT")
    chain_entry = create_audit_event(
        incident_id=incident_id,
        event_type=event,
        actor=source,
        decision=details.get("decision", "RECORDED") if details else "RECORDED",
        strategy_id=details.get("strategy_id") if details else None,
        details=details or {},
    )

    entry = {
        "timestamp": chain_entry["timestamp"],
        "event": event,
        "source": source,
        "event_id": chain_entry["event_id"],
        "entry_hash": chain_entry["entry_hash"],
        "prev_hash": chain_entry["prev_hash"],
    }

    if details:
        entry["details"] = details

    incident.setdefault(
        "audit_log",
        []
    ).append(
        entry
    )


# =========================================================
# STATE TRANSITION WRAPPER
# =========================================================

def advance_state(
    incident: Dict,
    next_state: str
) -> None:
    """
    Validate and apply incident state transition.
    """

    current_state = incident[
        "state"
    ]

    transition = transition_state(
        current_state,
        next_state
    )

    if isinstance(
        transition,
        dict
    ):

        transition_status = (
            transition.get(
                "status"
            )
        )

        if (
            transition_status
            != "STATE_TRANSITION_SUCCESS"
        ):

            raise HTTPException(
                status_code=400,
                detail={
                    "message":
                        "Invalid incident "
                        "state transition",

                    "transition":
                        transition
                }
            )

    incident[
        "state"
    ] = next_state

    incident[
        "updated_at"
    ] = now_timestamp()

    append_state_history(
        incident,
        next_state
    )

    append_audit_log(
        incident,
        event=next_state,
        source=(
            "Incident State Machine"
        ),
        details={
            "previous_state":
                current_state,

            "new_state":
                next_state
        }
    )


# =========================================================
# SUMMARY BUILDER
# =========================================================

def build_incident_summary(
    incident: Dict
) -> Dict:
    """
    Build compact UI-friendly incident summary.
    """

    telemetry_result = (
        incident.get(
            "telemetry_result"
        )
        or {}
    )

    robotics_er_result = (
        incident.get(
            "robotics_er_result"
        )
        or {}
    )

    root_cause_result = (
        incident.get(
            "root_cause"
        )
        or {}
    )

    recovery_plan = (
        incident.get(
            "recovery_plan"
        )
        or {}
    )

    recovery_prediction = (
        incident.get(
            "recovery_prediction"
        )
        or {}
    )

    execution = (
        incident.get(
            "execution"
        )
        or {}
    )

    verification = (
        incident.get(
            "verification"
        )
        or {}
    )

    root_cause = (
        root_cause_result.get(
            "root_cause"
        )
    )

    root_cause_name = None

    if isinstance(
        root_cause,
        dict
    ):

        root_cause_name = (
            root_cause.get(
                "name"
            )
        )

    elif isinstance(
        root_cause,
        str
    ):

        root_cause_name = (
            root_cause
        )

    return {

        "incident_id":
            incident.get(
                "incident_id"
            ),

        "state":
            incident.get(
                "state"
            ),

        "analysis_status":
            incident.get(
                "analysis_status"
            ),

        "recommendation":
            incident.get(
                "recommendation"
            ),

        "created_at":
            incident.get(
                "created_at"
            ),

        "updated_at":
            incident.get(
                "updated_at"
            ),

        "cell_id":
            incident.get(
                "cell_id"
            ),

        "robot_id":
            incident.get(
                "robot_id"
            ),

        "severity":
            incident.get(
                "severity"
            ),

        "telemetry": {

            "status":
                telemetry_result.get(
                    "status"
                ),

            "breach_count":
                len(
                    telemetry_result.get(
                        "breached_signals",
                        []
                    )
                )
        },

        "gemini": {

            "operation_status":
                robotics_er_result.get(
                    "operation_status"
                ),

            "motion_stability":
                robotics_er_result.get(
                    "motion_stability"
                ),

            "task_completed":
                robotics_er_result.get(
                    "task_completed"
                ),

            "cache_status":
                robotics_er_result.get(
                    "cache_status"
                ),

            "generated_by":
                robotics_er_result.get(
                    "generated_by"
                )
        },

        "diagnosis": {

            "root_cause":
                root_cause_name,

            "evidence_score":
                root_cause_result.get(
                    "score"
                ),

            "threshold":
                root_cause_result.get(
                    "threshold"
                )
        },

        "recovery": {

            "status":
                recovery_plan.get(
                    "status"
                ),

            "risk_level":
                recovery_plan.get(
                    "risk_level"
                ),

            "success_score":
                recovery_prediction.get(
                    "recovery_success_score"
                ),

            "residual_risk":
                recovery_prediction.get(
                    "residual_risk"
                ),

            "execution_status":
                execution.get(
                    "status"
                ),

            "verification_status":
                verification.get(
                    "status"
                )
        }
    }


# =========================================================
# HEALTH
# =========================================================

@app.get(
    "/health"
)
def health():

    return {
        "status": "ok",
        "service":
            "RoboIQ Guardian",
        "version": "1.0.0"
    }


# =========================================================
# ANALYSIS
#
# Observe
# Detect
# Investigate
# Diagnose
# Recover
# Assess
# =========================================================

@app.post(
    "/analysis"
)
def analyze_incident(
    request: AnalysisRequest
):

    telemetry_path = (
        resolve_project_path(
            request.telemetry_path
        )
    )

    video_path = (
        resolve_project_path(
            request.video_path
        )
    )

    thresholds = load_json(
        THRESHOLDS_FILE
    )

    telemetry = load_json(
        telemetry_path
    )

    # =====================================================
    # 1. DETECT
    # Deterministic telemetry analysis
    # =====================================================

    telemetry_result_obj = (
        analyze_telemetry(
            telemetry,
            thresholds
        )
    )

    telemetry_result = (
        telemetry_result_obj
        .to_dict()
    )

    # =====================================================
    # 2. OBSERVE
    # Gemini Robotics ER 2
    # =====================================================

    try:

        robotics_er_result = (
            analyze_video(
                str(video_path)
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Robotics ER analysis failed: "
                f"{str(exc)}"
            )
        ) from exc

    # =====================================================
    # CREATE INCIDENT
    # =====================================================

    incident_id = (
        f"INC-"
        f"{uuid4().hex[:8].upper()}"
    )

    created_at = (
        now_timestamp()
    )

    incident = {

        "incident_id":
            incident_id,

        "state":
            "NORMAL",

        "created_at":
            created_at,

        "updated_at":
            created_at,

        "cell_id":
            "CELL-03",

        "robot_id":
            "R-07",

        "severity":
            "NORMAL",

        "production_state":
            "RUNNING",

        "inputs": {

            "telemetry_path":
                request.telemetry_path,

            "video_path":
                request.video_path
        },

        "telemetry_result":
            telemetry_result,

        "robotics_er_result":
            robotics_er_result,

        "state_history": [
            {
                "state":
                    "NORMAL",

                "timestamp":
                    created_at
            }
        ],

        "audit_log": []
    }

    INCIDENTS[
        incident_id
    ] = incident

    append_audit_log(
        incident,
        event="ANALYSIS_STARTED",
        source="RoboIQ Guardian",
        details={
            "telemetry_path":
                request.telemetry_path,

            "video_path":
                request.video_path
        }
    )

    # =====================================================
    # HEALTHY STATE CHECK
    # =====================================================

    telemetry_normal = (
        telemetry_result.get(
            "status"
        )
        == "NORMAL"
    )

    visual_normal = (
        robotics_er_result.get(
            "operation_status"
        )
        == "NORMAL"

        and

        robotics_er_result.get(
            "motion_stability"
        )
        == "STABLE"
    )

    if (
        telemetry_normal
        and visual_normal
    ):

        incident[
            "analysis_status"
        ] = "NORMAL"

        incident[
            "recommendation"
        ] = (
            "CONTINUE_PRODUCTION"
        )

        incident[
            "severity"
        ] = "NORMAL"

        incident[
            "production_state"
        ] = "RUNNING"

        incident[
            "updated_at"
        ] = now_timestamp()

        append_audit_log(
            incident,
            event=(
                "NORMAL_OPERATION_CONFIRMED"
            ),
            source=(
                "RoboIQ Guardian"
            )
        )

        return incident

    # =====================================================
    # FAILURE PATH
    # =====================================================

    incident[
        "severity"
    ] = "HIGH"

    incident[
        "production_state"
    ] = "PAUSED"

    advance_state(
        incident,
        "FAILURE_DETECTED"
    )

    advance_state(
        incident,
        "INVESTIGATING"
    )

    # =====================================================
    # 3. MULTIMODAL EVIDENCE
    # =====================================================

    try:

        evidence = (
            build_evidence(
                telemetry_result,
                robotics_er_result
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Evidence generation failed: "
                f"{str(exc)}"
            )
        ) from exc

    incident[
        "evidence"
    ] = evidence

    append_audit_log(
        incident,
        event="EVIDENCE_GENERATED",
        source="Evidence Engine",
        details={
            "evidence_count":
                len(evidence)
        }
    )

    # =====================================================
    # 4. HYPOTHESIS ANALYSIS
    # =====================================================

    try:

        hypotheses = (
            get_hypotheses()
        )

        ranking = (
            score_hypotheses(
                evidence,
                hypotheses
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Hypothesis analysis failed: "
                f"{str(exc)}"
            )
        ) from exc

    incident[
        "hypothesis_ranking"
    ] = ranking

    append_audit_log(
        incident,
        event=(
            "HYPOTHESES_RANKED"
        ),
        source=(
            "Guardian Investigation Engine"
        ),
        details={
            "hypothesis_count":
                len(ranking)
        }
    )

    # =====================================================
    # 5. ROOT CAUSE
    # =====================================================

    try:

        root_cause = (
            select_root_cause(
                ranking
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Root cause selection failed: "
                f"{str(exc)}"
            )
        ) from exc

    incident[
        "root_cause"
    ] = root_cause

    if (
        root_cause.get(
            "status"
        )
        != "ROOT_CAUSE_IDENTIFIED"
    ):

        incident[
            "analysis_status"
        ] = (
            "ROOT_CAUSE_UNCERTAIN"
        )

        incident[
            "recommendation"
        ] = (
            "HUMAN_INVESTIGATION_REQUIRED"
        )

        incident[
            "updated_at"
        ] = now_timestamp()

        append_audit_log(
            incident,
            event=(
                "ROOT_CAUSE_UNCERTAIN"
            ),
            source=(
                "Root Cause Service"
            )
        )

        return incident

    advance_state(
        incident,
        "ROOT_CAUSE_IDENTIFIED"
    )

    append_audit_log(
        incident,
        event=(
            "ROOT_CAUSE_CONFIRMED"
        ),
        source=(
            "Guardian Investigation Engine"
        ),
        details={
            "root_cause":
                root_cause.get(
                    "root_cause"
                ),

            "evidence_score":
                root_cause.get(
                    "score"
                )
        }
    )

    # =====================================================
    # 6. GEMINI RECOVERY RECOMMENDATION
    # =====================================================

    try:

        recovery_plan = (
            generate_recovery_plan(
                root_cause,
                evidence
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Recovery recommendation "
                "failed: "
                f"{str(exc)}"
            )
        ) from exc

    incident[
        "recovery_plan"
    ] = recovery_plan

    if (
        recovery_plan.get(
            "status"
        )
        != "RECOVERY_PROPOSED"
    ):

        incident[
            "analysis_status"
        ] = (
            "RECOVERY_PLAN_NOT_READY"
        )

        incident[
            "recommendation"
        ] = (
            "HUMAN_RECOVERY_REVIEW_REQUIRED"
        )

        incident[
            "updated_at"
        ] = now_timestamp()

        append_audit_log(
            incident,
            event=(
                "RECOVERY_REVIEW_REQUIRED"
            ),
            source=(
                "Gemini Robotics ER 2"
            )
        )

        return incident

    advance_state(
        incident,
        "RECOVERY_PROPOSED"
    )

    append_audit_log(
        incident,
        event=(
            "RECOVERY_PLAN_GENERATED"
        ),
        source=(
            "Gemini Robotics ER 2"
        ),
        details={
            "risk_level":
                recovery_plan.get(
                    "risk_level"
                ),

            "action_count":
                len(
                    recovery_plan.get(
                        "recommended_actions",
                        []
                    )
                )
        }
    )

    # =====================================================
    # 7. RECOVERY SUCCESS ASSESSMENT
    # =====================================================

    try:

        recovery_prediction = (
            predict_recovery_success(
                root_cause,
                evidence,
                recovery_plan
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Recovery prediction failed: "
                f"{str(exc)}"
            )
        ) from exc

    incident[
        "recovery_prediction"
    ] = recovery_prediction

    incident[
        "analysis_status"
    ] = "RECOVERY_PROPOSED"

    incident[
        "recommendation"
    ] = (
        "AWAITING_HUMAN_APPROVAL"
    )

    incident[
        "updated_at"
    ] = now_timestamp()

    append_audit_log(
        incident,
        event=(
            "RECOVERY_SUCCESS_ASSESSED"
        ),
        source=(
            "Gemini Robotics ER 2"
        ),
        details={
            "recovery_success_score":
                recovery_prediction.get(
                    "recovery_success_score"
                ),

            "residual_risk":
                recovery_prediction.get(
                    "residual_risk"
                )
        }
    )

    # =====================================================
    # 8. GOOGLE ADK MULTI-AGENT ORCHESTRATION
    # =====================================================

    try:
        if orchestrate_investigation is None:
            raise RuntimeError("ADK dependency unavailable")
        adk_result = orchestrate_investigation(
            incident["incident_id"],
            execution_mode="auto"
        )
        incident["adk_orchestration"] = adk_result
        append_audit_log(
            incident,
            event="ADK_MULTI_AGENT_ORCHESTRATED",
            source="Google ADK Guardian Coordinator",
            details={
                "execution_mode": adk_result.get("provenance", {}).get("execution_mode"),
                "agents_count": len(adk_result.get("provenance", {}).get("agents_deployed", [])),
                "top_hypothesis": (
                    adk_result.get("identified_root_cause", {}).get("name")
                    if isinstance(adk_result.get("identified_root_cause"), dict)
                    else str(adk_result.get("identified_root_cause"))
                ),
            }
        )
    except Exception:
        pass

    return incident


# =========================================================
# GET FULL INCIDENT
# =========================================================

@app.get(
    "/incident/{incident_id}"
)
def get_incident(
    incident_id: str
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:

        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    return incident


# =========================================================
# LIST INCIDENTS
# =========================================================

@app.get(
    "/incidents"
)
def list_incidents():

    results = [
        build_incident_summary(
            incident
        )
        for incident
        in INCIDENTS.values()
    ]

    results.sort(
        key=lambda item:
            item.get(
                "created_at"
            )
            or "",
        reverse=True
    )

    return {
        "count":
            len(results),

        "incidents":
            results
    }


# =========================================================
# FLEET OVERVIEW
# =========================================================

@app.get(
    "/fleet"
)
def get_fleet():

    cell_03_incidents = [
        incident
        for incident
        in INCIDENTS.values()
        if (
            incident.get(
                "cell_id"
            )
            == "CELL-03"
        )
    ]

    cell_03_incidents.sort(
        key=lambda incident:
            incident.get(
                "created_at"
            )
            or "",
        reverse=True
    )

    latest_cell_03 = (
        cell_03_incidents[0]
        if cell_03_incidents
        else None
    )

    cell_03_active = False

    if latest_cell_03:

        cell_03_active = (
            latest_cell_03.get(
                "state"
            )
            not in {
                "NORMAL",
                "RECOVERED"
            }
        )

    fleet = [

        {
            "cell_id":
                "CELL-01",

            "robot_id":
                "R-01",

            "status":
                "NORMAL",

            "health_score":
                96,

            "production_state":
                "RUNNING",

            "active_incident":
                None
        },

        {
            "cell_id":
                "CELL-02",

            "robot_id":
                "R-04",

            "status":
                "NORMAL",

            "health_score":
                94,

            "production_state":
                "RUNNING",

            "active_incident":
                None
        },

        {
            "cell_id":
                "CELL-03",

            "robot_id":
                "R-07",

            "status":
                (
                    "FAILURE"
                    if cell_03_active
                    else "NORMAL"
                ),

            "health_score":
                (
                    42
                    if cell_03_active
                    else 95
                ),

            "production_state":
                (
                    "PAUSED"
                    if cell_03_active
                    else "RUNNING"
                ),

            "active_incident":
                (
                    latest_cell_03.get(
                        "incident_id"
                    )
                    if cell_03_active
                    else None
                )
        }
    ]

    return {
        "fleet":
            fleet,

        "total_cells":
            len(fleet),

        "healthy_cells":
            len(
                [
                    item
                    for item in fleet
                    if item[
                        "status"
                    ]
                    == "NORMAL"
                ]
            ),

        "affected_cells":
            len(
                [
                    item
                    for item in fleet
                    if item[
                        "status"
                    ]
                    != "NORMAL"
                ]
            )
    }


# =========================================================
# INCIDENT SUMMARY
# =========================================================

@app.get(
    "/incident/{incident_id}/summary"
)
def get_incident_summary(
    incident_id: str
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:

        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    return (
        build_incident_summary(
            incident
        )
    )


# =========================================================
# INCIDENT TELEMETRY
# =========================================================

@app.get(
    "/incident/{incident_id}/telemetry"
)
def get_incident_telemetry(
    incident_id: str
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:

        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    telemetry_path = (
        incident
        .get(
            "inputs",
            {}
        )
        .get(
            "telemetry_path"
        )
    )

    if not telemetry_path:

        raise HTTPException(
            status_code=404,
            detail=(
                "Telemetry source "
                "not available."
            )
        )

    resolved_path = (
        resolve_project_path(
            telemetry_path
        )
    )

    telemetry = load_json(
        resolved_path
    )

    thresholds = load_json(
        THRESHOLDS_FILE
    )

    return {

        "incident_id":
            incident_id,

        "cell_id":
            incident.get(
                "cell_id"
            ),

        "robot_id":
            incident.get(
                "robot_id"
            ),

        "telemetry":
            telemetry,

        "thresholds":
            thresholds,

        "analysis":
            incident.get(
                "telemetry_result"
            )
    }


# =========================================================
# HUMAN APPROVAL
# =========================================================

@app.post(
    "/incident/{incident_id}/approve"
)
def approve_incident(
    incident_id: str,
    request: ApprovalRequest
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:

        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    if (
        incident.get(
            "state"
        )
        != "RECOVERY_PROPOSED"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Incident is not awaiting "
                "recovery approval."
            )
        )

    recovery_plan = (
        incident.get(
            "recovery_plan"
        )
    )

    if not recovery_plan:

        raise HTTPException(
            status_code=400,
            detail=(
                "Recovery plan "
                "not available."
            )
        )

    root_cause_result = (
        incident.get(
            "root_cause"
        )
        or {}
    )

    root_cause_value = (
        root_cause_result.get(
            "root_cause"
        )
    )

    root_cause_name = None

    if isinstance(
        root_cause_value,
        dict
    ):

        root_cause_name = (
            root_cause_value.get(
                "name"
            )
        )

    elif isinstance(
        root_cause_value,
        str
    ):

        root_cause_name = (
            root_cause_value
        )

    approval_input = {

        "status":
            recovery_plan.get(
                "status"
            ),

        "root_cause":
            root_cause_name,

        "risk_level":
            recovery_plan.get(
                "risk_level"
            ),

        "human_approval_required":
            True,

        "actions":
            recovery_plan.get(
                "recommended_actions",
                []
            ),

        "recommended_actions":
            recovery_plan.get(
                "recommended_actions",
                []
            )
    }

    try:

        approval_result = (
            approve_recovery(
                approval_input,
                request.approved
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Approval processing failed: "
                f"{str(exc)}"
            )
        ) from exc

    incident[
        "approval"
    ] = approval_result

    incident[
        "updated_at"
    ] = now_timestamp()

    if request.approved:

        if (
            approval_result.get(
                "status"
            )
            != "RECOVERY_APPROVED"
        ):

            raise HTTPException(
                status_code=400,
                detail=approval_result
            )

        advance_state(
            incident,
            "RECOVERY_APPROVED"
        )

        incident[
            "recommendation"
        ] = (
            "READY_FOR_RECOVERY_EXECUTION"
        )

        append_audit_log(
            incident,
            event=(
                "RECOVERY_APPROVED_BY_OPERATOR"
            ),
            source=(
                "Human Operator"
            )
        )

    else:

        incident[
            "recommendation"
        ] = (
            "RECOVERY_REJECTED_BY_OPERATOR"
        )

        append_audit_log(
            incident,
            event=(
                "RECOVERY_REJECTED_BY_OPERATOR"
            ),
            source=(
                "Human Operator"
            )
        )

    return approval_result


# =========================================================
# RECOVERY EXECUTION
# =========================================================

@app.post(
    "/incident/{incident_id}/execute"
)
def execute_incident(
    incident_id: str,
    request: ExecutionRequest
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:

        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    if (
        incident.get(
            "state"
        )
        != "RECOVERY_APPROVED"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Recovery must be approved "
                "before execution."
            )
        )

    approval = (
        incident.get(
            "approval"
        )
    )

    if not approval:

        raise HTTPException(
            status_code=400,
            detail=(
                "Approval result "
                "not available."
            )
        )

    progress_video_path = None

    if (
        request.progress_video_path
    ):

        progress_video_path = str(
            resolve_project_path(
                request.progress_video_path
            )
        )

    advance_state(
        incident,
        "RECOVERING"
    )

    append_audit_log(
        incident,
        event=(
            "RECOVERY_EXECUTION_STARTED"
        ),
        source=(
            "Recovery Executor"
        )
    )

    try:

        execution_result = (
            execute_recovery(
                approval_result=
                    approval,

                progress_video_path=
                    progress_video_path
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Recovery execution failed: "
                f"{str(exc)}"
            )
        ) from exc

    incident[
        "execution"
    ] = execution_result

    incident[
        "updated_at"
    ] = now_timestamp()

    if (
        execution_result.get(
            "status"
        )
        != "RECOVERY_EXECUTED"
    ):

        incident[
            "recommendation"
        ] = (
            "RECOVERY_EXECUTION_REQUIRES_REVIEW"
        )

        append_audit_log(
            incident,
            event=(
                "RECOVERY_EXECUTION_FAILED"
            ),
            source=(
                "Recovery Executor"
            ),
            details={
                "status":
                    execution_result.get(
                        "status"
                    ),

                "failed_checkpoint":
                    execution_result.get(
                        "failed_checkpoint"
                    )
            }
        )

        # Move incident into failure state.
        if (
            incident.get(
                "state"
            )
            == "RECOVERING"
        ):

            advance_state(
                incident,
                "RECOVERY_FAILED"
            )

        incident[
            "production_state"
        ] = "PAUSED"

        return execution_result

    incident[
        "recommendation"
    ] = (
        "READY_FOR_FINAL_VERIFICATION"
    )

    append_audit_log(
        incident,
        event=(
            "RECOVERY_EXECUTION_COMPLETED"
        ),
        source=(
            "Recovery Executor"
        ),
        details={
            "actions_executed":
                execution_result.get(
                    "actions_executed"
                )
        }
    )

    return execution_result


# =========================================================
# FINAL VERIFICATION
# =========================================================

@app.post(
    "/incident/{incident_id}/verify"
)
def verify_incident(
    incident_id: str,
    request: VerificationRequest
):

    incident = INCIDENTS.get(
        incident_id
    )

    if not incident:

        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    if (
        incident.get(
            "state"
        )
        != "RECOVERING"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Recovery execution must "
                "complete before final "
                "verification."
            )
        )

    execution = (
        incident.get(
            "execution",
            {}
        )
    )

    if (
        execution.get(
            "status"
        )
        != "RECOVERY_EXECUTED"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Recovery execution "
                "is not complete."
            )
        )

    post_telemetry_path = (
        resolve_project_path(
            request.telemetry_path
        )
    )

    post_video_path = (
        resolve_project_path(
            request.video_path
        )
    )

    post_telemetry = (
        load_json(
            post_telemetry_path
        )
    )

    thresholds = (
        load_json(
            THRESHOLDS_FILE
        )
    )

    advance_state(
        incident,
        "VERIFYING"
    )

    append_audit_log(
        incident,
        event=(
            "FINAL_VERIFICATION_STARTED"
        ),
        source=(
            "RoboIQ Guardian"
        )
    )

    try:

        verification_result = (
            verify_recovery(
                telemetry=
                    post_telemetry,

                thresholds=
                    thresholds,

                video_path=
                    str(
                        post_video_path
                    )
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Recovery verification failed: "
                f"{str(exc)}"
            )
        ) from exc

    incident[
        "verification"
    ] = verification_result

    incident[
        "post_recovery_inputs"
    ] = {

        "telemetry_path":
            request.telemetry_path,

        "video_path":
            request.video_path
    }

    incident[
        "updated_at"
    ] = now_timestamp()

    if (
        verification_result.get(
            "status"
        )
        == "RECOVERY_VERIFIED"
    ):

        advance_state(
            incident,
            "RECOVERED"
        )

        incident[
            "recommendation"
        ] = (
            "RESUME_PRODUCTION"
        )

        incident[
            "severity"
        ] = "RESOLVED"

        incident[
            "production_state"
        ] = "RUNNING"

        append_audit_log(
            incident,
            event=(
                "RECOVERY_VERIFIED"
            ),
            source=(
                "RoboIQ Guardian"
            ),
            details={
                "telemetry_pass":
                    verification_result.get(
                        "telemetry_pass"
                    ),

                "visual_pass":
                    verification_result.get(
                        "visual_pass"
                    )
            }
        )

    else:

        advance_state(
            incident,
            "RECOVERY_FAILED"
        )

        incident[
            "recommendation"
        ] = (
            "KEEP_PRODUCTION_PAUSED"
        )

        incident[
            "severity"
        ] = "HIGH"

        incident[
            "production_state"
        ] = "PAUSED"

        append_audit_log(
            incident,
            event=(
                "RECOVERY_VERIFICATION_FAILED"
            ),
            source=(
                "RoboIQ Guardian"
            )
        )

    return verification_result


# =========================================================
# DEMO RUN
# =========================================================

@app.post(
    "/demo/run"
)
def run_demo(
    request: DemoRunRequest
):

    scenario = (
        request.scenario
        .strip()
        .lower()
    )

    if (
        scenario
        == "normal"
    ):

        analysis_request = (
            AnalysisRequest(

                telemetry_path=(
                    "data/telemetry/"
                    "normal.json"
                ),

                video_path=(
                    "data/videos/"
                    "normal.mp4"
                )
            )
        )

    elif (
        scenario
        == "failure"
    ):

        analysis_request = (
            AnalysisRequest(

                telemetry_path=(
                    "data/telemetry/"
                    "failure.json"
                ),

                video_path=(
                    "data/videos/"
                    "failure.mp4"
                )
            )
        )

    else:

        raise HTTPException(
            status_code=400,
            detail=(
                "Scenario must be "
                "'normal' or 'failure'."
            )
        )

    return analyze_incident(
        analysis_request
    )


# =========================================================
# DEMO RESET
# =========================================================

@app.post(
    "/demo/reset"
)
def reset_demo():

    incident_count = (
        len(
            INCIDENTS
        )
    )

    INCIDENTS.clear()

    return {

        "status":
            "DEMO_RESET",

        "incidents_cleared":
            incident_count,

        "message":
            (
                "RoboIQ Guardian demo "
                "state has been reset."
            )
    }


# =========================================================
# GOOGLE ADK MULTI-AGENT ORCHESTRATION ENDPOINTS
# =========================================================

@app.get(
    "/adk/status"
)
def get_adk_status():
    import os
    has_api_key = bool(
        os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    )
    return {
        "framework": "Google Agent Development Kit (ADK)",
        "adk_version": "version determined by installed package",
        "coordinator": "GuardianCoordinator",
        "agents": [
            "PredictionAgent",
            "PreventionAgent",
            "InvestigationAgent",
            "RecoveryAgent",
            "LearningAgent",
        ],
        "tools": [
            "get_robot_telemetry",
            "get_video_observations",
            "get_incident_evidence",
            "get_root_cause_hypotheses",
            "get_recovery_plan",
            "assess_recovery_risk",
            "simulate_recovery_option",
            "get_recovery_outcome",
        ],
        "bounded_iterations": 5,
        "live_execution_available": False,
        "default_execution_mode": "deterministic_fallback",
        "status": "READY" if orchestrate_investigation is not None else "DEPENDENCY_UNAVAILABLE",
        "dependency_error": ADK_IMPORT_ERROR,
    }


@app.post(
    "/adk/orchestrate"
)
def run_adk_orchestration(
    request: Optional[AdkOrchestrateRequest] = None
):
    incident_id = (request.incident_id if request else None) or "INC-E9005A5F"
    mode = (request.mode if request else "auto") or "auto"
    if orchestrate_investigation is None:
        raise HTTPException(status_code=503, detail="Official Google ADK dependency is unavailable")
    result = orchestrate_investigation(incident_id, execution_mode=mode)
    if incident_id in INCIDENTS:
        INCIDENTS[incident_id]["adk_orchestration"] = result
        append_audit_log(
            INCIDENTS[incident_id],
            event="ADK_MULTI_AGENT_ORCHESTRATED",
            source="Google ADK Guardian Coordinator",
            details={
                "execution_mode": result.get("provenance", {}).get("execution_mode"),
                "agents_count": len(result.get("provenance", {}).get("agents_deployed", [])),
            }
        )
    return result


@app.post("/incident/{incident_id}/orchestrate")
async def orchestrate_incident(
    incident_id: str,
    request: Optional[OrchestrationRequest] = None
):
    mode = (request.mode if request else "auto") or "auto"

    # Only existing incidents may be orchestrated.
    incident = INCIDENTS.get(incident_id)
    if incident is None:
        raise HTTPException(
            status_code=404,
            detail=f"Incident {incident_id} not found"
        )

    if mode == "adk_offline":
        try:
            result = await run_guardian_workflow(incident_id)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"ADK workflow failed: {exc}"
            ) from exc

        incident["adk_offline_workflow"] = result

        append_audit_log(
            incident,
            event="ADK_OFFLINE_RUNNER_EXECUTED",
            source="Google ADK Runner",
            details={
                "execution_mode": "adk_offline_runner",
                "agents_count": len(result["trace"]),
                "model_calls": 0,
            }
        )
        return result

    # Preserve existing orchestration behavior.
    if orchestrate_investigation is None:
        raise HTTPException(
            status_code=503,
            detail="Existing ADK coordinator unavailable"
        )

    result = orchestrate_investigation(
        incident_id,
        execution_mode=mode
    )

    incident["adk_orchestration"] = result

    append_audit_log(
        incident,
        event="ADK_MULTI_AGENT_ORCHESTRATED",
        source="Google ADK Guardian Coordinator",
        details={
            "execution_mode": result.get(
                "provenance", {}
            ).get("execution_mode"),
            "agents_count": len(
                result.get("provenance", {}).get(
                    "agents_deployed", []
                )
            ),
        }
    )

    return result



@app.get(
    "/incident/{incident_id}/orchestrate"
)
def get_incident_orchestration(
    incident_id: str
):
    incident = INCIDENTS.get(incident_id)
    if incident and incident.get("adk_orchestration"):
        return incident["adk_orchestration"]
    if orchestrate_investigation is None:
        raise HTTPException(status_code=503, detail="Official Google ADK dependency is unavailable")
    result = orchestrate_investigation(incident_id, execution_mode="auto")
    if incident:
        incident["adk_orchestration"] = result
    return result


# =========================================================
# STEP 41B: WHAT-IF RECOVERY INTELLIGENCE ENDPOINTS
# =========================================================

@app.post("/agent/recovery/what-if")
@app.get("/agent/recovery/what-if")
@app.post("/api/agent/recovery/what-if")
@app.get("/api/agent/recovery/what-if")
def evaluate_what_if_endpoint(
    request: Optional[WhatIfRequest] = None,
    incident_id: Optional[str] = None,
):
    """
    Step 41B What-If Recovery Intelligence endpoint.
    Accepts {"incident_id": "existing_incident_id"} or query parameter incident_id.
    Returns 3 evidence-grounded alternatives (Option A, Option B, Option C),
    residual risks, human approval prerequisites, verification requirements,
    qualitative recommendation, and provenance.
    Strictly read-only; no state changes or live physical commands.
    """
    target_id = None
    if request and request.incident_id:
        target_id = request.incident_id
    elif incident_id:
        target_id = incident_id

    # 1. Lookup incident from active registry
    incident = None
    if target_id and target_id in INCIDENTS:
        incident = INCIDENTS[target_id]
    elif INCIDENTS:
        if target_id:
            incident = INCIDENTS.get(target_id)
        if not incident:
            for inc in INCIDENTS.values():
                if inc.get("severity") in ("HIGH", "CRITICAL") or inc.get("state") == "RECOVERY_PROPOSED":
                    incident = inc
                    break
            if not incident:
                incident = next(iter(INCIDENTS.values()))

    # 2. If not found in memory, load from authoritative recorded failure data
    if not incident:
        incident = _load_incident_or_fallback(target_id or "INC-2026-ER2-401")
        resolved_id = target_id or incident.get("incident_id") or "INC-2026-ER2-401"
        if resolved_id not in INCIDENTS:
            INCIDENTS[resolved_id] = incident

    # 3. Evaluate What-If recovery alternatives
    result = evaluate_what_if_recovery(incident)

    # 4. Append audit log entry to incident audit trail
    if incident and "audit_log" in incident:
        append_audit_log(
            incident,
            event="WHAT_IF_RECOVERY_EVALUATED",
            source="RoboIQ Guardian What-If Intelligence",
            details={
                "incident_id": result.get("incident_id"),
                "status": result.get("status"),
                "alternatives_count": len(result.get("alternatives", [])),
                "recommended_strategy": (
                    result.get("recommendation", {}).get("recommended_strategy_id")
                    if result.get("recommendation")
                    else None
                ),
            },
        )

    return result


# =========================================================
# STEP 42.1: HUMAN APPROVAL & SAFETY GOVERNANCE ENDPOINTS
# =========================================================

@app.post("/agent/recovery/approval")
@app.post("/api/agent/recovery/approval")
def submit_recovery_approval(
    request: RecoveryApprovalRequest,
):
    """
    Step 42.1 Human Approval & Safety Governance endpoint.
    Accepts:
      {
        "incident_id": "...",
        "strategy_id": "...",
        "decision": "APPROVED" | "REJECTED" | "REVOKED",
        "incident_version": 1,
        "operator_id": "...",
        "operator_notes": "...",
        "caller_role": "..."
      }
    Validates incident ID, strategy ID, incident version, and human authorization.
    Enforces SIMULATION_ONLY and DEMO_APPROVAL_ONLY. Blocks AI self-approval.
    Rejects invalid, duplicate, stale, or superseded decisions.
    Appends SHA-256 chained audit event with cryptographic verification.
    """
    incident_id = request.incident_id
    if not incident_id:
        raise HTTPException(status_code=400, detail="incident_id is required.")

    # 1. Lookup incident from active registry or fallback
    incident = INCIDENTS.get(incident_id)
    if not incident:
        incident = _load_incident_or_fallback(incident_id)
        if incident:
            INCIDENTS[incident_id] = incident

    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    # 2. Process approval governance decision
    result = process_recovery_approval(incident, request.model_dump())

    # Check status and return appropriate HTTP status code
    status = result.get("status")
    if status == "BLOCKED":
        error_code = result.get("error_code")
        if error_code == "AI_SELF_APPROVAL_FORBIDDEN":
            raise HTTPException(status_code=403, detail=result)
        elif error_code == "STALE_INCIDENT_VERSION":
            raise HTTPException(status_code=409, detail=result)
        elif error_code in ("INVALID_STRATEGY_ID", "INVALID_INCIDENT_STATE", "NOTHING_TO_REVOKE"):
            raise HTTPException(status_code=400, detail=result)
        else:
            raise HTTPException(status_code=400, detail=result)

    if status == "DUPLICATE_DECISION":
        raise HTTPException(status_code=409, detail=result)

    return result


@app.get("/agent/recovery/approval/{incident_id}")
@app.get("/api/agent/recovery/approval/{incident_id}")
def get_recovery_approval_status(
    incident_id: str,
):
    """
    Step 42.1 Human Approval & Safety Governance query endpoint.
    Returns authoritative approval record, history, and SHA-256 audit chain integrity.
    """
    incident = INCIDENTS.get(incident_id)
    if not incident:
        incident = _load_incident_or_fallback(incident_id)
        if incident:
            INCIDENTS[incident_id] = incident

    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    return get_recovery_approval(incident_id, incident=incident)


# =========================================================
# STEP 42.2: SIMULATED RECOVERY EXECUTION ENDPOINTS
# =========================================================

@app.post("/agent/recovery/execute")
@app.post("/api/agent/recovery/execute")
def execute_recovery_simulation(
    request: RecoveryExecutionRequest,
):
    """
    Step 42.2 Simulated Recovery Execution endpoint.
    Accepts:
      {
        "incident_id": "...",
        "strategy_id": "...",
        "approval_id": "...",
        "incident_version": 1
      }
    Enforces prerequisite human approval (APPROVED_FOR_SIMULATION) from Step 42.1.
    Verifies SHA-256 audit chain integrity. Blocks duplicate or concurrent execution.
    Executes bounded simulated steps for Options A, B, and C.
    Strictly preserves SIMULATION_ONLY and DEMO_APPROVAL_ONLY.
    Never authorizes production restart or physical motion.
    """
    incident_id = request.incident_id
    if not incident_id:
        raise HTTPException(status_code=400, detail="incident_id is required.")

    # 1. Lookup incident from active registry or fallback
    incident = INCIDENTS.get(incident_id)
    if not incident:
        incident = _load_incident_or_fallback(incident_id)
        if incident:
            INCIDENTS[incident_id] = incident

    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    # 2. Execute simulated recovery
    result = execute_simulated_recovery(incident, request.model_dump())

    # Check status and return appropriate HTTP status code
    status = result.get("status")
    if status == "BLOCKED":
        error_code = result.get("error_code")
        if error_code in ("DUPLICATE_EXECUTION", "SIMULATION_ALREADY_RUNNING", "APPROVAL_ALREADY_CONSUMED", "STALE_INCIDENT_VERSION"):
            raise HTTPException(status_code=409, detail=result)
        elif error_code in ("MISSING_APPROVAL", "APPROVAL_REJECTED", "APPROVAL_REVOKED", "APPROVAL_SUPERSEDED", "NOT_APPROVED_FOR_SIMULATION", "STRATEGY_MISMATCH", "APPROVAL_ID_MISMATCH", "INVALID_STRATEGY_ID", "AUDIT_CHAIN_INTEGRITY_COMPROMISED"):
            raise HTTPException(status_code=400, detail=result)
        else:
            raise HTTPException(status_code=400, detail=result)

    return result


@app.get("/agent/recovery/execution/{incident_id}")
@app.get("/api/agent/recovery/execution/{incident_id}")
def get_recovery_execution_status(
    incident_id: str,
):
    """
    Step 42.2 Simulated Recovery Execution query endpoint.
    Returns authoritative execution state, step execution trace, safety restrictions,
    and linked audit event IDs.
    """
    incident = INCIDENTS.get(incident_id)
    if not incident:
        incident = _load_incident_or_fallback(incident_id)
        if incident:
            INCIDENTS[incident_id] = incident

    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    result = get_recovery_execution(incident_id, incident=incident)
    if result.get("execution_status") == "NO_EXECUTION_RECORD":
        raise HTTPException(status_code=404, detail=result)

    return result


# =========================================================
# STEP 43: RECOVERY VERIFICATION, LEARNING AGENT & PSR
# =========================================================

@app.post("/agent/recovery/verify")
@app.post("/api/agent/recovery/verify")
def submit_recovery_verification(
    request: AgentRecoveryVerificationRequest,
):
    """
    Step 43 Recovery Verification endpoint.
    Evaluates available post-recovery telemetry and Gemini Robotics ER 2 observations.
    Distinguishes pre-recovery evidence, simulated results, and independently recorded post-recovery evidence.
    Returns VERIFIED_SIMULATION_ONLY, VERIFICATION_FAILED, or INSUFFICIENT_EVIDENCE.
    Production resumption remains strictly unauthorized.
    """
    incident_id = request.incident_id
    if not incident_id:
        raise HTTPException(status_code=400, detail="incident_id is required.")

    incident = INCIDENTS.get(incident_id)
    if not incident:
        incident = _load_incident_or_fallback(incident_id)
        if incident:
            INCIDENTS[incident_id] = incident

    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    result = evaluate_recovery_verification(incident, request.model_dump())

    if result.get("status") == "BLOCKED":
        error_code = result.get("error_code")
        if error_code in ("AUDIT_CHAIN_INTEGRITY_COMPROMISED", "SIMULATION_INCOMPLETE"):
            raise HTTPException(status_code=400, detail=result)
        raise HTTPException(status_code=400, detail=result)

    return result


@app.get("/agent/recovery/verification/{incident_id}")
@app.get("/api/agent/recovery/verification/{incident_id}")
def get_recovery_verification_status(
    incident_id: str,
):
    """
    Step 43 Recovery Verification query endpoint.
    Returns verification status, evidence sufficiency, pre/sim/post breakdown, and unresolved risks.
    """
    incident = INCIDENTS.get(incident_id)
    if not incident:
        incident = _load_incident_or_fallback(incident_id)
        if incident:
            INCIDENTS[incident_id] = incident

    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")

    result = get_recovery_verification(incident_id, incident=incident)
    if result.get("verification_status") == "NO_VERIFICATION_RECORD":
        raise HTTPException(status_code=404, detail=result)

    return result


@app.get("/agent/learning/psr")
@app.get("/api/agent/learning/psr")
def get_prevention_success_rate():
    """
    Step 43 Prevention Success Rate (PSR) endpoint.
    Formula: Validated Successful Preventive Interventions / Eligible Preventive Interventions With Validated Outcomes * 100.
    Strictly excludes simulated executions and unverified outcomes.
    Returns PSR = 'N/A' (psr_value: None) when no eligible validated records exist.
    """
    return calculate_psr()


@app.get("/agent/learning/records")
@app.get("/api/agent/learning/records")
def list_learning_records():
    """
    List structured Learning Agent records across incidents.
    Deterministic offline processing, zero live model inference.
    """
    return {
        "count": len(LEARNING_REGISTRY),
        "records": list(LEARNING_REGISTRY.values()),
        "agent_metadata": {
            "agent_name": "LearningAgent",
            "framework": "Google Agent Development Kit (ADK)",
            "processing_mode": "deterministic_offline",
            "live_inference": False,
        },
    }


@app.get("/agent/learning/{incident_id}")
@app.get("/api/agent/learning/{incident_id}")
def get_incident_learning_record(
    incident_id: str,
):
    """
    Step 43 Learning Agent record query endpoint.
    Returns root-cause findings, strategy, approval ref, execution result, verification outcome,
    unresolved risks, and linked audit event IDs.
    """
    incident = INCIDENTS.get(incident_id)
    if not incident:
        incident = _load_incident_or_fallback(incident_id)
        if incident:
            INCIDENTS[incident_id] = incident

    record = get_learning_record(incident_id)
    if record.get("status") == "NO_LEARNING_RECORD":
        if incident:
            record = record_learning_outcome(incident)
        else:
            raise HTTPException(status_code=404, detail=f"No learning record found for incident '{incident_id}'.")

    return record

# Read-only historical synthetic telemetry (independent from the active demo incident).
from backend.services.telemetry_history import episode_catalog as _historical_episode_catalog, history_for as _historical_history_for

@app.get('/telemetry/episodes', tags=['Historical Telemetry'])
def historical_telemetry_episodes():
    return _historical_episode_catalog()

@app.get('/telemetry/history', tags=['Historical Telemetry'])
def historical_telemetry_history(robot_id: str, episode_id: str, limit: int = 240, start: str | None = None, end: str | None = None):
    if not 2 <= limit <= 1000:
        raise HTTPException(status_code=422, detail='limit must be between 2 and 1000')
    return _historical_history_for(robot_id, episode_id, limit, start, end)
