from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "10_运行时/production_intelligence_research_intake_policy.yaml"


def policy():
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def test_external_research_is_not_project_authority():
    p = policy()
    rules = p["authority_boundary"]["rules"]
    assert "external_research_cannot_override_project_story_character_scene_map_asset_or_continuity" in rules
    assert "external_research_cannot_self_promote_maturity" in rules


def test_master_cases_must_use_existing_director_pull():
    route = policy()["integration_routes"]["MASTER_OR_PRODUCTION_CASE"]
    assert route["destination"] == "existing_golden_case_director_pull"
    assert "non_transferable_surface_style" in route["extraction"]
    assert "converting_master_reputation_into_causal_proof" in route["forbidden"]


def test_benchmarks_only_contribute_dimensions_not_aesthetic_authority():
    route = policy()["integration_routes"]["GENERATIVE_MEDIA_BENCHMARK"]
    assert route["destination"] == "evaluation_dimension_candidate"
    assert "importing_one_aggregate_benchmark_score_as_aesthetic_score" in route["forbidden"]


def test_closed_model_cannot_inherit_paper_interface_without_evidence():
    route = policy()["integration_routes"]["GENERATIVE_MEDIA_PAPER"]
    assert "claiming_closed_model_supports_paper_interface_without_evidence" in route["forbidden"]


def test_research_must_start_from_project_problem():
    pipeline = policy()["claim_distillation_pipeline"]
    assert pipeline[0] == "define_current_production_problem"
    assert "define_targeted_validation_before_activation" in pipeline


def test_merge_decision_has_research_only_and_defer_paths():
    decisions = policy()["merge_decision"]
    assert "MERGE_EXISTING" in decisions
    assert "EXTEND_EXISTING" in decisions
    assert "NEW_CANDIDATE_CAPABILITY" in decisions
    assert "RESEARCH_ONLY" in decisions
    assert "REJECT_OR_DEFER" in decisions


def test_frontier_watch_hit_is_not_automatic_writeback():
    freshness = policy()["freshness_and_watch"]
    assert freshness["watch_output_rule"] == "a_watch_hit_is_not_an_automatic_writeback"


def test_high_impact_rule_prefers_cross_validation():
    cross = policy()["cross_validation"]["high_impact_new_rule"]
    assert cross["default"].startswith("seek_second_independent")
    assert cross["still_requires_project_scope_check"] is True
