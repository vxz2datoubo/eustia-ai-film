from pathlib import Path
import ast
import copy
import unittest

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
    session = base_session()
    session = set_material_director_intent(
        session,
        "观众应看到凯姆熟练解决横向移动问题，笑点来自意外而不是他的无能。",
        provenance=user_prov("intent"),
    )
    session = add_user_confirmed_decision(
        session,
        decision_id="D-COMEDY",
        statement="凯姆保持熟练、干冷，不能拍成笨拙小丑。",
        provenance=user_prov("decision"),
    )
    session["success_criteria"].append(
        {"criterion_id": "C1", "statement": "凯姆能力感不因笑点下降"}
    )
    session["examples"].append(
        {"example_id": "E1", "kind": "POSITIVE", "statement": "意外衣物挂身上但他不停顿地解决"}
    )
    session["counterexamples"].append(
        {"example_id": "E2", "statement": "凯姆手忙脚乱导致自己失败"}
    )
    session["non_goals"].append({"statement": "不把桥段拍成卡通喜剧"})
    session["downstream_dependencies"].append({"task_class": "DIRECTOR_FEATURE_COMPILATION"})
    return session


class MIDSDiscoveryTests(unittest.TestCase):
    def test_candidate_is_shadow_and_work_item_is_projection_only(self):
        session = base_session()
        self.assertEqual(session["mode"], "SHADOW_CANDIDATE")
        self.assertEqual(
            session["work_item_binding"]["work_item_id"],
            "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
        )
        validate_session(session)

    def test_unbound_discovery_cannot_mint_canonical_work_item_identity(self):
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            new_session(
                "想设计一个还没确定的新镜头",
                provenance=user_prov(),
                work_item_binding={"mode": "NEW_UNBOUND", "work_item_id": "FAKE-CANONICAL-ID"},
            )
        self.assertEqual(ctx.exception.code, "MIDS_UNBOUND_WORK_ITEM_CANNOT_CLAIM_CANONICAL_ID")

    def test_tacit_candidate_requires_explicit_user_confirmation(self):
        session = add_tacit_candidate(
            base_session(),
            decision_id="T1",
            statement="用户可能偏好让动作笑点服从角色能力感",
            confidence="MEDIUM",
            provenance=[{"source": "PROJECT_FEEDBACK_INFERENCE", "ref": "case-a"}],
        )
        self.assertFalse(session["confirmed_decisions"])
        session = confirm_tacit_candidate(
            session,
            "T1",
            user_confirmation_provenance=user_prov("confirm-t1"),
        )
        self.assertTrue(any(x["decision_id"] == "T1" for x in session["confirmed_decisions"]))

    def test_ai_proposal_requires_user_acceptance_and_keeps_origin(self):
        session = add_ai_proposal(
            base_session(),
            proposal_id="P-WHITE-MODEL",
            statement="把动作几何与外观参考分开",
            rationale="降低动作参考图外观污染风险",
            expected_effect="几何控制更清晰，同时减少脏纹理迁移",
            risks=["可能增加准备步骤"],
            criteria=["reference_role_separation"],
        )
        self.assertEqual(session["candidate_directions"][0]["status"], "PROPOSED")
        self.assertFalse(session["confirmed_decisions"])
        session = accept_ai_proposal(
            session,
            "P-WHITE-MODEL",
            user_acceptance_provenance=user_prov("accept-p"),
        )
        record = next(x for x in session["confirmed_decisions"] if x["decision_id"] == "P-WHITE-MODEL")
        self.assertEqual(record["epistemic_class"], "AI_DISCOVERABLE_OPTION")
        self.assertEqual(record["status"], "ACCEPTED")
        self.assertEqual(record["user_acceptance_provenance"][0]["source"], "USER")

    def test_rejected_ai_proposal_cannot_leak_into_compiled_spec(self):
        session = add_ai_proposal(
            make_ready_session(),
            proposal_id="P-CLOWN",
            statement="让凯姆滑行时手忙脚乱来增强笑点",
            rationale="更直接的喜剧",
            expected_effect="更强即时笑声",
        )
        session = reject_alternative(
            session,
            "P-CLOWN",
            user_rejection_provenance=user_prov("reject"),
            reason="会破坏凯姆能力感",
        )
        spec = compile_spec_candidate(session)
        self.assertIn("P-CLOWN", spec["rejected_alternative_ids"])
        self.assertTrue(all(x["decision_id"] != "P-CLOWN" for x in spec["confirmed_decisions"]))
        self.assertNotIn("手忙脚乱", spec["director_intent_text"])

    def test_question_budget_hard_caps_at_three(self):
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
        self.assertEqual(len(rank_questions(candidates, max_questions=3)["selected"]), 3)
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            rank_questions(candidates, max_questions=4)
        self.assertEqual(ctx.exception.code, "MIDS_QUESTION_BUDGET_INVALID")

    def test_known_canonical_answer_is_suppressed(self):
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
        self.assertEqual(receipt["selected"], [])
        self.assertEqual(
            receipt["suppressed"],
            [{"question_id": "Q-WORK", "reason": "ALREADY_KNOWN_OR_RESOLVED"}],
        )

    def test_technical_jargon_question_is_suppressed(self):
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
        self.assertFalse(receipt["selected"])
        self.assertEqual(receipt["suppressed"][0]["reason"], "TECHNICAL_JARGON_SHOULD_BE_TRANSLATED")

    def test_expert_blind_zone_requires_translation_or_research_action(self):
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            add_unknown(
                base_session(),
                unknown_id="U1",
                question="模型的某个底层参数该怎么设？",
                epistemic_class="EXPERT_BLIND_ZONE",
                materiality="HIGH",
                blocks_handoff=True,
            )
        self.assertEqual(
            ctx.exception.code,
            "MIDS_EXPERT_BLIND_ZONE_REQUIRES_TRANSLATION_OR_RESEARCH_ACTION",
        )

    def test_material_unknown_blocks_handoff(self):
        session = add_unknown(
            make_ready_session(),
            unknown_id="U-REF",
            question="当前目标模型是否会把动作参考图脏纹理带入成片？",
            epistemic_class="EXPERT_BLIND_ZONE",
            materiality="HIGH",
            next_information_action="controlled_reference_AB",
            user_facing_choice="是否先用干净白模验证几何，再绑定高质量外观参考",
            blocks_handoff=True,
        )
        receipt = validate_handoff_ready(session)
        self.assertFalse(receipt["ready"])
        self.assertIn("MATERIAL_UNKNOWN_UNRESOLVED", receipt["blockers"])

    def test_handoff_requires_examples_boundaries_and_downstream_dependency(self):
        session = set_material_director_intent(
            base_session(), "让凯姆保持能力感", provenance=user_prov()
        )
        session = add_user_confirmed_decision(
            session, decision_id="D1", statement="不拍成小丑", provenance=user_prov()
        )
        result = validate_handoff_ready(session)
        self.assertFalse(result["ready"])
        for blocker in (
            "SUCCESS_CRITERIA_MISSING",
            "POSITIVE_EXAMPLE_MISSING",
            "COUNTEREXAMPLE_OR_NON_GOAL_MISSING",
            "DOWNSTREAM_DEPENDENCY_MISSING",
        ):
            self.assertIn(blocker, result["blockers"])

    def test_ready_spec_does_not_spoof_feature_or_route_receipts(self):
        spec = compile_spec_candidate(make_ready_session())
        self.assertEqual(spec["status"], "READY_FOR_FEATURE_COMPILER")
        self.assertTrue(spec["authority_boundary"]["must_enter_existing_director_feature_compiler_next"])
        self.assertNotIn("feature_compiler_receipt", spec)
        self.assertNotIn("hard_routes", spec)

    def test_spec_excludes_unconfirmed_tacit_candidate(self):
        session = add_tacit_candidate(
            make_ready_session(),
            decision_id="T-UNCONFIRMED",
            statement="可能偏好侧面固定机位",
            confidence="LOW",
            provenance=[{"source": "AI_INFERENCE", "ref": "one-observation"}],
        )
        spec = compile_spec_candidate(session)
        self.assertIn("T-UNCONFIRMED", spec["excluded_tacit_candidates"])
        self.assertNotIn("侧面固定机位", spec["director_intent_text"])

    def test_replay_first_round_contracts(self):
        for case in REPLAYS["cases"]:
            with self.subTest(case=case["case_id"]):
                receipt = rank_questions(
                    case["candidate_questions"],
                    canonical_known_keys=case.get("canonical_known_keys", []),
                    max_questions=case["expected_first_round"]["max_questions"],
                )
                selected = {x["question_id"] for x in receipt["selected"]}
                for qid in case["expected_first_round"].get("must_select", []):
                    self.assertIn(qid, selected)
                for qid in case["expected_first_round"].get("must_not_select", []):
                    self.assertNotIn(qid, selected)
                self.assertLessEqual(len(receipt["selected"]), 3)

    def test_kaim_replay_discovers_multiple_later_critical_dimensions(self):
        case = next(x for x in REPLAYS["cases"] if x["case_id"] == "MIDS-REPLAY-KAIM-SCARF-001")
        receipt = rank_questions(
            case["candidate_questions"],
            canonical_known_keys=case["canonical_known_keys"],
            max_questions=3,
        )
        result = score_replay(question_receipt=receipt, fixture=case)
        self.assertLessEqual(result["user_interruption_cognitive_cost"]["questions"], 3)
        self.assertEqual(result["redundant_question_rate"], 0.0)
        self.assertGreaterEqual(result["critical_unknown_discovery"], 0.6)
        self.assertGreaterEqual(result["useful_decisions_per_question"], 2 / 3)

    def test_awir_negative_control_never_reasks_work_item_identity(self):
        case = next(x for x in REPLAYS["cases"] if x["case_id"] == "MIDS-REPLAY-AWI-NO-REDUNDANT-001")
        receipt = rank_questions(
            case["candidate_questions"],
            canonical_known_keys=case["canonical_known_keys"],
            max_questions=3,
        )
        selected = {x["question_id"] for x in receipt["selected"]}
        self.assertNotIn("Q-AWI-IDENTITY", selected)
        self.assertIn("Q-AWI-NATURALNESS", selected)
        self.assertEqual(score_replay(question_receipt=receipt, fixture=case)["redundant_question_rate"], 0.0)

    def test_replay_metrics_detect_authority_and_rejection_leakage(self):
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
        self.assertEqual(metrics["contradiction_leakage"], 1)
        self.assertEqual(metrics["authority_violation"], 1)

    def test_replay_prompts_are_not_claimed_as_verbatim_user_quotes(self):
        for case in REPLAYS["cases"]:
            self.assertIn(
                case["provenance_class"],
                {"RECONSTRUCTED_FROM_PROJECT_TRACE", "CANONICAL_REGRESSION_DERIVED"},
            )
            self.assertTrue(case["initial_fuzzy_input"].strip())

    def test_full_transcript_is_absent_from_session_and_spec(self):
        session = base_session()
        self.assertNotIn("full_transcript", session)
        self.assertNotIn("conversation_history", session)
        spec = compile_spec_candidate(make_ready_session())
        self.assertNotIn("full_transcript", spec)
        self.assertNotIn("conversation_history", spec)

    def test_spec_hands_natural_language_to_existing_feature_compiler(self):
        session = new_session(
            "群众看到圣女后跪拜，我还没决定具体怎么拍",
            provenance=user_prov("crowd-intent"),
            work_item_binding={"mode": "NEW_UNBOUND"},
        )
        session = set_material_director_intent(
            session,
            "群众看到圣女后跪拜，并明确面向圣女。",
            provenance=user_prov("crowd-intent-confirmed"),
        )
        session = add_user_confirmed_decision(
            session,
            decision_id="D-CROWD-TARGET",
            statement="群众的跪拜目标是圣女。",
            provenance=user_prov("crowd-target"),
        )
        session["success_criteria"].append({"statement": "群众的身体朝向与跪拜目标清楚指向圣女"})
        session["examples"].append({"kind": "POSITIVE", "statement": "群众看到圣女后转身面向她并跪拜"})
        session["counterexamples"].append({"statement": "群众朝摄影机跪而圣女在另一侧"})
        session["downstream_dependencies"].append({"task_class": "DIRECTOR_FEATURE_COMPILATION"})
        spec = compile_spec_candidate(session)
        features = compile_director_features(spec["director_intent_text"])
        self.assertTrue(features.recognized)
        self.assertNotIn("feature_compiler_receipt", spec)
        self.assertNotIn("hard_routes", spec)

    def test_candidate_remains_unregistered_and_does_not_inflate_directing_always(self):
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))
        contract = yaml.safe_load(
            (REPO_ROOT / "10_运行时/mixed_initiative_discovery_specification_pilot.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(contract["status"], "candidate_shadow")
        self.assertNotIn("mixed_initiative_discovery_specification_pilot", project.get("canonical", {}))
        self.assertNotIn(
            "10_运行时/mixed_initiative_discovery_specification_pilot.yaml",
            project.get("effective_sources", {}),
        )
        self.assertTrue(
            all("MIDS" not in str(item).upper() for item in read_sets["read_sets"]["directing"]["always"])
        )

    def test_existing_opportunity_router_keeps_downstream_role(self):
        router = yaml.safe_load(
            (REPO_ROOT / "10_运行时/proactive_execution_opportunity_router.yaml").read_text(encoding="utf-8")
        )
        contract = yaml.safe_load(
            (REPO_ROOT / "10_运行时/mixed_initiative_discovery_specification_pilot.yaml").read_text(encoding="utf-8")
        )
        self.assertIn("next_step_detection", router["scope"])
        self.assertTrue(contract["opportunity_router_boundary"]["opportunity_router_may_not_be_replaced_by_MIDS"])
        self.assertEqual(
            contract["architecture_position"]["downstream_existing_authorities"][-1],
            "10_运行时/proactive_execution_opportunity_router.yaml",
        )

    def test_mids_runtime_has_no_network_git_or_persistence_writer_imports(self):
        module = REPO_ROOT / "tools/learning_retriever/learning_retriever/mids_discovery.py"
        tree = ast.parse(module.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        forbidden = {"requests", "httpx", "urllib", "socket", "subprocess", "git", "github"}
        self.assertTrue(imports.isdisjoint(forbidden), imports.intersection(forbidden))

    def test_replay_suite_declares_hidden_answer_and_authority_boundaries(self):
        self.assertTrue(REPLAYS["authority_boundary"]["hidden_targets_are_eval_only"])
        self.assertTrue(REPLAYS["authority_boundary"]["replay_prompts_are_not_canonical_user_quotes"])
        self.assertGreaterEqual(len(REPLAYS["cases"]), 4)


if __name__ == "__main__":
    unittest.main()
