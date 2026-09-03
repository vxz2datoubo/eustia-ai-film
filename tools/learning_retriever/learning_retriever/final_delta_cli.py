from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .final_delta import FinalDeltaEvidenceError, compile_final_delta_learning_evidence


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile Repair Outcome / Final-Delta candidate learning evidence"
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--package", required=True, help="Final-Delta input YAML/JSON")
    args = parser.parse_args()

    path = Path(args.package)
    text = path.read_text(encoding="utf-8")
    raw = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    try:
        result = compile_final_delta_learning_evidence(raw, project_root=args.project_root)
    except FinalDeltaEvidenceError as exc:
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
