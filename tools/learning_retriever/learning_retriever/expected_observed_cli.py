from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .expected_observed import ExpectedObservedEvalError, evaluate_expected_vs_observed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare declared CinematicIntent expectations with supplied ReverseObservation evidence"
    )
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--eval", required=True, help="JSON or YAML expected-vs-observed evaluation file")
    args = parser.parse_args()

    path = Path(args.eval)
    text = path.read_text(encoding="utf-8")
    raw = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)

    try:
        result = evaluate_expected_vs_observed(raw, project_root=args.project_root)
    except ExpectedObservedEvalError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "stage": "expected_observed_gate",
                    "code": exc.code,
                    "error": exc.message,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "FAIL":
        return 2
    if result["status"] == "INCOMPLETE":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
