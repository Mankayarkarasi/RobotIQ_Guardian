import json
from pathlib import Path
from typing import Dict, List


BASE_DIR = Path(__file__).resolve().parents[2]

HYPOTHESES_FILE = (
    BASE_DIR
    / "data"
    / "config"
    / "hypotheses.json"
)


def get_hypotheses() -> List[Dict]:
    with open(
        HYPOTHESES_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


if __name__ == "__main__":
    hypotheses = get_hypotheses()

    print("--- RoboIQ Guardian Hypotheses ---")

    for hypothesis in hypotheses:
        print(
            f"\n{hypothesis['id']} - "
            f"{hypothesis['name']}"
        )

        print("Supported by:")

        for item in hypothesis.get(
            "supported_by",
            []
        ):
            print(f"  - {item}")