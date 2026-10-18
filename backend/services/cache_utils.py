import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional


BASE_DIR = Path(__file__).resolve().parents[2]

CACHE_DIR = BASE_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def build_cache_key(
    service_name: str,
    input_data: Any
) -> str:
    """
    Create a deterministic cache key from
    service name + normalized input data.
    """

    serialized = json.dumps(
        input_data,
        sort_keys=True,
        separators=(",", ":"),
        default=str
    )

    digest = hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()[:16]

    return f"{service_name}_{digest}.json"


def get_cache_path(
    service_name: str,
    input_data: Any
) -> Path:
    """
    Return the cache file path for a service/input pair.
    """

    filename = build_cache_key(
        service_name,
        input_data
    )

    return CACHE_DIR / filename


def load_cache(
    service_name: str,
    input_data: Any
) -> Optional[dict]:
    """
    Load cached result if available.

    Returns:
        dict with cache_status=CACHE_HIT
        or None if cache does not exist / is invalid.
    """

    cache_path = get_cache_path(
        service_name,
        input_data
    )

    if not cache_path.exists():
        return None

    try:
        with open(
            cache_path,
            "r",
            encoding="utf-8"
        ) as file:
            result = json.load(file)

        if not isinstance(result, dict):
            return None

        result["cache_status"] = "CACHE_HIT"

        return result

    except (
        json.JSONDecodeError,
        OSError
    ):
        return None


def save_cache(
    service_name: str,
    input_data: Any,
    result: dict
) -> Path:
    """
    Save a successful AI result to cache.

    Uses atomic replace to reduce the chance of
    leaving corrupted cache files.
    """

    cache_path = get_cache_path(
        service_name,
        input_data
    )

    temp_path = cache_path.with_suffix(
        ".tmp"
    )

    clean_result = dict(result)

    # Do not persist runtime cache metadata.
    clean_result.pop(
        "cache_status",
        None
    )

    clean_result.pop(
        "fallback_reason",
        None
    )

    try:
        with open(
            temp_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                clean_result,
                file,
                indent=2,
                default=str
            )

        os.replace(
            temp_path,
            cache_path
        )

    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

    return cache_path


def cache_fallback(
    service_name: str,
    input_data: Any,
    error: Exception
) -> Optional[dict]:
    """
    Return cached output when the live Gemini call fails.
    """

    cached = load_cache(
        service_name,
        input_data
    )

    if cached:
        cached[
            "cache_status"
        ] = "CACHE_FALLBACK"

        cached[
            "fallback_reason"
        ] = str(error)

    return cached


def delete_cache(
    service_name: str,
    input_data: Any
) -> bool:
    """
    Delete one specific cache entry.

    Useful when forcing a fresh Gemini result.
    """

    cache_path = get_cache_path(
        service_name,
        input_data
    )

    if not cache_path.exists():
        return False

    cache_path.unlink()

    return True