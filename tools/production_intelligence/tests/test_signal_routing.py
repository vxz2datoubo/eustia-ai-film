from dataclasses import replace
from pathlib import Path

import pytest
import yaml

import production_intelligence.trusted_adapter as trusted_adapter_module
from production_intelligence.runtime import CapabilityAtlas, ProductionIntelligenceError
from production_intelligence.trusted_adapter import (
    TARGETED_REPAIR_POLICY_PATH,
    TrustedRepairItem,
    compile_expected_observed_coordination,
    load_trusted_adapter_policy,
    require_trusted_eval_receipt,
)

ROOT = Path(__file__).resolve().parents[3]
SUITE = yaml.safe_load(
    (ROOT / "11_验收/expected_observed_eval_regression_cases.yaml").read_text(encoding="utf-8")
)


def atlas():
    return CapabilityAtlas.from_project_root(ROOT)


def case(case_id):
    return next(item for item in SUITE["cases"] if item["id"] == case_id)


def fake_serialized_signal(*, signatures=None, producer="Expected_vs_Observed"):
    return {
        "signal_id": "SIG-FORGED-001",
        "signal_type": "EVAL_DIMENSION_RESULT",
        "source_stage": "EVALUATED",
        "producer": producer,
        "work_item_id_when_required": "FAKE-WORK-ITEM",
        "materiality": "MATERIAL",
        "epistemic_zone": "K3_ADJACENT_EXPERT",
        "authority_refs": ["10_运行时/screen_observable_audible_ir_schema.yaml"],
        "payload": {"problem_signatures": list(signatures or ["camera_framing_fail"])},
        "provenance_chain": [
            {
                "stage": "EVALUATED",
                "producer": producer,
                "signal_or_packet_ref": "SIG-FORGED-001",
                "action": "CREATED",
            }
        ],
    }


def test_serialized_signal_envelope_cannot_claim_route_authority_even_if_fields_look_valid():
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(fake_serialized_signal())
    assert exc.value.code == "TRUSTED_SIGNAL_RECEIPT_REQUIRED"


def test_old_director_feature_style_self_assertion_is_no_longer_a_public_route():
    forged = fake_serialized_signal(
        signatures=["exposition_stall"], producer="Director_Feature_Compiler"
    )
    forged["signal_type"] = "DIRECTOR_FEATURE_RECEIPT"
    forged["source_stage"] = "DIRECTOR_FEATURE_COMPILED"
    forged["provenance_chain"][0]["stage"] = "DIRECTOR_FEATURE_COMPILED"
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(forged)
    assert exc.value.code == "TRUSTED_SIGNAL_RECEIPT_REQUIRED"


def test_canonical_camera_failure_routes_only_to_camera_owner():
    payload = case("EOE-EXPLICIT-FAIL-001")["payload"]
    result = atlas().resolve_expected_observed(payload, project_root=ROOT)
    assert result.materiality == "MATERIAL"
    assert result.signal_type == "EVAL_DIMENSION_RESULT"
    assert result.source_stage == "EVALUATED"
    assert result.problem_signatures == ("camera::capture_intent",)
    assert result.selected_capabilities == ("CAP-CAMERA-FRAMING",)
    assert "CAP-STORY-DIRECTOR-INTENT" not in result.selected_capabilities
    assert "CAP-SOUND" not in result.selected_capabilities
    assert "CAP-LEARNING" not in result.selected_capabilities
    receipt = result.as_dict()
    assert receipt["serialized_signal_envelope_route_authority"] is False
    assert receipt["consumer_policy_enforced"] is True
    assert receipt["authority_boundary"] == "coordination_receipt_only"


def test_missing_observation_routes_to_evidence_acquisition_only_without_learning():
    payload = case("EOE-MISSING-OBSERVATION-UNKNOWN-001")["payload"]
    result = atlas().resolve_expected_observed(payload, project_root=ROOT)
    assert result.materiality == "DIAGNOSTIC"
    assert result.problem_signatures == ("UNKNOWN::color_intent",)
    assert result.selected_capabilities == ("CAP-REVERSE-EVAL",)
    assert "CAP-LEARNING" not in result.selected_capabilities
    policy = load_trusted_adapter_policy(ROOT)
    unknown = policy["unknown_outcome_consumer"]
    assert unknown["same_evaluated_signal_may_not_reenter_reverse_observation"] is True
    assert unknown["new_evidence_or_new_generation_required_before_expected_observed_reentry"] is True
    assert unknown["may_not_route_to_learning_as_success_or_failure_evidence"] is True


