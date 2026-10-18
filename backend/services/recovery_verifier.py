"""
RoboIQ Guardian Final Recovery Verification

Final production-resume decision requires BOTH:

1. Post-recovery telemetry within configured limits
2. Gemini Robotics ER 2 visual verification of stable operation

Gemini provides embodied visual verification.
Deterministic telemetry rules provide industrial safety validation.
"""

import json
from pathlib import Path
from typing import Dict, Any

from backend.services.robotics_er_service import (
    analyze_video
)


BASE_DIR = Path(__file__).resolve().parents[2]


SIGNAL_THRESHOLD_KEYS = {
    "cycle_time":
        "cycle_time_max",

    "position_error":
        "position_error_max",

    "joint_3_vibration":
        "joint_3_vibration_max",

    "motor_current":
        "motor_current_max",

    "temperature":
        "temperature_max",
}


def load_json(
    path: Path
) -> Dict[str, Any]:
    """
    Load JSON file.
    """

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def verify_telemetry(
    telemetry: Dict,
    thresholds: Dict
) -> Dict:
    """
    Verify post-recovery telemetry against
    configured safety thresholds.

    Missing values do NOT automatically pass.
    """

    checks = {}

    for (
        signal,
        threshold_key
    ) in SIGNAL_THRESHOLD_KEYS.items():

        actual_value = telemetry.get(
            signal
        )

        threshold_value = thresholds.get(
            threshold_key
        )

        if actual_value is None:

            checks[signal] = {
                "status": "MISSING",
                "actual": None,
                "threshold":
                    threshold_value,
                "passed": False,
            }

            continue

        if threshold_value is None:

            checks[signal] = {
                "status":
                    "NO_THRESHOLD",
                "actual":
                    actual_value,
                "threshold":
                    None,
                "passed":
                    False,
            }

            continue

        passed = (
            actual_value
            <= threshold_value
        )

        checks[signal] = {
            "status":
                "PASS"
                if passed
                else "FAIL",

            "actual":
                actual_value,

            "threshold":
                threshold_value,

            "passed":
                passed,
        }

    telemetry_pass = all(
        item["passed"]
        for item in checks.values()
    )

    return {
        "passed":
            telemetry_pass,
        "checks":
            checks,
    }


def verify_visual_state(
    video_path: str,
    use_cache: bool = True,
    cache_only: bool = False,
) -> Dict:
    """
    Verify post-recovery physical state using
    Gemini Robotics ER 2.

    Uses robotics_er_service, so its video cache
    and quota fallback are automatically reused.
    """

    robotics_er_result = (
        analyze_video(
            video_path=video_path,
            use_cache=use_cache,
            cache_only=cache_only,
        )
    )

    parse_success = (
        robotics_er_result.get(
            "parse_status"
        )
        == "SUCCESS"
    )

    operation_normal = (
        robotics_er_result.get(
            "operation_status"
        )
        == "NORMAL"
    )

    motion_stable = (
        robotics_er_result.get(
            "motion_stability"
        )
        == "STABLE"
    )

    task_completed = (
        robotics_er_result.get(
            "task_completed"
        )
        is True
    )

    visual_pass = all([
        parse_success,
        operation_normal,
        motion_stable,
        task_completed,
    ])

    return {
        "passed":
            visual_pass,

        "checks": {
            "parse_success":
                parse_success,

            "operation_normal":
                operation_normal,

            "motion_stable":
                motion_stable,

            "task_completed":
                task_completed,
        },

        "robotics_er_result":
            robotics_er_result,

        "cache_status":
            robotics_er_result.get(
                "cache_status"
            ),
    }


def verify_recovery(
    telemetry: Dict,
    thresholds: Dict,
    video_path: str,
    use_cache: bool = True,
    cache_only: bool = False,
) -> Dict:
    """
    Perform final recovery verification.

    Recovery is verified ONLY if:

    - all post-recovery telemetry passes
    AND
    - Gemini Robotics ER confirms normal,
      stable and completed physical operation.
    """

    telemetry_result = (
        verify_telemetry(
            telemetry,
            thresholds
        )
    )

    try:

        visual_result = (
            verify_visual_state(
                video_path=
                    video_path,

                use_cache=
                    use_cache,

                cache_only=
                    cache_only,
            )
        )

    except Exception as exc:

        return {
            "status":
                "RECOVERY_FAILED",

            "telemetry_validation":
                telemetry_result,

            "visual_validation": {
                "passed":
                    False,

                "reason":
                    str(exc),
            },

            "telemetry_pass":
                telemetry_result.get(
                    "passed",
                    False
                ),

            "visual_pass":
                False,

            "recommendation":
                "KEEP_PRODUCTION_PAUSED",
        }

    telemetry_pass = (
        telemetry_result.get(
            "passed",
            False
        )
    )

    visual_pass = (
        visual_result.get(
            "passed",
            False
        )
    )

    if (
        telemetry_pass
        and visual_pass
    ):

        status = (
            "RECOVERY_VERIFIED"
        )

        recommendation = (
            "RESUME_PRODUCTION"
        )

    else:

        status = (
            "RECOVERY_FAILED"
        )

        recommendation = (
            "KEEP_PRODUCTION_PAUSED"
        )

    return {
        "status":
            status,

        "telemetry_pass":
            telemetry_pass,

        "visual_pass":
            visual_pass,

        "telemetry_validation":
            telemetry_result,

        "visual_validation":
            visual_result,

        "recommendation":
            recommendation,
    }


if __name__ == "__main__":

    telemetry_file = (
        BASE_DIR
        / "data"
        / "telemetry"
        / "normal.json"
    )

    thresholds_file = (
        BASE_DIR
        / "data"
        / "config"
        / "thresholds.json"
    )

    video_file = (
        BASE_DIR
        / "data"
        / "videos"
        / "normal.mp4"
    )

    telemetry = load_json(
        telemetry_file
    )

    thresholds = load_json(
        thresholds_file
    )

    result = verify_recovery(
        telemetry=
            telemetry,

        thresholds=
            thresholds,

        video_path=
            str(video_file),

        # After you have created the normal
        # video cache, you can change this
        # to True for zero Gemini calls.
        cache_only=False,
    )

    print(
        "--- Recovery Verification ---"
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )