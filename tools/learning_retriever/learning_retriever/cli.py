from __future__ import annotations

import argparse
import json
from pathlib import Path

from .retriever import LearningRetriever, RetrievalGateError, validate_index


def main() -> int:
    parser = argparse.ArgumentParser(description="EUSTIA Learning Smart Recall V1")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--task", help="JSON task feature file")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--expand", action="store_true", help="expand only selected Top-K canonical cases")
    parser.add_argument("--validate-index", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root)
    if args.validate_index:
        errors = validate_index(root)
        print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else 2
    if not args.task:
        parser.error("--task is required unless --validate-index is used")
    task = json.loads(Path(args.task).read_text(encoding="utf-8"))
    retriever = LearningRetriever(root)
    try:
        result = retriever.retrieve(task, top_k=args.top_k, expand=args.expand, fail_closed=True)
    except RetrievalGateError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
