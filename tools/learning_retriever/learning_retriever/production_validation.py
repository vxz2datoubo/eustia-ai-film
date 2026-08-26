from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .feature_compiler import FeatureCompilationError
from .retriever import RetrievalGateError
from .runtime import DirectorLearningRuntime


DEFAULT_MATRIX_PATH = Path("11_验收/learning_smart_recall_production_validation_matrix.yaml")
FEATURE_KEYS = (
    "dramatic_function",
    "relation_type",
    "spatial_action_features",
    "failure_mechanism",
)


def _as_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(item) for item in value}
    return {str(value)}


def _check_expected_result(case: dict[str, Any], result: dict[str, Any]) -> list[str]:
    expected = case.get("expected") or {}
    errors: list[str] = []
    runtime_receipt = result.get("canonical_runtime_receipt") or {}
    retrieval_receipt = result.get("retrieval_receipt") or {}
    compiled = runtime_receipt.get("compiled_features") or {}

    for field, values in (expected.get("feature_present") or {}).items():
        observed = _as_set(compiled.get(field))
        for value in values or []:
            if str(value) not in observed:
                errors.append(f"missing compiled feature {field}:{value}")

    for field, values in (expected.get("feature_absent") or {}).items():
        observed = _as_set(compiled.get(field))
        for value in values or []:
            if str(value) in observed:
                errors.append(f"forbidden compiled feature {field}:{value}")

    hard_routes = _as_set(retrieval_receipt.get("hard_routes"))
    for route in expected.get("hard_routes_present") or []:
        if str(route) not in hard_routes:
            errors.append(f"missing hard route {route}")
    for route in expected.get("hard_routes_absent") or []:
        if str(route) in hard_routes:
            errors.append(f"forbidden hard route {route}")

    mandatory = _as_set(retrieval_receipt.get("mandatory_case_ids"))
    selected = _as_set(retrieval_receipt.get("selected_case_ids"))
    for case_id in expected.get("mandatory_cases_present") or []:
        if str(case_id) not in mandatory:
            errors.append(f"missing mandatory case {case_id}")
    for case_id in expected.get("selected_cases_present") or []:
        if str(case_id) not in selected:
            errors.append(f"missing selected case {case_id}")
    for case_id in expected.get("selected_cases_absent") or []:
        if str(case_id) in selected:
            errors.append(f"forbidden selected case {case_id}")

    excluded = {
        str(item.get("case_id")): str(item.get("reason"))
        for item in (retrieval_receipt.get("excluded_candidates") or [])
        if isinstance(item, dict)
    }
    for case_id, reason in (expected.get("excluded_reasons") or {}).items():
        observed = excluded.get(str(case_id))
        if observed != str(reason):
            errors.append(f"excluded reason {case_id}: expected {reason}, observed {observed}")

    if "mandatory_recall_satisfied" in expected:
        observed = bool(retrieval_receipt.get("mandatory_recall_satisfied"))
        if observed != bool(expected["mandatory_recall_satisfied"]):
            errors.append(
                "mandatory_recall_satisfied mismatch: "
                f"expected {expected['mandatory_recall_satisfied']}, observed {observed}"
            )

    if "receipt_complete" in expected:
        observed = bool(retrieval_receipt.get("receipt_complete"))
        if observed != bool(expected["receipt_complete"]):
            errors.append(f"receipt_complete mismatch: expected {expected['receipt_complete']}, observed {observed}")

    expected_flow = ["director_feature_compiler", "hard_route", "semantic_recall"]
    if runtime_receipt.get("flow") != expected_flow:
        errors.append(f"canonical runtime flow changed: {runtime_receipt.get('flow')}")
    if runtime_receipt.get("route_authority") != "10_运行时/director_route_index.yaml":
        errors.append(f"route authority changed: {runtime_receipt.get('route_authority')}")
    compiler_receipt = runtime_receipt.get("feature_compiler_receipt") or {}
    if compiler_receipt.get("authority_boundary") != "retrieval_query_only":
        errors.append(f"compiler authority boundary changed: {compiler_receipt.get('authority_boundary')}")

    return errors


