import copy
import unittest

from learning_retriever.mids_discovery import (
    MIDSDiscoveryError,
    accept_ai_proposal,
    add_ai_proposal,
    add_contradiction,
    add_unknown,
    add_user_confirmed_decision,
    new_session,
    reject_alternative,
    resolve_contradiction,
    resolve_unknown,
    revoke_accepted_ai_proposal,
    set_material_director_intent,
    validate_handoff_ready,
    validate_session,
)
from learning_retriever.mids_handoff_guard import compile_guarded_spec_candidate


def user(ref="user"):
    return [{"source": "USER", "ref": ref}]


def user_basis(ref="answer"):
    return {"type": "USER_DECISION", "provenance": user(ref), "result_ref": ref}


def evidence_basis(ref="evidence"):
    return {"type": "RESEARCH_EVIDENCE", "provenance": [{"source": "EVIDENCE", "ref": ref}], "result_ref": ref}


def base_session():
    return new_session("继续这个镜头，但还有几个关键问题没想清楚", provenance=user("raw"), work_item_binding={"mode": "NEW_UNBOUND"})


def ready_session():
    session = base_session()
    session = set_material_director_intent(session, "凯姆保持熟练，笑点来自意外。", provenance=user("intent"))
    session = add_user_confirmed_decision(
        session, decision_id="D1", statement="不能拍成笨拙小丑。", provenance=user("d1")
    )
    session["success_criteria"].append({"statement": "能力感成立"})
    session["examples"].append({"kind": "POSITIVE", "statement": "意外发生但动作不停"})
    session["counterexamples"].append({"statement": "手忙脚乱"})
    session["downstream_dependencies"].append({"task_class": "DIRECTOR_FEATURE_COMPILATION"})
    validate_session(session)
    return session


