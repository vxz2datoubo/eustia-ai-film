from __future__ import annotations

import argparse
import json
from pathlib import Path

from .active_work_item import ActiveWorkItemResolutionError
from .feature_compiler import FeatureCompilationError, validate_semantic_dependencies
from .retriever import LearningRetriever, RetrievalGateError, validate_index
from .runtime import DirectorLearningRuntime


def main() -> int:
    parser = argparse.ArgumentParser(description="EUSTIA Learning Smart Recall V1.1")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--task", help="JSON structured task feature file")
    parser.add_argument("--description", help="natural-language director task description")
    parser.add_argument("--task-id", default="UNSPECIFIED_TASK")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--expand", action="store_true", help="expand only selected Top-K canonical cases")
    parser.add_argument("--validate-index", action="store_true")
    parser.add_argument("--validate-feature-compiler", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root)
    if args.validate_index:
        errors = validate_index(root)
        print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else 2
    if args.validate_feature_compiler:
        errors = validate_semantic_dependencies(root)
        print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, ensure_ascii=False, indent=2))
        return 0 if not errors else 2

    if args.task and args.description:
        parser.error("use either --task or --description, not both")
    if not args.task and not args.description:
        parser.error("--task or --description is required unless a validation flag is used")

    try:
        if args.description:
            # CLI intentionally has no serialized freshness override. Continuation
            # requests with a source Issue fail closed until a host runtime supplies
            # an in-process freshness provider backed by a real source read.
            result = DirectorLearningRuntime(root).retrieve(
                args.description,
                task_id=args.task_id,
                top_k=args.top_k,
                expand=args.expand,
            )
        else:
            raw_task = json.loads(Path(args.task).read_text(encoding="utf-8"))
            description = raw_task.pop("director_task_description", None)
            if description is not None:
                result = DirectorLearningRuntime(root).retrieve(
                    str(description),
                    task_id=str(raw_task.get("task_id") or args.task_id),
                    base_task=raw_task,
                    top_k=args.top_k,
                    expand=args.expand,
                )
            else:
                result = LearningRetriever(root).retrieve(
                    raw_task,
                    top_k=args.top_k,
                    expand=args.expand,
                    fail_closed=True,
                )
    except ActiveWorkItemResolutionError as exc:
        print(json.dumps({"status": "FAIL", "stage": "active_work_item_resolution", "error": exc.code, "details": exc.details}, ensure_ascii=False, indent=2))
        return 2
    except FeatureCompilationError as exc:
        print(json.dumps({"status": "FAIL", "stage": "feature_compiler", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    except RetrievalGateError as exc:
        print(json.dumps({"status": "FAIL", "stage": "retriever", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
