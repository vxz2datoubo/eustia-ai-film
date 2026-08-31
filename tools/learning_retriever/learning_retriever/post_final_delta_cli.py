from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .post_final_delta import PostFinalDeltaValidationError, assess_post_final_delta_validation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assess Final-Delta evidence cohorts, regression proposals and maturity routing"
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--assessment", required=True, help="Assessment YAML/JSON")
    args = parser.parse_args()

    path = Path(args.assessment)
    text = path.read_text(encoding="utf-8")
    raw = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    try:
        result = assess_post_final_delta_validation(raw, project_root=args.project_root)
    except PostFinalDeltaValidationError as exc:
        print(
            json.dumps(
                {"status": "STRUCTURAL_REJECT", "code": exc.code, "message": exc.message},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
