import json
from typing import Dict, List

from google import genai

from backend.services.cache_utils import (
    load_cache,
    save_cache,
    cache_fallback,
)


MODEL_NAME = "gemini-robotics-er-2-preview"
PROMPT_VERSION = "v1"


def predict_recovery_success(
    root_cause_result: Dict,
    evidence: List[Dict],
    recovery_plan: Dict,
    use_cache: bool = True,
    cache_only: bool = False,
) -> Dict:

    if (
        root_cause_result.get("status")
        != "ROOT_CAUSE_IDENTIFIED"
    ):
        return {
            "status":
                "PREDICTION_NOT_AVAILABLE",
            "reason":
                "Root cause not confidently identified",
        }

    if (
        recovery_plan.get("status")
        != "RECOVERY_PROPOSED"
    ):
        return {
            "status":
                "PREDICTION_NOT_AVAILABLE",
            "reason":
                "Valid recovery plan not available",
        }

    cache_input = {
        "model": MODEL_NAME,
        "prompt_version": PROMPT_VERSION,
        "root_cause":
            root_cause_result.get(
                "root_cause"
            ),
        "evidence":
            evidence,
        "recovery_plan":
            recovery_plan,
    }

    # -----------------------------------------------------
    # 1. CACHE LOOKUP
    # -----------------------------------------------------

    if use_cache:

        cached = load_cache(
            "recovery_prediction",
            cache_input,
        )

        if cached:
            return cached

    # -----------------------------------------------------
    # 2. CACHE-ONLY MODE
    # -----------------------------------------------------

    if cache_only:
        raise RuntimeError(
            "Cache-only mode enabled, but no "
            "cached recovery prediction exists."
        )

    prompt = f"""
Assess the expected success of this manufacturing
robot recovery plan.

Root cause:
{json.dumps(
    root_cause_result.get("root_cause"),
    indent=2
)}

Evidence:
{json.dumps(evidence, indent=2)}

Recovery plan:
{json.dumps(
    recovery_plan.get(
        "recommended_actions",
        []
    ),
    indent=2
)}

Recovery reasoning:
{recovery_plan.get(
    "reasoning_summary",
    ""
)}

Assess whether the proposed plan is likely to
restore normal operation.

Important:
- This is an evidence-based score, NOT a calibrated probability.
- Do not assume repair has succeeded.
- Do not invent inspection results.
- Do not invent telemetry.
- Include residual risks.
- Include verification requirements.

Return ONLY valid JSON:

{{
  "status": "PREDICTION_COMPLETED",
  "recovery_success_score": 0.0,
  "expected_post_recovery_state": "...",
  "residual_risk": "LOW | MEDIUM | HIGH",
  "risk_factors": [],
  "verification_requirements": [],
  "summary": "..."
}}
"""

    client = genai.Client()

    try:

        response = client.interactions.create(
            model=MODEL_NAME,
            input=[
                {
                    "type": "text",
                    "text": prompt,
                }
            ],
            generation_config={
                "thinking_level": "high",
            },
        )

        raw_output = (
            response.output_text
            .strip()
        )

        if raw_output.startswith("```"):

            raw_output = (
                raw_output
                .strip("`")
                .strip()
            )

            if raw_output.startswith("json"):
                raw_output = (
                    raw_output[4:]
                    .strip()
                )

        result = json.loads(
            raw_output
        )

        # -------------------------------------------------
        # Validate status
        # -------------------------------------------------

        status = result.get(
            "status"
        )

        if status != "PREDICTION_COMPLETED":
            raise ValueError(
                f"Invalid prediction status: {status}"
            )

        # -------------------------------------------------
        # Validate score
        # -------------------------------------------------

        score = result.get(
            "recovery_success_score"
        )

        if not isinstance(
            score,
            (int, float),
        ):
            return {
                "status":
                    "PREDICTION_INVALID",
                "reason":
                    "Recovery success score missing or invalid",
                "raw_result":
                    result,
            }

        if not 0 <= score <= 1:
            return {
                "status":
                    "PREDICTION_INVALID",
                "reason":
                    "Recovery success score must be between 0 and 1",
                "raw_result":
                    result,
            }

        # -------------------------------------------------
        # Validate residual risk
        # -------------------------------------------------

        residual_risk = result.get(
            "residual_risk"
        )

        if residual_risk not in {
            "LOW",
            "MEDIUM",
            "HIGH",
        }:
            raise ValueError(
                "residual_risk must be "
                "LOW, MEDIUM or HIGH"
            )

        # -------------------------------------------------
        # Validate list fields
        # -------------------------------------------------

        risk_factors = result.get(
            "risk_factors",
            [],
        )

        verification_requirements = (
            result.get(
                "verification_requirements",
                [],
            )
        )

        if not isinstance(
            risk_factors,
            list,
        ):
            raise ValueError(
                "risk_factors must be a list"
            )

        if not isinstance(
            verification_requirements,
            list,
        ):
            raise ValueError(
                "verification_requirements "
                "must be a list"
            )

        # -------------------------------------------------
        # Add metadata
        # -------------------------------------------------

        result[
            "generated_by"
        ] = MODEL_NAME

        result[
            "prompt_version"
        ] = PROMPT_VERSION

        result[
            "score_type"
        ] = (
            "evidence_based_not_calibrated_probability"
        )

        result[
            "cache_status"
        ] = "LIVE_RESULT"

        # -------------------------------------------------
        # Save successful result
        # -------------------------------------------------

        save_cache(
            "recovery_prediction",
            cache_input,
            result,
        )

        return result

    except Exception as exc:

        fallback = cache_fallback(
            "recovery_prediction",
            cache_input,
            exc,
        )

        if fallback:
            return fallback

        raise RuntimeError(
            "Recovery prediction failed "
            "and no cached result exists. "
            f"Original error: {exc}"
        ) from exc