from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "10_运行时/production_intelligence_epistemic_cycle_policy.yaml"


def load_policy():
    return yaml.safe_load(POLICY.read_text(encoding="utf-8"))


def test_three_knowledge_axes_are_explicit_and_orthogonal():
    policy = load_policy()
    coords = policy["knowledge_coordinate_system"]
    assert coords["axes_are_orthogonal"] is True
    assert set(coords["axes"]) == {
        "epistemic_relationship",
        "abstraction_level",
        "validation_maturity",
    }
    assert "K1_EXPLICIT_USER" in coords["axes"]["epistemic_relationship"]["values"]
    assert "L3_causal_mechanism" in coords["axes"]["abstraction_level"]["values"]
    assert "needs_revalidation" in coords["axes"]["validation_maturity"]["values"]


def test_tacit_elicitation_never_grants_user_confirmation():
    policy = load_policy()
    boundary = policy["authority_boundary"]["rules"]
    assert "this_policy_cannot_create_user_confirmed_preference" in boundary
    tacit = policy["tacit_elicitation"]
    assert tacit["maturity"].startswith("candidate")
    assert "user_confirmation_status" in tacit["candidate_fields"]
    assert tacit["pairwise_preference"]["may_learn_global_total_order_by_default"] is False
    assert tacit["pairwise_preference"]["inconsistent_cycles_are_not_auto_error"] is True


def test_nested_cycles_prevent_inner_loop_authority_leak():
    policy = load_policy()
    cycles = policy["production_cycles"]
    assert cycles["nested"] is True
    assert cycles["cycles"]["C1_SHOT_PRODUCTION"]["may_mutate_outer_canonical"] is False
    assert cycles["cycles"]["C5_PROJECT_ARCHITECTURE"]["independent_review_required_for_material_changes"] is True
    assert "C1_model_workaround_cannot_change_C3_map_story_or_formal_asset_identity" in cycles["containment_rules"]


def test_verification_and_validation_are_not_collapsed():
    policy = load_policy()["verification_vs_validation"]
    assert policy["VERIFICATION"]["question"] != policy["VALIDATION"]["question"]
    assert "verification_pass_does_not_imply_validation_pass" in policy["rules"]


def test_dsm_is_bounded_to_complex_coupled_work():
    policy = load_policy()["coupling_and_dependency_management"]
    assert policy["method"] == "temporary_design_structure_matrix_when_complexity_warrants"
    assert policy["anti_bloat"] == "do_not_build_DSM_for_simple_single_capability_task"
    assert policy["interpretation"]["strong_bidirectional_cluster"].startswith("iterate_as_microcycle")


def test_information_value_has_cost_and_reuse_not_fake_number():
    policy = load_policy()["information_value_routing"]
    assert policy["no_fake_precision"] is True
    components = set(policy["qualitative_priority_components"])
    assert "expected_decision_relevant_information_gain" in components
    assert "future_reuse_value" in components
    assert "generation_cost" in components
    assert "user_effort" in components


def test_multifidelity_is_dimension_level_and_version_bound():
    ledger = load_policy()["multi_fidelity_ledger"]
    assert "dimensions_supported_for_screening" in ledger["per_fidelity_fields"]
    assert "dimensions_not_transferable" in ledger["per_fidelity_fields"]
    assert "proxy_must_have_dimension_level_transfer_evidence" in ledger["rules"]
    assert "version_change_triggers_revalidation" in ledger["rules"]


def test_productive_iteration_and_rework_are_distinct():
    classes = load_policy()["iteration_classification"]
    assert "PRODUCTIVE_ITERATION" in classes
    assert "AVOIDABLE_REWORK" in classes
    assert "CREATIVE_EXPLORATION" in classes
    assert "wrong_asset_or_version" in classes["AVOIDABLE_REWORK"]["examples"]