def test_pass_only_eval_does_not_expand_creative_departments():
    payload = case("EOE-EXACT-PASS-001")["payload"]
    result = atlas().resolve_expected_observed(
        payload,
        project_root=ROOT,
        expected_work_item_id="TEST-SHOT-001",
    )
    assert result.materiality == "INFORMATIONAL"
    assert result.problem_signatures == ()
    assert result.selected_capabilities == ()
    assert result.work_item_projection == "TEST-SHOT-001"


def test_work_item_projection_mismatch_fails_but_projection_is_not_authority():
    payload = case("EOE-EXACT-PASS-001")["payload"]
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve_expected_observed(
            payload,
            project_root=ROOT,
            expected_work_item_id="OTHER-WORK-ITEM",
        )
    assert exc.value.code == "TRUSTED_ADAPTER_WORK_ITEM_PROJECTION_MISMATCH"


def test_trusted_receipt_cannot_be_replaced_to_forge_repair_items():
    payload = case("EOE-EXPLICIT-FAIL-001")["payload"]
    receipt = compile_expected_observed_coordination(payload, project_root=ROOT)
    require_trusted_eval_receipt(receipt)
    forged = replace(
        receipt,
        repair_items=(
            TrustedRepairItem(
                field="capture_intent",
                outcome="FAIL",
                failure_category="dialogue",
                repair_surface="SOUND_OR_AV_REVIEW",
                evidence_refs=("frame_004",),
            ),
        ),
    )
    with pytest.raises(ProductionIntelligenceError) as exc:
        require_trusted_eval_receipt(forged)
    assert exc.value.code == "TRUSTED_SIGNAL_RECEIPT_REQUIRED"


def test_adapter_policy_change_after_receipt_is_fresh_revalidated_at_final_consumer(monkeypatch):
    payload = case("EOE-EXPLICIT-FAIL-001")["payload"]
    instance = atlas()
    receipt = compile_expected_observed_coordination(payload, project_root=ROOT)
    original = trusted_adapter_module.load_trusted_adapter_policy

    def changed_policy(project_root):
        policy = original(project_root)
        policy["failure_category_consumer_map"]["camera"] = ["CAP-SOUND"]
        return policy

    monkeypatch.setattr(trusted_adapter_module, "load_trusted_adapter_policy", changed_policy)
    with pytest.raises(ProductionIntelligenceError) as exc:
        instance.resolve(receipt)
    assert exc.value.code in {
        "TRUSTED_ADAPTER_POLICY_STALE",
        "TRUSTED_ADAPTER_CONSUMER_ESCAPES_REPAIR_SURFACE",
    }


def test_same_repair_policy_id_but_changed_content_invalidates_receipt_at_final_consumer(monkeypatch):
    """Exact T3 blocker: stable policy_id must not make stale routing semantics reusable."""
    payload = case("EOE-EXPLICIT-FAIL-001")["payload"]
    instance = atlas()
    receipt = compile_expected_observed_coordination(payload, project_root=ROOT)
    original = trusted_adapter_module.load_yaml
    repair_path = (ROOT / TARGETED_REPAIR_POLICY_PATH).resolve()

    def changed_repair_policy(path):
        loaded = original(path)
        if Path(path).resolve() == repair_path:
            loaded["same_policy_id_content_revision_probe"] = "changed-after-receipt"
        return loaded

    monkeypatch.setattr(trusted_adapter_module, "load_yaml", changed_repair_policy)
    with pytest.raises(ProductionIntelligenceError) as exc:
        instance.resolve(receipt)
    assert exc.value.code == "TRUSTED_ADAPTER_REPAIR_POLICY_STALE"


def test_atlas_cannot_switch_project_root_during_expected_observed_resolution(tmp_path):
    payload = case("EOE-EXACT-PASS-001")["payload"]
    instance = atlas()
    with pytest.raises(ProductionIntelligenceError) as exc:
        instance.resolve_expected_observed(payload, project_root=tmp_path)
    assert exc.value.code == "TRUSTED_ADAPTER_PROJECT_ROOT_FORBIDDEN"


def test_caller_capability_selection_has_no_public_entry_point():
    forged = fake_serialized_signal(signatures=["future_unknown_signal_not_in_graph"])
    forged["payload"]["selected_capabilities"] = ["CAP-LEARNING"]
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(forged)
    assert exc.value.code == "TRUSTED_SIGNAL_RECEIPT_REQUIRED"
