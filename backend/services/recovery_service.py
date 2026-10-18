import json
from pathlib import Path
from typing import Dict, List

from google import genai

from backend.services.cache_utils import (
    load_cache,
    save_cache,
    cache_fallback,
)


MODEL_NAME = "gemini-robotics-er-2-preview"
PROMPT_VERSION = "v1"

BASE_DIR = Path(__file__).resolve().parents[2]

RECOVERY_ACTIONS_FILE = (
    BASE_DIR
    / "data"
    / "config"
    / "recovery_actions.json"
)


def load_allowed_actions() -> List[str]:
    with open(
        RECOVERY_ACTIONS_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        config = json.load(f)

    return config.get(
        "allowed_actions",
        [],
    )


def generate_recovery_plan(
    root_cause_result: Dict,
    evidence: List[Dict],
    use_cache: bool = True,
    cache_only: bool = False,
) -> Dict:

    if (
        root_cause_result.get("status")
        != "ROOT_CAUSE_IDENTIFIED"
    ):
        return {
            "status": "NO_RECOVERY_PLAN",
            "reason":
                "Root cause not confidently identified",
            "recommended_actions": [],
        }

    root_cause = root_cause_result.get(
        "root_cause",
        {},
    )

    allowed_actions = load_allowed_actions()

    if not allowed_actions:
        return {
            "status": "NO_RECOVERY_PLAN",
            "reason":
                "No allowed recovery actions configured",
            "recommended_actions": [],
        }

    # Cache key includes model/prompt version
    # so outdated responses are not reused.
    cache_input = {
        "model": MODEL_NAME,
        "prompt_version": PROMPT_VERSION,
        "root_cause": root_cause,
        "evidence": evidence,
        "allowed_actions": allowed_actions,
    }

    # -----------------------------------------------------
    # 1. CACHE LOOKUP
    # -----------------------------------------------------

    if use_cache:
        cached = load_cache(
            "recovery_plan",
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
            "cached recovery plan exists."
        )

    prompt = f"""
You are the recovery reasoning engine for a
manufacturing robotic incident.

Confirmed root cause:
{json.dumps(root_cause, indent=2)}

Evidence:
{json.dumps(evidence, indent=2)}

Allowed recovery actions:
{json.dumps(allowed_actions, indent=2)}

Generate the safest and most appropriate recovery sequence.

Rules:
- ONLY use actions from the allowed action list.
- Do not invent new recovery actions.
- Keep the recovery sequence minimal.
- Order actions logically.
- Human approval is mandatory.
- Return LOW, MEDIUM or HIGH risk.
- If evidence is insufficient, return NEEDS_HUMAN_REVIEW.

Return ONLY valid JSON:

{{
  "status": "RECOVERY_PROPOSED | NEEDS_HUMAN_REVIEW",
  "recommended_actions": [],
  "reasoning_summary": "...",
  "risk_level": "LOW | MEDIUM | HIGH",
  "human_approval_required": true
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
            raw_output = raw_output.strip("`").strip()

            if raw_output.startswith("json"):
                raw_output = (
                    raw_output[4:]
                    .strip()
                )

        result = json.loads(
            raw_output
        )

        # -------------------------------------------------
        # Basic response validation
        # -------------------------------------------------

        status = result.get("status")

        if status not in {
            "RECOVERY_PROPOSED",
            "NEEDS_HUMAN_REVIEW",
        }:
            raise ValueError(
                f"Invalid recovery status: {status}"
            )

        returned_actions = result.get(
            "recommended_actions",
            [],
        )

        if not isinstance(
            returned_actions,
            list,
        ):
            raise ValueError(
                "recommended_actions must be a list"
            )

        invalid_actions = [
            action
            for action in returned_actions
            if action not in allowed_actions
        ]

        if invalid_actions:
            return {
                "status":
                    "RECOVERY_PLAN_REJECTED",
                "reason":
                    "Model returned actions outside governed list",
                "invalid_actions":
                    invalid_actions,
                "recommended_actions": [],
            }

        # Ensure human approval remains mandatory
        result[
            "human_approval_required"
        ] = True

        result[
            "generated_by"
        ] = MODEL_NAME

        result[
            "prompt_version"
        ] = PROMPT_VERSION

        result[
            "cache_status"
        ] = "LIVE_RESULT"

        save_cache(
            "recovery_plan",
            cache_input,
            result,
        )

        return result

    except Exception as exc:
        fallback = cache_fallback(
            "recovery_plan",
            cache_input,
            exc,
        )

        if fallback:
            return fallback

        raise RuntimeError(
            "Recovery recommendation failed "
            "and no cached result exists. "
            f"Original error: {exc}"
        ) from exc