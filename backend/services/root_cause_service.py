import json
from pathlib import Path
from typing import Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parents[2]

ANALYSIS_CONFIG_FILE = (
    BASE_DIR
    / "data"
    / "config"
    / "analysis_config.json"
)


def load_root_cause_threshold() -> float:
    """
    Load root-cause evidence threshold dynamically
    from analysis_config.json.
    """

    if not ANALYSIS_CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Analysis config not found: "
            f"{ANALYSIS_CONFIG_FILE}"
        )

    with open(
        ANALYSIS_CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    threshold = config.get(
        "root_cause_threshold"
    )

    if not isinstance(
        threshold,
        (int, float)
    ):
        raise ValueError(
            "root_cause_threshold must be numeric."
        )

    if not 0 <= threshold <= 1:
        raise ValueError(
            "root_cause_threshold must be "
            "between 0 and 1."
        )

    return float(threshold)


def select_root_cause(
    hypothesis_results: List[Dict],
    threshold: Optional[float] = None
) -> Dict:
    """
    Select the highest-ranked hypothesis as the
    root cause only if its evidence score meets
    the configured threshold.

    The score is an evidence score, not a
    calibrated probability.
    """

    if threshold is None:
        threshold = (
            load_root_cause_threshold()
        )

    if not hypothesis_results:
        return {
            "status":
                "INSUFFICIENT_EVIDENCE",
            "root_cause":
                None,
            "score":
                0.0,
            "threshold":
                threshold,
        }

    # Defensive sorting in case caller sends
    # an unsorted list.
    ranked_results = sorted(
        hypothesis_results,
        key=lambda item:
            item.get(
                "score",
                0.0
            ),
        reverse=True,
    )

    top = ranked_results[0]

    top_score = float(
        top.get(
            "score",
            0.0
        )
    )

    if top_score >= threshold:

        return {
            "status":
                "ROOT_CAUSE_IDENTIFIED",

            "root_cause": {
                "id":
                    top.get("id"),
                "name":
                    top.get("name"),
            },

            "score":
                top_score,

            "score_type":
                "evidence_score",

            "threshold":
                threshold,

            "matched_evidence":
                top.get(
                    "matched_evidence",
                    []
                ),

            "contradicting_evidence":
                top.get(
                    "contradicting_evidence",
                    []
                ),
        }

    return {
        "status":
            "HUMAN_INVESTIGATION_REQUIRED",

        "root_cause":
            None,

        "top_candidate": {
            "id":
                top.get("id"),
            "name":
                top.get("name"),
        },

        "score":
            top_score,

        "score_type":
            "evidence_score",

        "threshold":
            threshold,

        "matched_evidence":
            top.get(
                "matched_evidence",
                []
            ),

        "reason":
            (
                "Top hypothesis evidence score "
                "did not meet the configured "
                "root-cause threshold."
            ),
    }


if __name__ == "__main__":

    hypothesis_results = [
        {
            "id": "H1",
            "name":
                "Joint-3 Mechanical Degradation",
            "score": 0.90,
            "matched_evidence": [
                "joint_3_vibration",
                "motor_current",
                "temperature",
                "unstable_motion",
            ],
            "contradicting_evidence": [],
        },
        {
            "id": "H2",
            "name":
                "Conveyor Instability",
            "score": 0.0,
            "matched_evidence": [],
            "contradicting_evidence": [],
        },
        {
            "id": "H3",
            "name":
                "Fixture Misalignment",
            "score": 0.0,
            "matched_evidence": [],
            "contradicting_evidence": [],
        },
    ]

    result = select_root_cause(
        hypothesis_results
    )

    print(
        "--- Root Cause Decision ---"
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )