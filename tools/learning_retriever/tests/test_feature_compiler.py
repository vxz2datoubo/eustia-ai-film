from pathlib import Path

import pytest
import yaml

from learning_retriever import LearningRetriever
from learning_retriever.feature_compiler import (
    FeatureCompilationError,
    compile_director_features,
    compile_retrieval_task,
    validate_semantic_dependencies,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
REGRESSION_PATH = REPO_ROOT / "11_验收/director_feature_compiler_regression_cases.yaml"
REGRESSIONS = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))


def _assert_declared_compatibility(case):
    compiled = [compile_director_features(description) for description in case["descriptions"]]
    expected = case["expected"]

    if "compatible_failure_mechanism" in expected:
        value = expected["compatible_failure_mechanism"]
        assert all(value in item.failure_mechanism for item in compiled)

    if "compatible_relation_type" in expected:
        value = expected["compatible_relation_type"]
        assert all(value in item.relation_type for item in compiled)

    for value in expected.get("compatible_spatial_action_features", []):
        assert all(value in item.spatial_action_features for item in compiled)


@pytest.mark.parametrize("case", REGRESSIONS["cases"], ids=lambda case: case["id"])
def test_declared_cross_surface_regressions_are_executable(case):
    _assert_declared_compatibility(case)


@pytest.mark.parametrize("case", REGRESSIONS["retrieval_cases"], ids=lambda case: case["id"])
def test_cross_surface_same_mechanism_recalls_same_canonical_case(case):
    retriever = LearningRetriever(REPO_ROOT)
    expected = case["expected_case_id"]

    for index, description in enumerate(case["descriptions"]):
        task = compile_retrieval_task(description, task_id=f"{case['id']}-{index}")
        result = retriever.retrieve(task, top_k=5)
        selected = result["retrieval_receipt"]["selected_case_ids"]
        assert expected in selected
        assert selected[0] == expected
        assert result["status"] == "PASS"


@pytest.mark.parametrize("case", REGRESSIONS["negative_semantic_cases"], ids=lambda case: case["id"])
def test_negative_semantic_regressions(case):
    result = compile_director_features(case["description"])
    for field, values in case.get("expected_present", {}).items():
        observed = getattr(result, field)
        for value in values:
            assert value in observed
    for field, values in case.get("expected_absent", {}).items():
        observed = getattr(result, field)
        for value in values:
            assert value not in observed


@pytest.mark.parametrize("case", REGRESSIONS["fail_closed_cases"], ids=lambda case: case["id"])
def test_unrecognized_description_fails_closed(case):
    with pytest.raises(FeatureCompilationError, match=case["expected_error"]):
        compile_director_features(case["description"])


def test_semantic_dependencies_bind_existing_soac_eventgraph_blocking_visibleir():
    assert validate_semantic_dependencies(REPO_ROOT) == []


def test_structured_features_are_preserved_when_natural_language_is_compiled():
    task = compile_retrieval_task(
        "角色面向门口目标",
        task_id="REG-MERGE",
        base_task={"dramatic_function": ["explicit_user_feature"]},
    )
    assert "explicit_user_feature" in task["dramatic_function"]
    assert "target_oriented_action" in task["dramatic_function"]


def test_compiler_is_query_only_and_does_not_duplicate_learning_authority():
    task = compile_retrieval_task("普通对白场景", task_id="REG-AUTHORITY")
    assert set(task["feature_compiler_receipt"]) == {
        "component",
        "status",
        "input_fingerprint",
        "compiled_feature_keys",
        "matched_rules",
        "semantic_trace",
        "authority_boundary",
    }
    assert task["feature_compiler_receipt"]["authority_boundary"] == "retrieval_query_only"
    assert "learning_rules" not in task
    assert "authority_ref" not in task
    assert "maturity" not in task
    assert "scope" not in task
