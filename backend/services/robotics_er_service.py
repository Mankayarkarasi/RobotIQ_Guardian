"""
RoboIQ Guardian
Gemini Robotics ER 2 Video Analysis Service

Purpose
-------
Analyze industrial robotic-arm video using Gemini Robotics ER 2.

The service is intentionally restricted to directly observable
physical behavior. It must NOT:

- use telemetry
- infer hidden mechanical root causes
- recommend maintenance/recovery actions
- use offline ground truth

Responsibilities
----------------
1. Analyze robot video.
2. Determine observable operation status.
3. Determine observable motion stability.
4. Determine whether the task was completed.
5. Produce timestamped visual observations.
6. Persist successful Gemini results to cache.
7. Reuse cached results during repeated PoC/demo runs.

Cache behavior
--------------
Default:
    Use cache when available.
    Otherwise call Gemini and save the successful result.

--no-cache:
    Force a fresh Gemini call.
    Successful result is still written to cache.

--cache-only:
    Never call Gemini.
    Return cached result only.

Example
-------
python -m backend.services.robotics_er_service \
    --video data/videos/normal.mp4

python -m backend.services.robotics_er_service \
    --video data/videos/failure.mp4 \
    --no-cache

python -m backend.services.robotics_er_service \
    --video data/videos/failure.mp4 \
    --cache-only
"""

import argparse
import hashlib
import json
import os
import re
import time

from pathlib import Path
from typing import Any, Dict, Optional

from google import genai
from google.genai import types


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

CACHE_DIR = (
    BASE_DIR
    / "data"
    / "cache"
)

CACHE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# GEMINI MODEL
# ============================================================

MODEL_NAME = (
    "gemini-robotics-er-2-preview"
)

PROMPT_VERSION = "v2-motion-analysis"


# ============================================================
# ROBOTICS ER PROMPT
# ============================================================

ANALYSIS_PROMPT = """
You are analyzing a short industrial robotic-arm video.

Your task is to inspect ONLY directly observable physical behavior
visible in the supplied video.

Do NOT:
- use telemetry
- assume sensor values
- infer hidden mechanical root causes
- diagnose internal component failure
- recommend maintenance
- recommend recovery actions
- invent events that are not visible
- use information outside the supplied video

Carefully inspect the COMPLETE video sequence.

Evaluate the following:

1. OPERATION STATUS

Determine whether the visible robotic operation appears:

NORMAL
ABNORMAL
UNCERTAIN

Use ABNORMAL only when directly observable physical behavior differs
from a smooth, controlled industrial robot operation.

Use UNCERTAIN when the video does not provide enough visual evidence
to make a reliable determination.


2. MOTION STABILITY

Determine whether visible robot motion is:

STABLE
UNSTABLE
UNCERTAIN

When assessing motion stability, carefully inspect for subtle
physical abnormalities including:

- sudden jerks
- oscillation
- vibration-like movement
- hesitation
- unexpected pauses
- repeated corrective movement
- overshoot
- irregular trajectory
- unstable gripper positioning
- abnormal approach motion
- abnormal withdrawal motion
- placement correction
- abrupt direction changes
- visible deviation from a smooth controlled trajectory

Do NOT classify motion as UNSTABLE unless one or more such behaviors
is actually visible.

Do NOT assume instability merely because this is an industrial
failure-analysis task.


3. TASK COMPLETION

Determine whether the intended visible task appears to have been
completed.

Return:

true
false
null

Use null if task completion cannot be determined visually.


4. TIMESTAMPED OBSERVATIONS

Provide concise observations at important points in the video.

Each observation must describe ONLY something directly visible.

Good examples:

"The arm pauses briefly during approach to the fixture."

"The end-effector makes a corrective lateral movement before placement."

"The robot retracts smoothly after releasing the component."

Bad examples:

"Joint-3 bearing degradation causes vibration."

"The motor current is excessive."

"The robot requires maintenance."

Those are not directly observable from video.


5. SUMMARY

Provide a short factual summary of the observed physical behavior.

Do not provide:
- root-cause diagnosis
- maintenance recommendation
- recovery recommendation


Return ONLY valid JSON using exactly this structure:

{
  "operation_status": "NORMAL|ABNORMAL|UNCERTAIN",
  "motion_stability": "STABLE|UNSTABLE|UNCERTAIN",
  "task_completed": true,
  "observations": [
    {
      "timestamp_seconds": 0.0,
      "observation": "Directly observable physical event",
      "confidence": 0.0
    }
  ],
  "summary": "Concise factual description of observable robot behavior"
}

Confidence must be between 0.0 and 1.0.

Do not include Markdown.
Do not wrap the JSON in code fences.
"""


