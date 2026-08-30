from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .learning_pipeline import LearningEvidencePipelineError, run_learning_evidence_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the evidence-driven continual-learning pipeline over supplied before/after observations"
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--pipeline", required=True, help="Pipeline package YAML/JSON")
    args = parser.parse_args()

    path = Path(args.pipeline)
    text = path.read_text(encoding="utf-8")
    raw = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    try:
        result = run_learning_evidence_pipeline(raw, project_root=args.project_root)
    except LearningEvidencePipelineError as exc:
        print(json.dumps(exc.as_dict(), ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
