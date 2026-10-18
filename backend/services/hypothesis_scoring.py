"""
RoboIQ Guardian - Hypothesis Scoring

Scores configured failure hypotheses against multimodal evidence.

Important:
Scores are Evidence Scores.

They are NOT:
- calibrated probabilities
- model confidence probabilities
- guaranteed root-cause probabilities

The scoring logic is deterministic and configuration-driven.
"""

import json

from pathlib import Path
from typing import Any, Dict, List, Set


# =============================================================
# PATHS
# =============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

WEIGHTS_FILE = (
    BASE_DIR
    / "data"
    / "config"
    / "evidence_weights.json"
)


# =============================================================
# LOAD WEIGHTS
# =============================================================

def load_evidence_weights() -> Dict[str, float]:

    if not WEIGHTS_FILE.exists():

        raise FileNotFoundError(
            f"Evidence weights file not found: "
            f"{WEIGHTS_FILE}"
        )

    with open(
        WEIGHTS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        weights = json.load(
            file
        )

    if not isinstance(
        weights,
        dict
    ):

        raise ValueError(
            "evidence_weights.json must contain "
            "a JSON object."
        )

    validated = {}

    for key, value in weights.items():

        if not isinstance(
            value,
            (int, float)
        ):

            raise ValueError(
                f"Weight for '{key}' must be numeric."
            )

        if value < 0 or value > 1:

            raise ValueError(
                f"Weight for '{key}' must be "
                "between 0 and 1."
            )

        validated[
            str(key)
        ] = float(
            value
        )

    return validated


# =============================================================
# EVIDENCE TAG EXTRACTION
# =============================================================

def extract_evidence_tags(
    evidence: List[Dict[str, Any]]
) -> List[str]:
    """
    Convert raw multimodal evidence into normalized evidence tags.

    Explicit 'signal' values are always preferred.

    Visual free text is additionally mapped into semantic tags
    where appropriate.
    """

    tags: List[str] = []

    for item in evidence:

        if not isinstance(
            item,
            dict
        ):
            continue

        # -----------------------------------------------------
        # Explicit structured signal
        # -----------------------------------------------------

        signal = (
            item.get(
                "signal"
            )
        )

        if signal:

            signal = str(
                signal
            ).strip()

            if signal:

                tags.append(
                    signal
                )

        # -----------------------------------------------------
        # Visual semantic mapping
        # -----------------------------------------------------

        if (
            item.get(
                "type"
            )
            == "visual"
        ):

            description = str(
                item.get(
                    "description"
                )
                or item.get(
                    "observation"
                )
                or ""
            ).lower()

            if description:

                # Unstable motion
                unstable_terms = (
                    "unstable",
                    "oscillat",
                    "jerk",
                    "irregular motion",
                    "abnormal motion",
                    "abrupt movement",
                    "overshoot"
                )

                if any(
                    term in description
                    for term in unstable_terms
                ):

                    tags.append(
                        "unstable_motion"
                    )

                # Placement deviation
                placement_terms = (
                    "misalign",
                    "placement deviation",
                    "incorrect placement",
                    "wrong position",
                    "missed placement",
                    "placement correction"
                )

                if any(
                    term in description
                    for term in placement_terms
                ):

                    tags.append(
                        "placement_deviation"
                    )

                # Conveyor motion abnormality
                conveyor_terms = (
                    "conveyor unstable",
                    "conveyor vibration",
                    "conveyor oscillation",
                    "conveyor jerking",
                    "irregular conveyor",
                    "abnormal conveyor"
                )

                if any(
                    term in description
                    for term in conveyor_terms
                ):

                    tags.append(
                        "conveyor_motion_abnormal"
                    )

                # Task failure
                task_failure_terms = (
                    "fails to",
                    "failed to",
                    "failing to",
                    "empty gripper",
                    "task failed",
                    "task incomplete",
                    "unable to",
                    "did not complete",
                    "warning light"
                )

                if any(
                    term in description
                    for term in task_failure_terms
                ):

                    tags.append(
                        "task_failure"
                    )

    # Preserve order while removing duplicates.
    return list(
        dict.fromkeys(
            tags
        )
    )


# =============================================================
# SUPPORTING-EVIDENCE FIELD NORMALIZATION
# =============================================================

def get_supporting_evidence(
    hypothesis: Dict[str, Any]
) -> List[str]:
    """
    Support both likely hypothesis configuration names.

    Preferred:
        supporting_evidence

    Backward-compatible:
        evidence
        signals
        indicators
    """

    possible_fields = (
        "supporting_evidence",
        "evidence",
        "signals",
        "indicators"
    )

    for field in possible_fields:

        value = (
            hypothesis.get(
                field
            )
        )

        if isinstance(
            value,
            list
        ):

            return [
                str(item)
                for item in value
            ]

    return []


# =============================================================
# CONTRADICTION FIELD
# =============================================================

def get_contradicting_evidence(
    hypothesis: Dict[str, Any]
) -> List[str]:

    value = (
        hypothesis.get(
            "contradicted_by",
            []
        )
    )

    if not isinstance(
        value,
        list
    ):

        return []

    return [
        str(item)
        for item in value
    ]


# =============================================================
# HYPOTHESIS SCORING
# =============================================================

def score_hypotheses(
    evidence: List[Dict[str, Any]],
    hypotheses: Any
) -> List[Dict[str, Any]]:
    """
    Score all configured hypotheses.

    Positive evidence contributes configured weight.

    Contradicting evidence, when configured, subtracts its
    configured weight.

    Final score is clamped to [0, 1].
    """

    weights = (
        load_evidence_weights()
    )

    evidence_tags = (
        extract_evidence_tags(
            evidence
        )
    )

    evidence_tag_set: Set[str] = set(
        evidence_tags
    )

    # ---------------------------------------------------------
    # Normalize hypothesis structure.
    #
    # Allows:
    # [
    #   {...}
    # ]
    #
    # or:
    # {
    #   "hypotheses": [...]
    # }
    # ---------------------------------------------------------

    if isinstance(
        hypotheses,
        dict
    ):

        hypothesis_list = (
            hypotheses.get(
                "hypotheses",
                []
            )
        )

    else:

        hypothesis_list = (
            hypotheses
        )

    if not isinstance(
        hypothesis_list,
        list
    ):

        raise ValueError(
            "Hypotheses must be a list or "
            "an object containing a "
            "'hypotheses' list."
        )

    results = []

    for hypothesis in hypothesis_list:

        if not isinstance(
            hypothesis,
            dict
        ):
            continue

        hypothesis_id = (
            hypothesis.get(
                "id"
            )
        )

        hypothesis_name = (
            hypothesis.get(
                "name"
            )
        )

        supporting = (
            get_supporting_evidence(
                hypothesis
            )
        )

        contradicting = (
            get_contradicting_evidence(
                hypothesis
            )
        )

        matched_evidence = [
            tag
            for tag in supporting
            if tag in evidence_tag_set
        ]

        contradicting_matches = [
            tag
            for tag in contradicting
            if tag in evidence_tag_set
        ]

        positive_score = sum(
            weights.get(
                tag,
                0.0
            )
            for tag
            in matched_evidence
        )

        contradiction_score = sum(
            weights.get(
                tag,
                0.0
            )
            for tag
            in contradicting_matches
        )

        score = (
            positive_score
            - contradiction_score
        )

        score = max(
            0.0,
            min(
                1.0,
                score
            )
        )

        results.append({

            "id":
                hypothesis_id,

            "name":
                hypothesis_name,

            "score":
                round(
                    score,
                    4
                ),

            "score_type":
                "evidence_score",

            "matched_evidence":
                matched_evidence,

            "contradicting_evidence":
                contradicting_matches,

            "evidence_tags":
                evidence_tags
        })

    # Highest evidence score first.
    results.sort(
        key=lambda item:
            item.get(
                "score",
                0
            ),
        reverse=True
    )

    return results


# =============================================================
# LOCAL TEST
# =============================================================

if __name__ == "__main__":

    sample_evidence = [
        {
            "evidence_id":
                "T1",
            "type":
                "telemetry",
            "signal":
                "cycle_time"
        },
        {
            "evidence_id":
                "T2",
            "type":
                "telemetry",
            "signal":
                "position_error"
        },
        {
            "evidence_id":
                "T3",
            "type":
                "telemetry",
            "signal":
                "joint_3_vibration"
        },
        {
            "evidence_id":
                "T4",
            "type":
                "telemetry",
            "signal":
                "motor_current"
        },
        {
            "evidence_id":
                "T5",
            "type":
                "telemetry",
            "signal":
                "temperature"
        },
        {
            "evidence_id":
                "V6",
            "type":
                "visual",
            "signal":
                "task_failure",
            "description":
                (
                    "Robot failed to complete "
                    "the pick operation."
                )
        }
    ]

    sample_hypotheses = {
        "hypotheses": [
            {
                "id":
                    "H1",
                "name":
                    "Joint-3 Mechanical Degradation",
                "supporting_evidence": [
                    "joint_3_vibration",
                    "motor_current",
                    "temperature",
                    "unstable_motion",
                    "task_failure"
                ]
            },
            {
                "id":
                    "H2",
                "name":
                    "Conveyor Instability",
                "supporting_evidence": [
                    "cycle_time",
                    "conveyor_motion_abnormal"
                ]
            },
            {
                "id":
                    "H3",
                "name":
                    "Fixture Misalignment",
                "supporting_evidence": [
                    "position_error",
                    "placement_deviation",
                    "task_failure"
                ]
            }
        ]
    }

    results = (
        score_hypotheses(
            sample_evidence,
            sample_hypotheses
        )
    )

    print(
        json.dumps(
            results,
            indent=2
        )
    )