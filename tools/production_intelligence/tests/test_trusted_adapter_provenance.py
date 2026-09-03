from pathlib import Path

import pytest
import yaml

import production_intelligence.trusted_adapter as adapter
from production_intelligence.contracts import ProductionIntelligenceError

ROOT = Path(__file__).resolve().parents[3]
SUITE = yaml.safe_load(
    (ROOT / "11_验收/expected_observed_eval_regression_cases.yaml").read_text(encoding="utf-8")
)


def payload():
    return next(
        item["payload"] for item in SUITE["cases"] if item["id"] == "EOE-EXPLICIT-FAIL-001"
    )


def _fake_plan(*args, **kwargs):
    return {
        "source_eval_id": "ATTACK",
        "source_eval_status": "FAIL",
        "source_binding": {
            "mode": "canonical_expected_observed_reexecution",
            "serialized_eval_result_accepted": False,
        },
        "routing_policy_id": "EUSTIA_TARGETED_REPAIR_V1",
        "repair_items": [
            {
                "field": "capture_intent",
                "outcome": "FAIL",
                "failure_category": "camera",
                "repair_surface": "UPSTREAM_CAMERA_CONTRACT_REVIEW",
                "evidence_refs": ["attacker"],
            }
        ],
        "prompt_mutation_authorized": False,
        "generation_authorized": False,
        "camera_authority_mutation_authorized": False,
        "canonical_mutation_authorized": False,
        "learning_writeback_authorized": False,
        "maturity_promotion_authorized": False,
        "causal_claim_authorized": False,
    }


def test_unmodified_governed_runtime_still_mints_trusted_receipt():
    receipt = adapter.compile_expected_observed_coordination(payload(), project_root=ROOT)
    assert adapter.require_trusted_eval_receipt(receipt) is receipt


def test_public_planner_binding_substitution_fails_before_receipt_mint(monkeypatch):
    monkeypatch.setattr(adapter, "plan_targeted_repair", _fake_plan)
    with pytest.raises(ProductionIntelligenceError) as exc:
        adapter.compile_expected_observed_coordination(payload(), project_root=ROOT)
    assert exc.value.code == "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_SUBSTITUTED"
    assert exc.value.details["reason"] == "public_planner_binding_substituted"


def test_core_planner_binding_substitution_fails_before_receipt_mint(monkeypatch):
    monkeypatch.setattr(adapter._core, "plan_targeted_repair", _fake_plan)
    with pytest.raises(ProductionIntelligenceError) as exc:
        adapter.compile_expected_observed_coordination(payload(), project_root=ROOT)
    assert exc.value.code == "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_SUBSTITUTED"
    assert exc.value.details["reason"] == "core_planner_binding_substituted"


def test_targeted_repair_module_export_substitution_fails_closed(monkeypatch):
    monkeypatch.setattr(adapter._targeted_repair_module, "plan_targeted_repair", _fake_plan)
    with pytest.raises(ProductionIntelligenceError) as exc:
        adapter.compile_expected_observed_coordination(payload(), project_root=ROOT)
    assert exc.value.code == "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_SUBSTITUTED"
    assert exc.value.details["reason"] == "planner_binding_substituted"


def test_transitive_expected_observed_binding_substitution_fails_closed(monkeypatch):
    def fake_eval(*args, **kwargs):
        return {}

    monkeypatch.setattr(adapter._targeted_repair_module, "evaluate_expected_vs_observed", fake_eval)
    with pytest.raises(ProductionIntelligenceError) as exc:
        adapter.compile_expected_observed_coordination(payload(), project_root=ROOT)
    assert exc.value.code == "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_SUBSTITUTED"
    assert exc.value.details["reason"] == "planner_evaluator_binding_substituted"


def test_expected_observed_module_export_substitution_fails_closed(monkeypatch):
    def fake_eval(*args, **kwargs):
        return {}

    monkeypatch.setattr(adapter._expected_observed_module, "evaluate_expected_vs_observed", fake_eval)
    with pytest.raises(ProductionIntelligenceError) as exc:
        adapter.compile_expected_observed_coordination(payload(), project_root=ROOT)
    assert exc.value.code == "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_SUBSTITUTED"
    assert exc.value.details["reason"] == "evaluator_binding_substituted"


def test_targeted_repair_source_locator_substitution_fails_closed(monkeypatch):
    monkeypatch.setattr(
        adapter._targeted_repair_module,
        "__file__",
        str(ROOT / "tools/learning_retriever/learning_retriever/attacker_targeted_repair.py"),
    )
    with pytest.raises(ProductionIntelligenceError) as exc:
        adapter.compile_expected_observed_coordination(payload(), project_root=ROOT)
    assert exc.value.code in {
        "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_INVALID",
        "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_SUBSTITUTED",
    }


def test_consumer_revalidates_runtime_provenance_after_receipt_mint(monkeypatch):
    receipt = adapter.compile_expected_observed_coordination(payload(), project_root=ROOT)
    monkeypatch.setattr(adapter._core, "plan_targeted_repair", _fake_plan)
    with pytest.raises(ProductionIntelligenceError) as exc:
        adapter.resolve_receipt_consumers(
            receipt,
            project_root=ROOT,
            capability_ids={"CAP-CAMERA-FRAMING", "CAP-REVERSE-EVAL"},
        )
    assert exc.value.code == "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_SUBSTITUTED"
