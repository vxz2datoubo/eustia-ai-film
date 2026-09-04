from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .post_final_delta import PostFinalDeltaValidationError
from .post_final_delta_source_bound import assess_source_bound_post_final_delta


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Assess Post-Final-Delta evidence only from source packages that are "
            "re-executed through the governed Final-Delta runtime"
        )
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--assessment",
        required=True,
        help="Source-bound assessment YAML/JSON containing final_delta_inputs, never serialized final_deltas",
    )
    args = parser.parse_args()

    path = Path(args.assessment)
    text = path.read_text(encoding="utf-8")
    raw = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    try:
        result = assess_source_bound_post_final_delta(raw, project_root=args.project_root)
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
