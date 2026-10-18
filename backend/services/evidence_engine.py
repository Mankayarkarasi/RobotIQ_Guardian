"""
RoboIQ Guardian - Multimodal Evidence Engine

Combines deterministic telemetry anomalies with directly observable
Gemini Robotics ER visual evidence.

Important design rule:
This layer creates evidence only.

It does NOT:
- choose a root cause
- score hypotheses
- infer hidden mechanical failures
- override Gemini observations
"""

from typing import Any, Dict, List


def build_evidence(
    telemetry_result: Dict[str, Any],
    robotics_er_result: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Build multimodal evidence from:

    1. Telemetry threshold breaches
    2. Gemini Robotics ER timestamped observations
    3. High-level directly observable task outcome

    Returns
    -------
    List[Dict]
        Ordered evidence objects with unique evidence IDs.
    """

    evidence: List[Dict[str, Any]] = []

    evidence_counter = 1

    # =========================================================
    # TELEMETRY EVIDENCE
    # =========================================================

    breached_signals = (
        telemetry_result.get(
            "breached_signals",
            []
        )
        or []
    )

    for breach in breached_signals:

        signal = (
            breach.get("signal")
            or breach.get("signal_name")
            or breach.get("name")
        )

        value = (
            breach.get("actual")
            if breach.get("actual") is not None
            else breach.get("actual_value")
        )

        threshold = (
            breach.get("threshold")
        )

        if not signal:
            continue

        evidence.append({
            "evidence_id":
                f"T{evidence_counter}",

            "type":
                "telemetry",

            "signal":
                signal,

            "value":
                value,

            "threshold":
                threshold,

            "description":
                (
                    f"{signal} exceeded threshold: "
                    f"{value} > {threshold}"
                )
        })

        evidence_counter += 1

    # =========================================================
    # GEMINI ROBOTICS ER OBSERVATIONS
    # =========================================================

    observations = (
        robotics_er_result.get(
            "observations",
            []
        )
        or []
    )

    for observation in observations:

        description = (
            observation.get("observation")
            or observation.get("description")
            or ""
        )

        if not description:
            continue

        evidence.append({
            "evidence_id":
                f"V{evidence_counter}",

            "type":
                "visual",

            "timestamp_seconds":
                observation.get(
                    "timestamp_seconds"
                ),

            "description":
                description,

            "confidence":
                observation.get(
                    "confidence"
                )
        })

        evidence_counter += 1

    # =========================================================
    # DIRECTLY OBSERVED TASK FAILURE
    # =========================================================
    #
    # Gemini may observe a failed task even when the arm motion
    # itself remains smooth/stable.
    #
    # Example:
    # - operation_status = ABNORMAL
    # - motion_stability = STABLE
    # - task_completed = false
    #
    # This is valid visual evidence and should not be discarded
    # merely because unstable motion was not observed.
    # =========================================================

    operation_status = (
        str(
            robotics_er_result.get(
                "operation_status",
                ""
            )
        )
        .strip()
        .upper()
    )

    task_completed = (
        robotics_er_result.get(
            "task_completed"
        )
    )

    if (
        operation_status == "ABNORMAL"
        or task_completed is False
    ):

        evidence.append({
            "evidence_id":
                f"V{evidence_counter}",

            "type":
                "visual",

            "signal":
                "task_failure",

            "description":
                (
                    "Gemini Robotics ER observed an abnormal "
                    "operation or an incomplete robotic task."
                ),

            "confidence":
                _derive_task_failure_confidence(
                    robotics_er_result
                )
        })

        evidence_counter += 1

    # =========================================================
    # DIRECTLY OBSERVED UNSTABLE MOTION
    # =========================================================

    motion_stability = (
        str(
            robotics_er_result.get(
                "motion_stability",
                ""
            )
        )
        .strip()
        .upper()
    )

    if motion_stability == "UNSTABLE":

        evidence.append({
            "evidence_id":
                f"V{evidence_counter}",

            "type":
                "visual",

            "signal":
                "unstable_motion",

            "description":
                (
                    "Gemini Robotics ER directly observed "
                    "unstable robot motion."
                ),

            "confidence":
                _derive_visual_confidence(
                    robotics_er_result
                )
        })

        evidence_counter += 1

    return evidence


def _derive_visual_confidence(
    robotics_er_result: Dict[str, Any]
) -> float:
    """
    Derive representative confidence from Gemini observations.

    This is not a probability of root cause.
    It is only the mean confidence of visual observations.
    """

    observations = (
        robotics_er_result.get(
            "observations",
            []
        )
        or []
    )

    confidence_values = []

    for observation in observations:

        confidence = observation.get(
            "confidence"
        )

        if isinstance(
            confidence,
            (int, float)
        ):

            if 0 <= confidence <= 1:

                confidence_values.append(
                    float(confidence)
                )

    if not confidence_values:
        return 0.8

    return round(
        sum(confidence_values)
        / len(confidence_values),
        4
    )


def _derive_task_failure_confidence(
    robotics_er_result: Dict[str, Any]
) -> float:
    """
    Determine confidence for task-failure evidence.

    Prefer observations containing language associated with
    failure/incomplete task. Otherwise use overall visual
    observation confidence.
    """

    failure_terms = (
        "fail",
        "failed",
        "failing",
        "empty",
        "miss",
        "unable",
        "incomplete",
        "not complete",
        "warning"
    )

    observations = (
        robotics_er_result.get(
            "observations",
            []
        )
        or []
    )

    matching_confidences = []

    for observation in observations:

        description = str(
            observation.get(
                "observation",
                ""
            )
        ).lower()

        if any(
            term in description
            for term in failure_terms
        ):

            confidence = (
                observation.get(
                    "confidence"
                )
            )

            if isinstance(
                confidence,
                (int, float)
            ):

                if 0 <= confidence <= 1:

                    matching_confidences.append(
                        float(confidence)
                    )

    if matching_confidences:

        return round(
            max(
                matching_confidences
            ),
            4
        )

    return _derive_visual_confidence(
        robotics_er_result
    )


# =============================================================
# LOCAL TEST
# =============================================================

if __name__ == "__main__":

    sample_telemetry = {
        "status": "FAILURE",
        "breached_signals": [
            {
                "signal":
                    "joint_3_vibration",
                "actual":
                    5.7,
                "threshold":
                    2.5
            },
            {
                "signal":
                    "motor_current",
                "actual":
                    10.2,
                "threshold":
                    8.5
            },
            {
                "signal":
                    "temperature",
                "actual":
                    81,
                "threshold":
                    75
            }
        ]
    }

    sample_er = {
        "operation_status":
            "ABNORMAL",

        "motion_stability":
            "STABLE",

        "task_completed":
            False,

        "observations": [
            {
                "timestamp_seconds":
                    6.0,

                "observation":
                    (
                        "The arm retracts upwards "
                        "with an empty gripper, "
                        "failing to pick up the part."
                    ),

                "confidence":
                    0.95
            }
        ]
    }

    for item in build_evidence(
        sample_telemetry,
        sample_er
    ):

        print(item)