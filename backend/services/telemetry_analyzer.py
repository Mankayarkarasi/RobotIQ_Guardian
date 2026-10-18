"""
RoboIQ-Guardian Telemetry Analyzer Service
Analyzes robotic telemetry data against configured safety thresholds.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class AnalysisResult:
    """Encapsulates the result of telemetry threshold analysis."""

    def __init__(self, status: str, breached_signals: List[Dict[str, Any]]):
        self.status = status
        self.breached_signals = breached_signals
        self.breaches = breached_signals

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.status == other
        if isinstance(other, tuple):
            return (self.status, self.breached_signals) == other
        if isinstance(other, dict):
            return self.to_dict() == other
        return super().__eq__(other)

    def __iter__(self):
        return iter((self.status, self.breached_signals))

    def __getitem__(self, item: Union[str, int]) -> Any:
        if item == "status":
            return self.status
        if item in ("breached_signals", "breaches"):
            return self.breached_signals
        if isinstance(item, int):
            return (self.status, self.breached_signals)[item]
        raise KeyError(item)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "status":
            return self.status
        if key in ("breached_signals", "breaches"):
            return self.breached_signals
        return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "breached_signals": self.breached_signals,
        }

    def __repr__(self) -> str:
        return f"AnalysisResult(status='{self.status}', breached_signals={self.breached_signals})"

    def __str__(self) -> str:
        if self.status == "NORMAL":
            return "NORMAL"
        breach_desc = ", ".join(
            f"{b['signal']} (actual: {b['actual']}, threshold: {b['threshold']})"
            for b in self.breached_signals
        )
        return f"FAILURE: {breach_desc}"


def resolve_path(rel_path: Union[str, Path]) -> Path:
    """Resolves relative file paths across different execution directories."""
    path = Path(rel_path)
    if path.is_file():
        return path

    cwd_path = Path.cwd() / path
    if cwd_path.is_file():
        return cwd_path

    cwd_robo = Path.cwd() / "RoboIQ-Guardian" / path
    if cwd_robo.is_file():
        return cwd_robo

    script_dir = Path(__file__).resolve().parent
    for parent in [script_dir, script_dir.parent, script_dir.parent.parent]:
        candidate = parent / path
        if candidate.is_file():
            return candidate

    return path


def load_json(source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """Loads a JSON file or returns the dictionary if already parsed."""
    if isinstance(source, dict):
        return source
    resolved = resolve_path(source)
    with open(resolved, "r", encoding="utf-8") as f:
        return json.load(f)


# Mapping of the 5 monitored signal fields to their threshold keys
SIGNAL_THRESHOLD_KEYS = {
    "cycle_time": "cycle_time_max",
    "position_error": "position_error_max",
    "joint_3_vibration": "joint_3_vibration_max",
    "motor_current": "motor_current_max",
    "temperature": "temperature_max",
}


def analyze_telemetry(
    telemetry: Union[str, Path, Dict[str, Any]],
    thresholds: Optional[Union[str, Path, Dict[str, Any]]] = None,
) -> AnalysisResult:
    """
    Compares telemetry data against thresholds.

    Returns:
        AnalysisResult:
            - status: "NORMAL" if no thresholds exceeded, "FAILURE" otherwise
            - breached_signals: list of dicts with signal name, actual value, and threshold
    """
    telemetry_data = load_json(telemetry)
    if thresholds is None:
        thresholds_data = load_json("data/config/thresholds.json")
    else:
        thresholds_data = load_json(thresholds)

    breached_signals: List[Dict[str, Any]] = []

    for signal, threshold_key in SIGNAL_THRESHOLD_KEYS.items():
        if signal not in telemetry_data:
            continue

        actual_val = telemetry_data[signal]
        threshold_val = thresholds_data.get(threshold_key, thresholds_data.get(signal))

        if threshold_val is not None and actual_val > threshold_val:
            breached_signals.append({
                "signal": signal,
                "name": signal,
                "signal_name": signal,
                "actual": actual_val,
                "actual_value": actual_val,
                "threshold": threshold_val,
            })

    status = "FAILURE" if breached_signals else "NORMAL"
    return AnalysisResult(status=status, breached_signals=breached_signals)


if __name__ == "__main__":
    thresholds_path = "data/config/thresholds.json"
    normal_path = "data/telemetry/normal.json"
    failure_path = "data/telemetry/failure.json"

    print("--- Scenario 1: Normal Telemetry ---")
    normal_res = analyze_telemetry(normal_path, thresholds_path)
    print(f"Status: {normal_res.status}")
    if normal_res.breached_signals:
        print("Breached signals:")
        for breach in normal_res.breached_signals:
            print(f"  - {breach['signal']}: actual {breach['actual']} > threshold {breach['threshold']}")
    else:
        print("All signals within safety limits.")

    print("\n--- Scenario 2: Failure Telemetry ---")
    failure_res = analyze_telemetry(failure_path, thresholds_path)
    print(f"Status: {failure_res.status}")
    if failure_res.breached_signals:
        print("Breached signals:")
        for breach in failure_res.breached_signals:
            print(f"  - {breach['signal']}: actual {breach['actual']} (threshold: {breach['threshold']})")
    else:
        print("All signals within safety limits.")