# ============================================================
# FILE HASH
# ============================================================

def compute_file_hash(
    file_path: Path,
    chunk_size: int = 1024 * 1024
) -> str:
    """
    Compute deterministic SHA256 hash of video contents.

    Using file content rather than absolute path allows cache
    reuse after moving/exporting the project.
    """

    sha256 = hashlib.sha256()

    with open(
        file_path,
        "rb"
    ) as file:

        while True:

            chunk = file.read(
                chunk_size
            )

            if not chunk:
                break

            sha256.update(
                chunk
            )

    return sha256.hexdigest()


# ============================================================
# CACHE PATH
# ============================================================

def get_cache_path(
    video_path: Path
) -> Path:
    """
    Generate deterministic cache filename.

    Example:
    normal_2e29ad69823d_er.json
    """

    video_hash = compute_file_hash(
        video_path
    )

    short_hash = video_hash[:12]

    safe_stem = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        video_path.stem
    )

    return (
        CACHE_DIR
        / f"{safe_stem}_{short_hash}_er.json"
    )


# ============================================================
# CACHE LOAD
# ============================================================

def load_cached_result(
    cache_path: Path
) -> Optional[Dict[str, Any]]:

    if not cache_path.exists():
        return None

    try:

        with open(
            cache_path,
            "r",
            encoding="utf-8"
        ) as file:

            result = json.load(
                file
            )

        if not isinstance(
            result,
            dict
        ):
            return None

        return result

    except (
        OSError,
        json.JSONDecodeError
    ):

        return None


# ============================================================
# CACHE SAVE
# ============================================================

def save_cached_result(
    cache_path: Path,
    result: Dict[str, Any]
) -> None:
    """
    Atomically save successful Gemini result.

    Runtime-only cache_status is not persisted.
    """

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    persisted_result = dict(
        result
    )

    persisted_result.pop(
        "cache_status",
        None
    )

    temporary_path = (
        cache_path.with_suffix(
            ".tmp"
        )
    )

    with open(
        temporary_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            persisted_result,
            file,
            indent=2,
            ensure_ascii=False
        )

    os.replace(
        temporary_path,
        cache_path
    )


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(
    response_text: str
) -> Dict[str, Any]:

    if not response_text:
        raise ValueError(
            "Gemini returned an empty response."
        )

    cleaned = (
        response_text
        .strip()
    )

    # Defensive handling in case the model still returns
    # Markdown code fences.
    if cleaned.startswith(
        "```"
    ):

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned
        )

    try:

        result = json.loads(
            cleaned
        )

    except json.JSONDecodeError:

        # Last-resort extraction of the first JSON object.
        start = cleaned.find(
            "{"
        )

        end = cleaned.rfind(
            "}"
        )

        if (
            start == -1
            or end == -1
            or end <= start
        ):

            raise ValueError(
                "Gemini response did not contain valid JSON."
            )

        candidate = cleaned[
            start:end + 1
        ]

        try:

            result = json.loads(
                candidate
            )

        except json.JSONDecodeError as exc:

            raise ValueError(
                "Gemini response contained malformed JSON."
            ) from exc

    if not isinstance(
        result,
        dict
    ):

        raise ValueError(
            "Gemini response must be a JSON object."
        )

    return result


# ============================================================
# RESULT VALIDATION
# ============================================================

def validate_result(
    result: Dict[str, Any]
) -> Dict[str, Any]:

    valid_operation_statuses = {
        "NORMAL",
        "ABNORMAL",
        "UNCERTAIN"
    }

    valid_motion_statuses = {
        "STABLE",
        "UNSTABLE",
        "UNCERTAIN"
    }

    operation_status = (
        str(
            result.get(
                "operation_status",
                ""
            )
        )
        .strip()
        .upper()
    )

    motion_stability = (
        str(
            result.get(
                "motion_stability",
                ""
            )
        )
        .strip()
        .upper()
    )

    if (
        operation_status
        not in valid_operation_statuses
    ):

        raise ValueError(
            "Invalid operation_status returned "
            f"by Gemini: {operation_status}"
        )

    if (
        motion_stability
        not in valid_motion_statuses
    ):

        raise ValueError(
            "Invalid motion_stability returned "
            f"by Gemini: {motion_stability}"
        )

    task_completed = (
        result.get(
            "task_completed"
        )
    )

    if (
        task_completed
        not in (
            True,
            False,
            None
        )
    ):

        raise ValueError(
            "task_completed must be "
            "true, false, or null."
        )

    observations = (
        result.get(
            "observations",
            []
        )
    )

    if observations is None:
        observations = []

    if not isinstance(
        observations,
        list
    ):

        raise ValueError(
            "observations must be a list."
        )

    validated_observations = []

    for index, observation in enumerate(
        observations
    ):

        if not isinstance(
            observation,
            dict
        ):

            raise ValueError(
                f"Observation {index} "
                "must be an object."
            )

        timestamp = (
            observation.get(
                "timestamp_seconds"
            )
        )

        description = (
            observation.get(
                "observation"
            )
        )

        confidence = (
            observation.get(
                "confidence"
            )
        )

        try:

            timestamp = float(
                timestamp
            )

        except (
            TypeError,
            ValueError
        ) as exc:

            raise ValueError(
                f"Observation {index} has "
                "invalid timestamp_seconds."
            ) from exc

        if timestamp < 0:

            raise ValueError(
                f"Observation {index} timestamp "
                "cannot be negative."
            )

        if (
            not isinstance(
                description,
                str
            )
            or not description.strip()
        ):

            raise ValueError(
                f"Observation {index} has "
                "invalid observation text."
            )

        try:

            confidence = float(
                confidence
            )

        except (
            TypeError,
            ValueError
        ) as exc:

            raise ValueError(
                f"Observation {index} has "
                "invalid confidence."
            ) from exc

        if not (
            0.0
            <= confidence
            <= 1.0
        ):

            raise ValueError(
                f"Observation {index} confidence "
                "must be between 0 and 1."
            )

        validated_observations.append({
            "timestamp_seconds":
                round(
                    timestamp,
                    2
                ),

            "observation":
                description.strip(),

            "confidence":
                round(
                    confidence,
                    4
                )
        })

    summary = (
        result.get(
            "summary",
            ""
        )
    )

    if not isinstance(
        summary,
        str
    ):

        summary = str(
            summary
        )

    validated_result = {

        "operation_status":
            operation_status,

        "motion_stability":
            motion_stability,

        "task_completed":
            task_completed,

        "observations":
            validated_observations,

        "summary":
            summary.strip(),

        "parse_status":
            "SUCCESS",

        "generated_by":
            MODEL_NAME
    }

    return validated_result


# ============================================================
# GEMINI CLIENT
# ============================================================

def create_client() -> genai.Client:
    """
    Create Gemini client.

    google-genai can obtain authentication from the environment.

    If GEMINI_API_KEY is explicitly available, use it.
    Otherwise create the client using the environment's configured
    Google authentication.
    """

    api_key = (
        os.getenv(
            "GEMINI_API_KEY"
        )
        or os.getenv(
            "GOOGLE_API_KEY"
        )
    )

    if api_key:

        return genai.Client(
            api_key=api_key
        )

    return genai.Client()


# ============================================================
# WAIT FOR VIDEO PROCESSING
# ============================================================

def wait_for_uploaded_file(
    client: genai.Client,
    uploaded_file: Any,
    timeout_seconds: int = 180
) -> Any:
    """
    Wait until Gemini finishes processing the uploaded video.
    """

    start_time = time.time()

    file_obj = uploaded_file

    while True:

        state_obj = getattr(
            file_obj,
            "state",
            None
        )

        state_name = getattr(
            state_obj,
            "name",
            None
        )

        if state_name is None:

            state_name = str(
                state_obj or ""
            )

        state_name = (
            state_name
            .upper()
        )

        if (
            "ACTIVE"
            in state_name
        ):

            return file_obj

        if (
            "FAILED"
            in state_name
        ):

            raise RuntimeError(
                "Gemini failed to process "
                "the uploaded video."
            )

        # Some SDK/runtime versions may not expose
        # a processing state. In that case continue.
        if not state_name:

            return file_obj

        if (
            time.time()
            - start_time
            > timeout_seconds
        ):

            raise TimeoutError(
                "Timed out waiting for Gemini "
                "to process the video."
            )

        time.sleep(
            2
        )

        file_obj = (
            client.files.get(
                name=uploaded_file.name
            )
        )


# ============================================================
# LIVE GEMINI CALL
# ============================================================

def call_gemini(
    video_path: Path
) -> Dict[str, Any]:

    client = create_client()

    print(
        f"Uploading video: "
        f"{video_path}"
    )

    uploaded_file = (
        client.files.upload(
            file=str(
                video_path
            )
        )
    )

    uploaded_file = (
        wait_for_uploaded_file(
            client,
            uploaded_file
        )
    )

    print(
        "Running Gemini Robotics ER 2 analysis..."
    )

    response = (
        client.models.generate_content(
            model=MODEL_NAME,

            contents=[
                uploaded_file,
                ANALYSIS_PROMPT
            ],

            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type=(
                    "application/json"
                )
            )
        )
    )

    response_text = (
        response.text
        if response.text
        else ""
    )

    parsed_result = (
        extract_json(
            response_text
        )
    )

    validated_result = (
        validate_result(
            parsed_result
        )
    )

    return validated_result


# ============================================================
# MAIN SERVICE FUNCTION
# ============================================================

def analyze_video(
    video_path: str,
    use_cache: bool = True,
    cache_only: bool = False
) -> Dict[str, Any]:
    """
    Analyze industrial robot video.

    Parameters
    ----------
    video_path:
        Video file path.

    use_cache:
        If True, read existing cached result before
        making a Gemini request.

    cache_only:
        If True, Gemini is NEVER called.
        Cached result must already exist.

    Returns
    -------
    Dict containing:

    operation_status
    motion_stability
    task_completed
    observations
    summary
    parse_status
    generated_by
    cache_status
    """

    resolved_video_path = (
        Path(
            video_path
        )
        .expanduser()
        .resolve()
    )

    if not resolved_video_path.exists():

        raise FileNotFoundError(
            f"Video file not found: "
            f"{resolved_video_path}"
        )

    if not resolved_video_path.is_file():

        raise ValueError(
            f"Video path is not a file: "
            f"{resolved_video_path}"
        )

    cache_path = (
        get_cache_path(
            resolved_video_path
        )
    )

    # ========================================================
    # CACHE READ
    # ========================================================

    if (
        use_cache
        or cache_only
    ):

        cached_result = (
            load_cached_result(
                cache_path
            )
        )

        if cached_result:

            validated_cached_result = (
                validate_result(
                    cached_result
                )
            )

            validated_cached_result[
                "cache_status"
            ] = "CACHE_HIT"

            print(
                "Using cached Robotics ER result."
            )

            return (
                validated_cached_result
            )

    # ========================================================
    # CACHE-ONLY MODE
    # ========================================================

    if cache_only:

        raise FileNotFoundError(
            "Robotics ER cache not found for "
            f"{resolved_video_path.name}. "
            f"Expected cache: {cache_path}"
        )

    # ========================================================
    # LIVE GEMINI ANALYSIS
    # ========================================================

    try:

        live_result = (
            call_gemini(
                resolved_video_path
            )
        )

        # Successful result is ALWAYS cached,
        # including when --no-cache forced the call.
        save_cached_result(
            cache_path,
            live_result
        )

        print(
            "Robotics ER result cached at:"
        )

        print(
            cache_path
        )

        live_result[
            "cache_status"
        ] = "LIVE_RESULT"

        return live_result

    except Exception as exc:

        # ====================================================
        # FALLBACK
        # ====================================================
        #
        # If Gemini temporarily fails and an older valid
        # cached result exists, use it.
        #
        # This helps protect the PoC from quota/high-demand
        # failures during demonstrations.
        # ====================================================

        fallback = (
            load_cached_result(
                cache_path
            )
        )

        if fallback:

            validated_fallback = (
                validate_result(
                    fallback
                )
            )

            validated_fallback[
                "cache_status"
            ] = "CACHE_FALLBACK"

            validated_fallback[
                "live_error"
            ] = str(
                exc
            )

            print(
                "Live Robotics ER call failed."
            )

            print(
                "Using cached fallback result."
            )

            return (
                validated_fallback
            )

        raise RuntimeError(
            "Gemini Robotics ER analysis failed "
            "and no cached result is available. "
            f"Error: {str(exc)}"
        ) from exc


# ============================================================
# CLI
# ============================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Analyze industrial robot video "
            "using Gemini Robotics ER 2."
        )
    )

    parser.add_argument(
        "--video",
        required=True,
        help="Path to input video."
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help=(
            "Force a fresh Gemini call. "
            "Successful result will still "
            "be saved to cache."
        )
    )

    parser.add_argument(
        "--cache-only",
        action="store_true",
        help=(
            "Only use an existing cache. "
            "Never call Gemini."
        )
    )

    args = parser.parse_args()

    if (
        args.no_cache
        and args.cache_only
    ):

        parser.error(
            "--no-cache and --cache-only "
            "cannot be used together."
        )

    result = analyze_video(
        video_path=args.video,

        use_cache=(
            not args.no_cache
        ),

        cache_only=(
            args.cache_only
        )
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()