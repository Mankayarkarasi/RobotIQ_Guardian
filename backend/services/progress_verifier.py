import json
import os
from typing import Dict

from google import genai


MODEL_NAME = "gemini-robotics-er-2-preview"


_UPLOAD_CACHE = {}


def get_or_upload_file(client, video_path: str):
    import time
    if video_path in _UPLOAD_CACHE:
        return _UPLOAD_CACHE[video_path]
    uploaded_file = client.files.upload(file=video_path)
    while getattr(uploaded_file, "state", None) and "PROCESSING" in str(uploaded_file.state):
        time.sleep(1)
        uploaded_file = client.files.get(name=uploaded_file.name)
    _UPLOAD_CACHE[video_path] = uploaded_file
    return uploaded_file



def verify_progress(
    video_path: str,
    checkpoint_name: str,
    expected_state: str
) -> Dict:
    """
    Verify whether a recovery checkpoint has been physically achieved
    using Gemini Robotics ER 2.

    Example checkpoints:
    - SAFE_POSITION
    - VALIDATION_READY
    """

    if not os.path.exists(video_path):
        return {
            "status": "CHECKPOINT_ERROR",
            "checkpoint": checkpoint_name,
            "reason": f"Video not found: {video_path}"
        }

    client = genai.Client()
    uploaded_file = get_or_upload_file(client, video_path)


    prompt = f"""
You are verifying progress during a manufacturing robot recovery workflow.

Checkpoint:
{checkpoint_name}

Expected physical state:
{expected_state}

Analyze only what is physically observable in the supplied video.

Your task is to determine whether the expected recovery state
has been achieved.

Rules:
- Do not diagnose hidden mechanical failures.
- Do not assume the recovery step succeeded.
- Do not use telemetry.
- Do not invent measurements.
- If the visual evidence is insufficient, return UNCERTAIN.
- Base the decision only on visible robot/workcell state.

Return ONLY valid JSON in this structure:

{{
  "checkpoint": "{checkpoint_name}",
  "status": "VERIFIED | NOT_VERIFIED | UNCERTAIN",
  "confidence": 0.0,
  "observation": "Short description of visible evidence",
  "expected_state": "{expected_state}"
}}
"""

    import time
    response = None
    for attempt in range(3):
        try:
            response = client.interactions.create(
                model=MODEL_NAME,
                input=[
                    {
                        "type": "video",
                        "uri": uploaded_file.uri,
                        "mime_type": uploaded_file.mime_type
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
                generation_config={
                    "thinking_level": "high"
                }
            )
            break
        except Exception as e:
            if "503" in str(e) or "high demand" in str(e):
                if attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    continue
                return {
                    "status": "CHECKPOINT_SERVICE_BUSY",
                    "checkpoint": checkpoint_name,
                    "reason": f"Model busy (503): {str(e)}",
                    "confidence": 0.5,
                    "observation": "Robotics ER model temporarily busy; checkpoint marked for human review"
                }
            raise e


    raw_output = response.output_text.strip()

    # Remove markdown fences if Gemini returns them
    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`")

        if raw_output.startswith("json"):
            raw_output = raw_output[4:].strip()

    try:
        result = json.loads(raw_output)

    except json.JSONDecodeError:
        return {
            "status": "CHECKPOINT_PARSE_FAILED",
            "checkpoint": checkpoint_name,
            "raw_model_output": response.output_text
        }

    confidence = result.get("confidence")

    if not isinstance(confidence, (int, float)):
        return {
            "status": "CHECKPOINT_INVALID",
            "checkpoint": checkpoint_name,
            "reason": "Confidence value missing or invalid",
            "raw_result": result
        }

    if confidence < 0 or confidence > 1:
        return {
            "status": "CHECKPOINT_INVALID",
            "checkpoint": checkpoint_name,
            "reason": "Confidence must be between 0 and 1",
            "raw_result": result
        }

    result["generated_by"] = MODEL_NAME

    return result


if __name__ == "__main__":

    # Minimal PoC test.
    # Reuse the normal video as the simulated post-recovery visual state.

    video_path = "data/videos/normal.mp4"

    checkpoint_1 = verify_progress(
        video_path=video_path,
        checkpoint_name="SAFE_POSITION",
        expected_state=(
            "The robot is in a stable and safe position "
            "with no abnormal movement."
        )
    )

    checkpoint_2 = verify_progress(
        video_path=video_path,
        checkpoint_name="VALIDATION_READY",
        expected_state=(
            "The robot motion appears stable and the cell "
            "is ready for a validation cycle."
        )
    )

    print("--- Recovery Progress Verification ---")

    print("\nCheckpoint 1:")
    print(json.dumps(
        checkpoint_1,
        indent=2
    ))

    print("\nCheckpoint 2:")
    print(json.dumps(
        checkpoint_2,
        indent=2
    ))