def run_production_validation_matrix(
    project_root: str | Path,
    *,
    matrix_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run the production matrix through the canonical director learning runtime.

    This is an eval harness only. It does not own retrieval, route definitions,
    learning payloads, maturity or scope. Every executable positive case enters
    ``DirectorLearningRuntime.retrieve`` and therefore traverses the canonical
    Feature Compiler -> Hard Route -> Semantic Recall path.
    """
    root = Path(project_root)
    path = Path(matrix_path) if matrix_path else root / DEFAULT_MATRIX_PATH
    if not path.is_absolute():
        path = root / path
    matrix = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = matrix.get("cases") or []
    runtime = DirectorLearningRuntime(root)

    reports: list[dict[str, Any]] = []
    false_positive_routes: list[dict[str, str]] = []
    false_negative_mandatory: list[dict[str, str]] = []
    authority_violations: list[dict[str, str]] = []

    for case in cases:
        case_id = str(case.get("id") or "UNSPECIFIED_MATRIX_CASE")
        description = str(case.get("description") or "")
        expected_error = case.get("expected_error") or {}
        try:
            result = runtime.retrieve(
                description,
                task_id=case_id,
                base_task=case.get("base_task"),
                top_k=int(case.get("top_k") or 8),
                expand=False,
            )
        except FeatureCompilationError as exc:
            code = str(exc)
            expected_stage = str(expected_error.get("stage") or "")
            expected_code = str(expected_error.get("code") or "")
            passed = expected_stage == "feature_compiler" and code == expected_code
            reports.append(
                {
                    "case_id": case_id,
                    "family": case.get("family"),
                    "kind": case.get("kind"),
                    "production_context": case.get("production_context"),
                    "input": description,
                    "compiled_features": {},
                    "hard_routes": [],
                    "mandatory_cases": [],
                    "selected_cases": [],
                    "excluded_cases": [],
                    "filters": [],
                    "mandatory_recall_satisfied": None,
                    "receipt_complete": None,
                    "error": {"stage": "feature_compiler", "code": code},
                    "verdict": "PASS" if passed else "FAIL",
                    "failures": [] if passed else [f"unexpected feature compiler error {code}"],
                }
            )
            continue
        except RetrievalGateError as exc:
            code = str(exc)
            expected_stage = str(expected_error.get("stage") or "")
            expected_code = str(expected_error.get("code") or "")
            passed = expected_stage == "retriever" and code == expected_code
            reports.append(
                {
                    "case_id": case_id,
                    "family": case.get("family"),
                    "kind": case.get("kind"),
                    "production_context": case.get("production_context"),
                    "input": description,
                    "compiled_features": {},
                    "hard_routes": [],
                    "mandatory_cases": [],
                    "selected_cases": [],
                    "excluded_cases": [],
                    "filters": [],
                    "mandatory_recall_satisfied": False,
                    "receipt_complete": False,
                    "error": {"stage": "retriever", "code": code},
                    "verdict": "PASS" if passed else "FAIL",
                    "failures": [] if passed else [f"unexpected retrieval gate error {code}"],
                }
            )
            continue

        if expected_error:
            failures = [f"expected {expected_error.get('stage')} error {expected_error.get('code')} but runtime passed"]
        else:
            failures = _check_expected_result(case, result)

        receipt = result.get("retrieval_receipt") or {}
        runtime_receipt = result.get("canonical_runtime_receipt") or {}
        expected = case.get("expected") or {}
        actual_routes = _as_set(receipt.get("hard_routes"))
        actual_mandatory = _as_set(receipt.get("mandatory_case_ids"))
        actual_selected = _as_set(receipt.get("selected_case_ids"))

        for route in expected.get("hard_routes_absent") or []:
            if str(route) in actual_routes:
                false_positive_routes.append({"case_id": case_id, "route": str(route)})
        for case_ref in expected.get("mandatory_cases_present") or []:
            if str(case_ref) not in actual_mandatory or str(case_ref) not in actual_selected:
                false_negative_mandatory.append({"case_id": case_id, "case": str(case_ref)})

        for failure in failures:
            if "authority" in failure or "runtime flow" in failure:
                authority_violations.append({"case_id": case_id, "detail": failure})

        reports.append(
            {
                "case_id": case_id,
                "family": case.get("family"),
                "kind": case.get("kind"),
                "production_context": case.get("production_context"),
                "input": description,
                "compiled_features": runtime_receipt.get("compiled_features") or {},
                "hard_routes": list(receipt.get("hard_routes") or []),
                "mandatory_cases": list(receipt.get("mandatory_case_ids") or []),
                "selected_cases": list(receipt.get("selected_case_ids") or []),
                "excluded_cases": list(receipt.get("excluded_candidates") or []),
                "filters": list(receipt.get("filters_applied") or []),
                "mandatory_recall_satisfied": receipt.get("mandatory_recall_satisfied"),
                "receipt_complete": receipt.get("receipt_complete"),
                "verdict": "PASS" if not failures else "FAIL",
                "failures": failures,
            }
        )

    positive_reports = [item for item in reports if item.get("kind") == "positive"]
    negative_reports = [item for item in reports if item.get("kind") in {"negative", "fail_closed"}]
    failed = [item["case_id"] for item in reports if item["verdict"] != "PASS"]
    observed_families = {str(item.get("family")) for item in reports}
    required_families = {str(item) for item in matrix.get("required_families") or []}
    missing_families = sorted(required_families - observed_families)

    aggregate = {
        "total_cases": len(reports),
        "positive_passes": sum(item["verdict"] == "PASS" for item in positive_reports),
        "positive_total": len(positive_reports),
        "negative_fail_closed_passes": sum(item["verdict"] == "PASS" for item in negative_reports),
        "negative_fail_closed_total": len(negative_reports),
        "false_positive_routes": false_positive_routes,
        "false_negative_mandatory_recalls": false_negative_mandatory,
        "authority_boundary_violations": authority_violations,
        "missing_required_families": missing_families,
        "failed_case_ids": failed,
        "verdict": "PASS"
        if not failed and not false_positive_routes and not false_negative_mandatory and not authority_violations and not missing_families
        else "FAIL",
    }
    return {
        "schema": "LEARNING_SMART_RECALL_PRODUCTION_VALIDATION_REPORT/v1",
        "matrix": str(path.relative_to(root) if path.is_relative_to(root) else path),
        "cases": reports,
        "aggregate": aggregate,
    }
