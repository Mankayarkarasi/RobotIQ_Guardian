"""
RoboIQ Guardian Recovery Executor

Executes an approved recovery plan using simulated actions.

Important:
- This PoC does NOT control a physical robot.
- Execution is simulated.
- Gemini Robotics ER independently verifies physical
  recovery checkpoints using supplied video evidence.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parents[2]

if str(BASE_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(BASE_DIR)
    )


from backend.services.progress_verifier import verify_progress
from backend.services.recovery_simulation_service import (
    execute_simulated_recovery,
    get_recovery_execution,
    EXECUTION_REGISTRY,
    BOUNDED_STRATEGY_STEPS,
)


CORRECTIVE_KEYWORDS = [
    "maintenance",
    "replacement",
    "repair",
    "calibration",
]


def now_timestamp() -> str:
    return datetime.now().isoformat(
        timespec="seconds"
    )


def execute_step(
    action: str
) -> Dict:
    """
    Simulate execution of one approved recovery action.

    This PoC does not control a real robot.
    """

    time.sleep(0.2)

    return {
        "type": "ACTION",
        "action": action,
        "status": "SUCCESS",
        "timestamp": now_timestamp(),
        "execution_mode": "SIMULATED",
    }


def run_progress_checkpoint(
    checkpoint_name: str,
    expected_state: str,
    video_path: str,
    use_cache: bool = True,
    cache_only: bool = False,
) -> Dict:
    """
    Ask Gemini Robotics ER 2 to verify whether
    the expected physical recovery state is visible.
    """

    result = verify_progress(
        video_path=video_path,
        checkpoint_name=checkpoint_name,
        expected_state=expected_state,
        use_cache=use_cache,
        cache_only=cache_only,
    )

    return {
        "type": "ER_PROGRESS_CHECK",
        "checkpoint": checkpoint_name,
        "status": result.get(
            "status"
        ),
        "confidence": result.get(
            "confidence"
        ),
        "observation": result.get(
            "observation"
        ),
        "expected_state": expected_state,
        "generated_by": result.get(
            "generated_by"
        ),
        "cache_status": result.get(
            "cache_status"
        ),
        "fallback_reason": result.get(
            "fallback_reason"
        ),
        "timestamp": now_timestamp(),
    }


def find_last_corrective_action_index(
    actions: List[str]
) -> Optional[int]:
    """
    Find the final maintenance / replacement /
    repair / calibration action.

    VALIDATION_READY should be checked only after
    all corrective actions are complete.
    """

    corrective_indexes = []

    for index, action in enumerate(actions):

        action_lower = action.lower()

        if any(
            keyword in action_lower
            for keyword in CORRECTIVE_KEYWORDS
        ):
            corrective_indexes.append(
                index
            )

    if not corrective_indexes:
        return None

    return corrective_indexes[-1]


def execute_recovery(
    approval_result: Dict,
    progress_video_path: Optional[str] = None,
    use_cache: bool = True,
    cache_only: bool = False,
) -> Dict:
    """
    Execute an approved recovery plan.

    Recovery actions come dynamically from the
    approved Gemini ER-generated recovery recommendation.

    Execution itself is simulated.

    Visual checkpoints are independently verified
    using Gemini Robotics ER 2.
    """

    # -----------------------------------------------------
    # Approval validation
    # -----------------------------------------------------

    if (
        approval_result.get("status")
        != "RECOVERY_APPROVED"
    ):
        return {
            "status": "EXECUTION_BLOCKED",
            "reason":
                "Recovery has not been approved.",
            "timeline": [],
            "progress_checks": [],
        }

    if (
        approval_result.get("approved")
        is False
    ):
        return {
            "status": "EXECUTION_BLOCKED",
            "reason":
                "Recovery approval was rejected.",
            "timeline": [],
            "progress_checks": [],
        }

    # -----------------------------------------------------
    # Support both action formats
    # -----------------------------------------------------

    actions: List[str] = (
        approval_result.get("actions")
        or approval_result.get(
            "recommended_actions"
        )
        or []
    )

    if not actions:
        return {
            "status": "EXECUTION_BLOCKED",
            "reason":
                "No approved recovery actions available.",
            "timeline": [],
            "progress_checks": [],
        }

    timeline: List[Dict] = []
    progress_checks: List[Dict] = []

    safe_position_verified = False
    validation_ready_verified = False

    last_corrective_index = (
        find_last_corrective_action_index(
            actions
        )
    )

    # -----------------------------------------------------
    # Execute actions
    # -----------------------------------------------------

    for index, action in enumerate(actions):

        step_result = execute_step(
            action
        )

        timeline.append(
            step_result
        )

        if (
            step_result.get("status")
            != "SUCCESS"
        ):
            return {
                "status":
                    "RECOVERY_EXECUTION_FAILED",
                "failed_action":
                    action,
                "timeline":
                    timeline,
                "progress_checks":
                    progress_checks,
            }

        action_lower = action.lower()

        # -------------------------------------------------
        # CHECKPOINT 1 — SAFE_POSITION
        # -------------------------------------------------

        is_safe_position_action = (
            "safe" in action_lower
            and "position" in action_lower
        )

        if (
            progress_video_path
            and is_safe_position_action
            and not safe_position_verified
        ):

            check = run_progress_checkpoint(
                checkpoint_name=
                    "SAFE_POSITION",
                expected_state=(
                    "The robot is in a stable and "
                    "safe position with no abnormal "
                    "movement."
                ),
                video_path=
                    progress_video_path,
                use_cache=
                    use_cache,
                cache_only=
                    cache_only,
            )

            timeline.append(
                check
            )

            progress_checks.append(
                check
            )

            # IMPORTANT:
            # Only VERIFIED allows recovery to proceed.
            if (
                check.get("status")
                != "VERIFIED"
            ):
                return {
                    "status":
                        "RECOVERY_PROGRESS_FAILED",
                    "failed_checkpoint":
                        "SAFE_POSITION",
                    "checkpoint_status":
                        check.get("status"),
                    "timeline":
                        timeline,
                    "progress_checks":
                        progress_checks,
                    "recommendation":
                        "PAUSE_AND_HUMAN_REVIEW",
                }

            safe_position_verified = True

        # -------------------------------------------------
        # CHECKPOINT 2 — VALIDATION_READY
        #
        # Run after the LAST corrective action,
        # not after the first maintenance/calibration.
        # -------------------------------------------------

        if (
            progress_video_path
            and
            last_corrective_index is not None
            and
            index == last_corrective_index
            and
            not validation_ready_verified
        ):

            check = run_progress_checkpoint(
                checkpoint_name=
                    "VALIDATION_READY",
                expected_state=(
                    "The robot motion appears stable "
                    "and the cell is ready to proceed "
                    "to a validation cycle."
                ),
                video_path=
                    progress_video_path,
                use_cache=
                    use_cache,
                cache_only=
                    cache_only,
            )

            timeline.append(
                check
            )

            progress_checks.append(
                check
            )

            if (
                check.get("status")
                != "VERIFIED"
            ):
                return {
                    "status":
                        "RECOVERY_PROGRESS_FAILED",
                    "failed_checkpoint":
                        "VALIDATION_READY",
                    "checkpoint_status":
                        check.get("status"),
                    "timeline":
                        timeline,
                    "progress_checks":
                        progress_checks,
                    "recommendation":
                        "PAUSE_AND_HUMAN_REVIEW",
                }

            validation_ready_verified = True

    # -----------------------------------------------------
    # Successful simulated execution
    # -----------------------------------------------------

    return {
        "status": "RECOVERY_EXECUTED",
        "root_cause":
            approval_result.get(
                "root_cause"
            ),
        "execution_mode":
            "SIMULATED",
        "timeline":
            timeline,
        "progress_checks":
            progress_checks,
        "actions_executed":
            len(actions),
        "safe_position_verified":
            safe_position_verified,
        "validation_ready_verified":
            validation_ready_verified,
    }


if __name__ == "__main__":

    # Test data only.
    # Integrated API flow will supply the actual
    # approved Gemini-generated recovery plan.

    approval_result = {
        "status":
            "RECOVERY_APPROVED",
        "approved":
            True,
        "root_cause":
            "Joint-3 Mechanical Degradation",
        "recommended_actions": [
            "Pause production cell",
            "Move robot to safe inspection position",
            "Inspect Joint-3",
            "Perform simulated Joint-3 maintenance",
            "Perform robot calibration",
            "Run validation cycle",
        ],
    }

    result = execute_recovery(
        approval_result=
            approval_result,
        progress_video_path=
            "data/videos/normal.mp4",
    )

    print(
        "--- Recovery Execution ---"
    )

    print(
        f"Status: {result['status']}"
    )

    print(
        "\nRecovery Timeline:"
    )

    for item in result.get(
        "timeline",
        []
    ):

        if (
            item["type"]
            == "ACTION"
        ):
            print(
                f"{item['timestamp']} | "
                f"{item['action']} | "
                f"{item['status']}"
            )

        elif (
            item["type"]
            == "ER_PROGRESS_CHECK"
        ):
            print(
                f"{item['timestamp']} | "
                f"ER CHECK: "
                f"{item['checkpoint']} | "
                f"{item['status']} | "
                f"Confidence: "
                f"{item.get('confidence')} | "
                f"Cache: "
                f"{item.get('cache_status')}"
            )