class MIDSTransitionAuthorityTests(unittest.TestCase):
    def test_scalar_id_collision_fails_before_ai_proposal_can_exist(self):
        session = ready_session()
        before = copy.deepcopy(session["confirmed_decisions"])
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            add_ai_proposal(
                session, proposal_id="D1", statement="碰撞用户ID",
                rationale="attack", expected_effect="erase user choice",
            )
        self.assertEqual(ctx.exception.code, "MIDS_DECISION_ID_COLLISION")
        self.assertEqual(session["confirmed_decisions"], before)

    def test_ai_cannot_reject_proposal_without_user_provenance(self):
        session = add_ai_proposal(
            ready_session(), proposal_id="P1", statement="用夸张动作",
            rationale="candidate", expected_effect="more comedy",
        )
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            reject_alternative(
                session, "P1",
                user_rejection_provenance=[{"source": "AI", "ref": "self"}],
                reason="self rejection",
            )
        self.assertEqual(ctx.exception.code, "MIDS_TRUSTED_USER_RECEIPT_REQUIRED")

    def test_open_rejection_preserves_unrelated_user_decision(self):
        session = add_ai_proposal(
            ready_session(), proposal_id="P1", statement="用夸张动作",
            rationale="candidate", expected_effect="more comedy",
        )
        session = reject_alternative(session, "P1", user_rejection_provenance=user("reject"), reason="破坏能力感")
        self.assertEqual([x["decision_id"] for x in session["confirmed_decisions"]], ["D1"])
        self.assertEqual(session["candidate_directions"][0]["status"], "REJECTED")
        self.assertEqual(session["mids_transition_log"][-1]["from_status"], "PROPOSED")
        self.assertEqual(session["mids_transition_log"][-1]["to_status"], "REJECTED")

    def test_accepted_proposal_requires_revocation_and_history_moves_out_of_confirmed(self):
        session = add_ai_proposal(
            ready_session(), proposal_id="P2", statement="先白模验证",
            rationale="reduce contamination", expected_effect="clean geometry",
        )
        session = accept_ai_proposal(session, "P2", user_acceptance_provenance=user("accept"))
        with self.assertRaises(MIDSDiscoveryError):
            reject_alternative(session, "P2", user_rejection_provenance=user("reject"), reason="changed mind")
        session = revoke_accepted_ai_proposal(
            session, "P2", user_revocation_provenance=user("revoke"), reason="用户明确撤销"
        )
        self.assertFalse(any(x["decision_id"] == "P2" for x in session["confirmed_decisions"]))
        self.assertEqual(session["revoked_decisions"][0]["decision_id"], "P2")
        self.assertEqual(session["revoked_decisions"][0]["status"], "REVOKED")
        self.assertEqual(session["candidate_directions"][-1]["status"], "REVOKED")
        validate_session(session)

    def test_direct_unknown_resolved_mutation_with_typed_user_basis_still_needs_transition(self):
        session = add_unknown(
            ready_session(), unknown_id="U1", question="是否接受先白模？",
            epistemic_class="USER_TACIT_CANDIDATE", materiality="HIGH",
            user_facing_choice="先白模还是直接生成", blocks_handoff=True,
        )
        forged = copy.deepcopy(session)
        forged["unknowns"][0]["status"] = "RESOLVED"
        forged["unknowns"][0]["resolution_basis"] = user_basis("forged-user-basis")
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_UNKNOWN_RESOLUTION_TRANSITION_MISSING")

    def test_research_label_cannot_self_resolve_material_unknown(self):
        session = add_unknown(
            ready_session(), unknown_id="U2", question="模型会不会污染参考纹理？",
            epistemic_class="EXPERT_BLIND_ZONE", materiality="HIGH",
            next_information_action="controlled_AB", blocks_handoff=True,
        )
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            resolve_unknown(session, "U2", resolution_basis=evidence_basis())
        self.assertEqual(ctx.exception.code, "MIDS_EXTERNAL_RESOLUTION_REQUIRES_AUTHORITY_ADAPTER")
        self.assertIn("MATERIAL_UNKNOWN_UNRESOLVED", validate_handoff_ready(session)["blockers"])

    def test_user_resolution_creates_transition_and_clears_unknown_blocker(self):
        session = add_unknown(
            ready_session(), unknown_id="U3", question="是否接受先白模？",
            epistemic_class="USER_TACIT_CANDIDATE", materiality="HIGH",
            user_facing_choice="先白模还是直接生成", blocks_handoff=True,
        )
        session = resolve_unknown(session, "U3", resolution_basis=user_basis("user-choice"))
        self.assertNotIn("MATERIAL_UNKNOWN_UNRESOLVED", validate_handoff_ready(session)["blockers"])
        transition = session["mids_transition_log"][-1]
        self.assertEqual((transition["target_kind"], transition["from_status"], transition["to_status"]), ("UNKNOWN", "OPEN", "RESOLVED"))
        self.assertEqual(transition["basis_type"], "USER_DECISION")

    def test_direct_contradiction_resolved_mutation_with_basis_still_needs_transition(self):
        session = add_contradiction(ready_session(), contradiction_id="C1", statement="两个目标冲突")
        forged = copy.deepcopy(session)
        forged["contradictions"][0]["status"] = "RESOLVED"
        forged["contradictions"][0]["resolution_basis"] = user_basis("forged")
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_CONTRADICTION_RESOLUTION_TRANSITION_MISSING")

    def test_external_evidence_cannot_self_resolve_contradiction(self):
        session = add_contradiction(ready_session(), contradiction_id="C2", statement="两条资料冲突")
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            resolve_contradiction(session, "C2", resolution_basis=evidence_basis("research-2"))
        self.assertEqual(ctx.exception.code, "MIDS_EXTERNAL_RESOLUTION_REQUIRES_AUTHORITY_ADAPTER")

    def test_user_contradiction_resolution_creates_transition(self):
        session = add_contradiction(ready_session(), contradiction_id="C3", statement="两个用户目标冲突")
        session = resolve_contradiction(session, "C3", resolution_basis=user_basis("priority-choice"))
        self.assertNotIn("MATERIAL_CONTRADICTION_UNRESOLVED", validate_handoff_ready(session)["blockers"])
        self.assertEqual(session["mids_transition_log"][-1]["target_kind"], "CONTRADICTION")

    def test_guarded_handoff_rejects_caller_forged_research_resolution(self):
        session = add_unknown(
            ready_session(), unknown_id="U4", question="模型会不会污染纹理？",
            epistemic_class="EXPERT_BLIND_ZONE", materiality="HIGH",
            next_information_action="controlled_AB", blocks_handoff=True,
        )
        forged = copy.deepcopy(session)
        forged["unknowns"][0]["status"] = "RESOLVED"
        forged["unknowns"][0]["resolution_basis"] = evidence_basis("fake-evidence")
        forged["mids_transition_log"].append({
            "event_type": "STATE_TRANSITION", "target_kind": "UNKNOWN", "target_id": "U4",
            "from_status": "OPEN", "to_status": "RESOLVED", "basis_type": "RESEARCH_EVIDENCE",
            "basis_ref": "fake-evidence", "provenance": [{"source": "EVIDENCE", "ref": "fake-evidence"}],
        })
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            compile_guarded_spec_candidate(forged)
        self.assertEqual(ctx.exception.code, "MIDS_EXTERNAL_RESOLUTION_REQUIRES_AUTHORITY_ADAPTER")


if __name__ == "__main__":
    unittest.main()
