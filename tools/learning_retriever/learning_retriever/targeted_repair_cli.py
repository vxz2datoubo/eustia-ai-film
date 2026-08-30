from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .targeted_repair import TargetedRepairPlanError, plan_targeted_repair


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan bounded Targeted Repair routing")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--eval-result", required=True, help="Expected-vs-Observed result YAML/JSON")
    args = parser.parse_args()

    path = Path(args.eval_result)
    text = path.read_text(encoding="utf-8")
    raw = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    try:
        result = plan_targeted_repair(raw, project_root=args.project_root)
    except TargetedRepairPlanError as exc:
        print(json.dumps({"status": "STRUCTURAL_REJECT", "code": exc.code, "message": exc.message}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())