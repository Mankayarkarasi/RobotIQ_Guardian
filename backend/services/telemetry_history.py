"""Read-only historical synthetic telemetry for RoboIQ Guardian."""
import json
from functools import lru_cache
from pathlib import Path
from fastapi import HTTPException

DATA_DIR = Path(__file__).resolve().parents[2] / 'data' / 'historical'
SIGNALS = ('cycle_time_s', 'joint_3_vibration_mm_s', 'motor_current_a', 'motor_temperature_c', 'position_error_mm', 'defect_rate_pct')

@lru_cache(maxsize=1)
def load_history():
    path = DATA_DIR / 'telemetry.jsonl'
    if not path.is_file():
        raise HTTPException(status_code=503, detail='Historical telemetry dataset not installed')
    with path.open(encoding='utf-8') as stream:
        return tuple(json.loads(line) for line in stream if line.strip())

@lru_cache(maxsize=1)
def load_episodes():
    path = DATA_DIR / 'episodes.jsonl'
    if not path.is_file():
        raise HTTPException(status_code=503, detail='Historical episode metadata not installed')
    with path.open(encoding='utf-8') as stream:
        return tuple(json.loads(line) for line in stream if line.strip())

def episode_catalog():
    episodes = list(load_episodes())
    return {'source': 'historical_synthetic', 'total_records': len(load_history()), 'robots': sorted({e['robot_id'] for e in episodes}), 'episodes': episodes}

def history_for(robot_id, episode_id, limit=240, start=None, end=None):
    candidates = [e for e in load_episodes() if e.get('robot_id') == robot_id and e.get('episode_id') == episode_id]
    if not candidates:
        raise HTTPException(status_code=404, detail='Unknown robot/episode pair')
    rows = [r for r in load_history() if r.get('robot_id') == robot_id and r.get('episode_id') == episode_id and (not start or r['timestamp'] >= start) and (not end or r['timestamp'] <= end)]
    rows.sort(key=lambda r: r['timestamp'])
    count = len(rows)
    if count > limit:
        # Evenly sample while preserving first and last observations.
        indices = [round(i * (count - 1) / (limit - 1)) for i in range(limit)]
        rows = [rows[i] for i in indices]
    return {'source': 'historical_synthetic', 'robot_id': robot_id, 'episode_id': episode_id, 'scenario_type': candidates[0].get('scenario_type'), 'total_matching_records': count, 'returned_records': len(rows), 'signals': SIGNALS, 'records': rows}
