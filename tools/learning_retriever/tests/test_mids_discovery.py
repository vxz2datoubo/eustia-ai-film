from pathlib import Path
import ast
import copy

import pytest
import yaml

from learning_retriever.feature_compiler import compile_director_features
from learning_retriever.mids_discovery import (
    MIDSDiscoveryError,
    accept_ai_proposal,
    add_ai_proposal,
    add_tacit_candidate,
    add_unknown,
    add_user_confirmed_decision,
    compile_spec_candidate,
    confirm_tacit_candidate,
    new_session,
    rank_questions,
    reject_alternative,
    score_replay,
    set_material_director_intent,
    validate_handoff_ready,
    validate_session,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REPLAYS = yaml.safe_load(
    (REPO_ROOT / "11_验收/mids_discovery_replay_cases.yaml").read_text(encoding="utf-8")
)


def user_prov(ref="turn-user-1"):
    return [{"source": "USER", "ref": ref}]


def trusted_binding():
    return {
        "mode": "TRUSTED_EXISTING",
        "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
        "trust_basis": "canonical_github_readback_verified_snapshot",
    }


def base_session():
    return new_session(
        "我大概想要这种感觉，但不知道具体应该怎么做",
        provenance=user_prov(),
        work_item_binding=trusted_binding(),
    )


def make_ready_session():
    s = base_session()
    s = set_material_director_intent(
        s,
        "观众应看到凯姆熟练解决横向移动问题，笑点来自意外而不是他的无能。",
        provenance=user_prov("intent"),
    )
    s = add_user_confirmed_decision(
        s,
        decision_id="D-COMEDY",
        statement="凯姆保持熟练、干冷，不能拍成笨拙小丑。",
        provenance=user_prov("decision"),
    )
    s["success_criteria"].append(
        {"criterion_id": "C1", "statement": "凯姆能力感不因笑点下降"}
    )
    s["examples"].append(
        {"example_id": "E1", "kind": "POSITIVE", "statement": "意外衣物挂身上但他不停顿地解决"}
    )
    s["counterexamples"].append(
        {"example_id": "E2", "statement": "凯姆手忙脚乱导致自己失败"}
    )
    s["non_goals"].append({"statement": "不把桥段拍成卡通喜剧"})
    s["downstream_dependencies"].append({"task_class": "DIRECTOR_FEATURE_COMPILATION"})
    return s


def test_candidate_is_shadow_and_work_item_is_projection_only():
    s = base_session()
    assert s["mode"] == "SHADOW_CANDIDATE"
    assert s["work_item_binding"]["work_item_id"] == "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
    validate_session(s)


def test_unbound_discovery_cannot_mint_canonical_work_item_identity():
    with pytest.raises(MIDSDiscoveryError) as exc:
        new_session(
            "想设计一个还没确定的新镜头",
            provenance=user_prov(),
            work_item_binding={"mode": "NEW_UNBOUND", "work_item_id": "FAKE-CANONICAL-ID"},
        )
    assert exc.value.code == "MIDS_UNBOUND_WORK_ITEM_CANNOT_CLAIM_CANONICAL_ID"


def test_tacit_candidate_does_not_enter_confirmed_state_until_user_confirms():
    s = add_tacit_candidate(
        base_session(),
        decision_id="T1",
        statement="用户可能偏好让动作笑点服从角色能力感",
        confidence="MEDIUM",
        provenance=[{"source": "PROJECT_FEEDBACK_INFERENCE", "ref": "case-a"}],
    )
    assert not s["confirmed_decisions"]
    s2 = confirm_tacit_candidate(
        s, "T1", user_confirmation_provenance=user_prov("confirm-t1")
    )
    assert any(x["decision_id"] == "T1" for x in s2["confirmed_decisions"])


def test_ai_proposal_remains_proposal_until_user_accepts_and_origin_is_preserved():
    s = add_ai_proposal(
        base_session(),
        proposal_id="P-WHITE-MODEL",
        statement="把动作几何与外观参考分开",
        rationale="降低动作参考图外观污染风险",
        expected_effect="几何控制更清晰，同时减少脏纹理迁移",
        risks=["可能增加准备步骤"],
        criteria=["reference_role_separation"],
    )
    assert s["candidate_directions"][0]["status"] == "PROPOSED"
    assert not s["confirmed_decisions"]
    s = accept_ai_proposal(
        s, "P-WHITE-MODEL", user_acceptance_provenance=user_prov("accept-p")
    )
    record = next(
        x for x in s["confirmed_decisions"] if x["decision_id"] == "P-WHITE-MODEL"
    )
    assert record["epistemic_class"] == "AI_DISCOVERABLE_OPTION"
    assert record["status"] == "ACCEPTED"
    assert record["user_acceptance_provenance"][0]["source"] == "USER"


def test_rejected_ai_proposal_cannot_leak_into_compiled_spec():
    s = make_ready_session()
    s = add_ai_proposal(
        s,
        proposal_id="P-CLOWN",
        statement="让凯姆滑行时手忙脚乱来增强笑点",
        rationale="更直接的喜剧",
        expected_effect="更强即时笑声",
    )
    s = reject_alternative(
        s,
        "P-CLOWN",
        user_rejection_provenance=user_prov("reject"),
        reason="会破坏凯姆能力感",
    )
    spec = compile_spec_candidate(s)
    assert "P-CLOWN" in spec["rejected_alternative_ids"]
    assert all(x["decision_id"] != "P-CLOWN" for x in spec["confirmed_decisions"])
    assert "手忙脚乱" not in spec["director_intent_text"]


def test_question_budget_hard_caps_at_three():
    candidates = [
        {
            "question_id": f"Q{i}",
            "text": f"问题{i}",
            "resolves_keys": [f"gap{i}"],
            "material": True,
            "decision_impact": 3,
            "uncertainty_reduction": 3,
            "dependency_centrality": 2,
            "irreversibility": 1,
            "novelty_potential": 1,
            "cognitive_load": 1,
            "interruption_cost": 1,
            "requires_technical_jargon": False,
            "rationale": "material gap",
        }
        for i in range(8)
    ]
    assert len(rank_questions(candidates, max_questions=3)["selected"]) == 3
    with pytest.raises(MIDSDiscoveryError) as exc:
        rank_questions(candidates, max_questions=4)
    assert exc.value.code == "MIDS_QUESTION_BUDGET_INVALID"


def test_known_canonical_answer_is_suppressed_even_when_question_scores_high():
    candidate = {
        "question_id": "Q-WORK",
        "text": "你说的是哪个30秒？",
        "resolves_keys": ["work_item_identity"],
        "material": True,
        "blocks_handoff": True,
        "decision_impact": 3,
        "uncertainty_reduction": 3,
        "dependency_centrality": 3,
        "irreversibility": 3,
        "novelty_potential": 0,
        "cognitive_load": 1,
        "interruption_cost": 1,
        "requires_technical_jargon": False,
        "rationale": "identity matters",
    }
    receipt = rank_questions([candidate], canonical_known_keys=["work_item_identity"])
    assert receipt["selected"] == []
    assert receipt["suppressed"] == [
        {"question_id": "Q-WORK", "reason": "ALREADY_KNOWN_OR_RESOLVED"}
    ]


def test_technical_jargon_question_is_suppressed_for_expert_blind_zone_translation():
    candidate = {
        "question_id": "Q-JARGON",
        "text": "选择 latent appearance disentanglement 吗？",
        "resolves_keys": ["reference_role_separation"],
        "material": True,
        "decision_impact": 3,
        "uncertainty_reduction": 3,
        "dependency_centrality": 2,
        "irreversibility": 1,
        "novelty_potential": 2,
        "cognitive_load": 3,
        "interruption_cost": 2,
        "requires_technical_jargon": True,
        "rationale": "expert parameter",
    }
    receipt = rank_questions([candidate])
    assert not receipt["selected"]
    assert receipt["suppressed"][0]["reason"] == "TECHNICAL_JARGON_SHOULD_BE_TRANSLATED"


def test_expert_blind_zone_requires_translated_choice_or_research_action():
    with pytest.raises(MIDSDiscoveryError) as exc:
        add_unknown(
            base_session(),
            unknown_id="U1",
            question="模型的某个底层参数该怎么设？",
            epistemic_class="EXPERT_BLIND_ZONE",
            materiality="HIGH",
            blocks_handoff=True,
        )
    assert exc.value.code == "MIDS_EXPERT_BLIND_ZONE_REQUIRES_TRANSLATION_OR_RESEARCH_ACTION"


def test_material_unknown_blocks_handoff():
    s = make_ready_session()
    s = add_unknown(
        s,
        unknown_id="U-REF",
        question="当前目标模型是否会把动作参考图脏纹理带入成片？",
        epistemic_class="EXPERT_BLIND_ZONE",
        materiality="HIGH",
        next_information_action="controlled_reference_AB",
        user_facing_choice="是否先用干净白模验证几何，再绑定高质量外观参考",
        blocks_handoff=True,
    )
    receipt = validate_handoff_ready(s)
    assert receipt["ready"] is False
    assert "MATERIAL_UNKNOWN_UNRESOLVED" in receipt["blockers"]


def test_handoff_requires_examples_boundaries_and_downstream_dependency():
    s = base_session()
    s = set_material_director_intent(s, "让凯姆保持能力感", provenance=user_prov())
    s = add_user_confirmed_decision(
        s, decision_id="D1", statement="不拍成小丑", provenance=user_prov()
    )
    result = validate_handoff_ready(s)
    assert result["ready"] is False
    assert "SUCCESS_CRITERIA_MISSING" in result["blockers"]
    assert "POSITIVE_EXAMPLE_MISSING" in result["blockers"]
    assert "COUNTEREXAMPLE_OR_NON_GOAL_MISSING" in result["blockers"]
    assert "DOWNSTREAM_DEPENDENCY_MISSING" in result["blockers"]


def test_ready_spec_is_minimum_sufficient_and_does_not_spoof_feature_or_route_receipts():
    spec = compile_spec_candidate(make_ready_session())
    assert spec["status"] == "READY_FOR_FEATURE_COMPILER"
    assert spec["authority_boundary"]["must_enter_existing_director_feature_compiler_next"]
    assert "feature_compiler_receipt" not in spec
    assert "hard_routes" not in spec
    assert "director_intent_text" in spec


def test_spec_does_not_include_unconfirmed_tacit_candidate():
    s = add_tacit_candidate(
        make_ready_session(),
        decision_id="T-UNCONFIRMED",
        statement="可能偏好侧面固定机位",
        confidence="LOW",
        provenance=[{"source": "AI_INFERENCE", "ref": "one-observation"}],
    )
    spec = compile_spec_candidate(s)
    assert "T-UNCONFIRMED" in spec["excluded_tacit_candidates"]
    assert "侧面固定机位" not in spec["director_intent_text"]


@pytest.mark.parametrize("case", REPLAYS["cases"], ids=lambda c: c["case_id"])
def test_replay_first_round_obeys_budget_known_fact_suppression_and_expected_selection(case):
    receipt = rank_questions(
        case["candidate_questions"],
        canonical_known_keys=case.get("canonical_known_keys", []),
        max_questions=case["expected_first_round"]["max_questions"],
    )
    selected_ids = {x["question_id"] for x in receipt["selected"]}
    for qid in case["expected_first_round"].get("must_select", []):
        assert qid in selected_ids
    for qid in case["expected_first_round"].get("must_not_select", []):
        assert qid not in selected_ids
    assert len(receipt["selected"]) <= 3


def test_kaim_replay_discovers_multiple_later_critical_dimensions_in_first_round():
    case = next(
        x for x in REPLAYS["cases"] if x["case_id"] == "MIDS-REPLAY-KAIM-SCARF-001"
    )
    receipt = rank_questions(
        case["candidate_questions"],
        canonical_known_keys=case["canonical_known_keys"],
        max_questions=3,
    )
    result = score_replay(question_receipt=receipt, fixture=case)
    assert result["user_interruption_cognitive_cost"]["questions"] <= 3
    assert result["redundant_question_rate"] == 0.0
    assert result["critical_unknown_discovery"] >= 0.6
    assert result["useful_decisions_per_question"] >= 2 / 3


def test_negative_awir_replay_never_reasks_resolved_work_item_identity():
    case = next(
        x for x in REPLAYS["cases"] if x["case_id"] == "MIDS-REPLAY-AWI-NO-REDUNDANT-001"
    )
    receipt = rank_questions(
        case["candidate_questions"],
        canonical_known_keys=case["canonical_known_keys"],
        max_questions=3,
    )
    selected = {x["question_id"] for x in receipt["selected"]}
    assert "Q-AWI-IDENTITY" not in selected
    assert "Q-AWI-NATURALNESS" in selected
    assert score_replay(question_receipt=receipt, fixture=case)["redundant_question_rate"] == 0.0


def test_replay_metrics_detect_authority_or_rejection_leakage():
    broken = copy.deepcopy(compile_spec_candidate(make_ready_session()))
    broken["rejected_alternative_ids"] = ["BAD"]
    broken["confirmed_decisions"].append(
        {
            "decision_id": "BAD",
            "statement": "bad",
            "epistemic_class": "USER_TACIT_CANDIDATE",
            "status": "INFERRED",
            "provenance": [{"source": "AI_INFERENCE", "ref": "x"}],
        }
    )
    metrics = score_replay(
        question_receipt={"selected": []},
        fixture={"case_id": "BROKEN", "hidden_critical_targets": [], "canonical_known_keys": []},
        spec_candidate=broken,
    )
    assert metrics["contradiction_leakage"] == 1
    assert metrics["authority_violation"] == 1


def test_reconstructed_replay_prompts_are_explicitly_not_verbatim_user_quotes():
    for case in REPLAYS["cases"]:
        assert case["provenance_class"] in {
            "RECONSTRUCTED_FROM_PROJECT_TRACE", "CANONICAL_REGRESSION_DERIVED"
        }
        assert case["initial_fuzzy_input"].strip()


def test_full_transcript_is_not_part_of_session_or_spec_schema():
    s = base_session()
    assert "full_transcript" not in s
    assert "conversation_history" not in s
    spec = compile_spec_candidate(make_ready_session())
    assert "full_transcript" not in spec
    assert "conversation_history" not in spec


def test_ready_spec_hands_natural_language_to_existing_feature_compiler_instead_of_replacing_it():
    s = new_session(
        "群众看到圣女后跪拜，我还没决定具体怎么拍",
        provenance=user_prov("crowd-intent"),
        work_item_binding={"mode": "NEW_UNBOUND"},
    )
    s = set_material_director_intent(
        s,
        "群众看到圣女后跪拜，并明确面向圣女。",
        provenance=user_prov("crowd-intent-confirmed"),
    )
    s = add_user_confirmed_decision(
        s,
        decision_id="D-CROWD-TARGET",
        statement="群众的跪拜目标是圣女。",
        provenance=user_prov("crowd-target"),
    )
    s["success_criteria"].append({"statement": "群众的身体朝向与跪拜目标清楚指向圣女"})
    s["examples"].append({"kind": "POSITIVE", "statement": "群众看到圣女后转身面向她并跪拜"})
    s["counterexamples"].append({"statement": "群众朝摄影机跪而圣女在另一侧"})
    s["downstream_dependencies"].append({"task_class": "DIRECTOR_FEATURE_COMPILATION"})
    spec = compile_spec_candidate(s)
    features = compile_director_features(spec["director_intent_text"])
    assert features.recognized is True
    assert "feature_compiler_receipt" not in spec
    assert "hard_routes" not in spec


def test_candidate_remains_unregistered_and_does_not_inflate_directing_always():
    project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
    read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
    contract = yaml.safe_load(
        (REPO_ROOT / "10_运行时/mixed_initiative_discovery_specification_pilot.yaml").read_text(encoding="utf-8")
    )
    assert contract["status"] == "candidate_shadow"
    assert "mixed_initiative_discovery_specification_pilot" not in project.get("canonical", {})
    assert "10_运行时/mixed_initiative_discovery_specification_pilot.yaml" not in project.get("effective_sources", {})
    assert all(
        "MIDS" not in str(item).upper()
        for item in read_sets["read_sets"]["directing"]["always"]
    )


def test_existing_opportunity_router_keeps_downstream_next_step_role():
    router = yaml.safe_load(
        (REPO_ROOT / "10_运行时/proactive_execution_opportunity_router.yaml").read_text(encoding="utf-8")
    )
    contract = yaml.safe_load(
        (REPO_ROOT / "10_运行时/mixed_initiative_discovery_specification_pilot.yaml").read_text(encoding="utf-8")
    )
    assert "next_step_detection" in router["scope"]
    assert contract["opportunity_router_boundary"]["opportunity_router_may_not_be_replaced_by_MIDS"]
    assert (
        contract["architecture_position"]["downstream_existing_authorities"][-1]
        == "10_运行时/proactive_execution_opportunity_router.yaml"
    )


def test_mids_runtime_has_no_network_git_or_persistence_writer_imports():
    module = REPO_ROOT / "tools/learning_retriever/learning_retriever/mids_discovery.py"
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    forbidden = {"requests", "httpx", "urllib", "socket", "subprocess", "git", "github"}
    assert imports.isdisjoint(forbidden), imports.intersection(forbidden)


def test_replay_suite_declares_hidden_answer_and_authority_boundaries():
    assert REPLAYS["authority_boundary"]["hidden_targets_are_eval_only"]
    assert REPLAYS["authority_boundary"]["replay_prompts_are_not_canonical_user_quotes"]
    assert len(REPLAYS["cases"]) >= 4
