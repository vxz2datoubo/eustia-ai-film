import copy
import unittest

from learning_retriever.mids_discovery import (
    MIDSDiscoveryError,
    accept_ai_proposal,
    add_ai_proposal,
    add_contradiction,
    add_tacit_candidate,
    add_unknown,
    add_user_confirmed_decision,
    confirm_tacit_candidate,
    new_session,
    reject_alternative,
    revoke_accepted_ai_proposal,
    set_material_director_intent,
    validate_handoff_ready,
    validate_session,
)


def user(ref):
    return [{"source": "USER", "ref": ref}]


def transition_session():
    session = new_session(
        "继续这个镜头，但还有几个关键问题没想清楚",
        provenance=user("raw"), work_item_binding={"mode": "NEW_UNBOUND"},
    )
    session = set_material_director_intent(
        session, "凯姆保持熟练，笑点来自意外。", provenance=user("intent"),
    )
    session = add_user_confirmed_decision(
        session, decision_id="D1", statement="不能拍成笨拙小丑。", provenance=user("d1"),
    )
    session["success_criteria"].append({"statement": "能力感成立"})
    session["examples"].append({"kind": "POSITIVE", "statement": "意外发生但动作不停"})
    session["counterexamples"].append({"statement": "手忙脚乱"})
    session["downstream_dependencies"].append({"task_class": "DIRECTOR_FEATURE_COMPILATION"})
    validate_session(session)
    return session


def main_session():
    return new_session(
        "我大概想要这种感觉，但不知道具体应该怎么做",
        provenance=user("turn-user-1"), work_item_binding={"mode": "NEW_UNBOUND"},
    )


def user_basis(ref):
    return {"type": "USER_DECISION", "provenance": user(ref), "result_ref": ref}


class MIDSReviewRemediationTests(unittest.TestCase):
    def test_lowercase_high_materiality_fails_closed_at_public_session_boundary(self):
        session = transition_session()
        session["unknowns"].append({
            "unknown_id": "U-LOWER-HIGH", "question": "关键选择？",
            "epistemic_class": "USER_TACIT_CANDIDATE", "materiality": "high",
            "status": "OPEN", "blocks_handoff": False,
        })
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            validate_handoff_ready(session)
        self.assertEqual(ctx.exception.code, "MIDS_UNKNOWN_MATERIALITY_NONCANONICAL")

    def test_lowercase_open_status_fails_closed_at_public_session_boundary(self):
        session = transition_session()
        session["unknowns"].append({
            "unknown_id": "U-LOWER-OPEN", "question": "材料未知？",
            "epistemic_class": "USER_TACIT_CANDIDATE", "materiality": "MATERIAL",
            "status": "open", "blocks_handoff": False,
        })
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            validate_handoff_ready(session)
        self.assertEqual(ctx.exception.code, "MIDS_UNKNOWN_STATUS_NONCANONICAL")

    def test_lowercase_resolved_unknown_cannot_skip_transition_receipt_validation(self):
        session = add_unknown(
            transition_session(), unknown_id="U-LOWER-RESOLVED", question="是否解决？",
            epistemic_class="USER_TACIT_CANDIDATE", materiality="HIGH", blocks_handoff=True,
        )
        forged = copy.deepcopy(session)
        forged["unknowns"][0]["status"] = "resolved"
        forged["unknowns"][0]["resolution_basis"] = user_basis("forged-user-basis")
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_UNKNOWN_STATUS_NONCANONICAL")

    def test_lowercase_resolved_contradiction_cannot_skip_transition_receipt_validation(self):
        session = add_contradiction(transition_session(), contradiction_id="C-LOWER", statement="两个目标冲突")
        forged = copy.deepcopy(session)
        forged["contradictions"][0]["status"] = "resolved"
        forged["contradictions"][0]["resolution_basis"] = user_basis("forged")
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_CONTRADICTION_STATUS_NONCANONICAL")

    def test_add_unknown_rejects_duplicate_identifier(self):
        session = add_unknown(
            transition_session(), unknown_id="U-DUP", question="第一次",
            epistemic_class="USER_TACIT_CANDIDATE", materiality="MEDIUM",
        )
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            add_unknown(session, unknown_id="U-DUP", question="第二次",
                        epistemic_class="USER_TACIT_CANDIDATE", materiality="HIGH")
        self.assertEqual(ctx.exception.code, "MIDS_UNKNOWN_ID_DUPLICATE")

    def test_mutated_session_with_duplicate_unknown_ids_is_rejected(self):
        session = add_unknown(
            transition_session(), unknown_id="U-DUP-MUTATED", question="第一次",
            epistemic_class="USER_TACIT_CANDIDATE", materiality="MEDIUM",
        )
        forged = copy.deepcopy(session)
        duplicate = copy.deepcopy(forged["unknowns"][0]); duplicate["question"] = "伪造第二条"
        forged["unknowns"].append(duplicate)
        with self.assertRaises(MIDSDiscoveryError) as ctx: validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_UNKNOWN_ID_DUPLICATE")

    def test_duplicate_contradiction_identifier_rejected_on_insert(self):
        session = add_contradiction(transition_session(), contradiction_id="C-DUP", statement="第一冲突")
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            add_contradiction(session, contradiction_id="C-DUP", statement="第二冲突")
        self.assertEqual(ctx.exception.code, "MIDS_CONTRADICTION_ID_DUPLICATE")

    def test_duplicate_contradiction_identifier_rejected_after_direct_mutation(self):
        session = add_contradiction(transition_session(), contradiction_id="C-DUP-M", statement="第一冲突")
        forged = copy.deepcopy(session); duplicate = copy.deepcopy(forged["contradictions"][0]); duplicate["statement"] = "第二冲突"
        forged["contradictions"].append(duplicate)
        with self.assertRaises(MIDSDiscoveryError) as ctx: validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_CONTRADICTION_ID_DUPLICATE")

    def test_accept_receipt_cannot_authorize_rewritten_same_id_proposal(self):
        session = add_ai_proposal(
            transition_session(), proposal_id="P2", statement="先白模验证",
            rationale="reduce contamination", expected_effect="clean geometry",
        )
        forged = copy.deepcopy(session); forged["candidate_directions"][0]["statement"] = "直接改成另一个方案"
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            accept_ai_proposal(forged, "P2", user_acceptance_provenance=user("accept"))
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_accepted_proposal_statement_cannot_be_rewritten_after_acceptance(self):
        session = add_ai_proposal(transition_session(), proposal_id="P2", statement="先白模验证", rationale="reduce contamination", expected_effect="clean geometry")
        session = accept_ai_proposal(session, "P2", user_acceptance_provenance=user("accept"))
        forged = copy.deepcopy(session)
        for field in ("candidate_directions", "confirmed_decisions"):
            for record in forged[field]:
                if record.get("decision_id") == "P2": record["statement"] = "接受后偷换方案"
        with self.assertRaises(MIDSDiscoveryError) as ctx: validate_session(forged)
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_accepted_ai_proposal_requires_live_candidate_copy(self):
        session = add_ai_proposal(transition_session(), proposal_id="P2", statement="先白模验证", rationale="reduce contamination", expected_effect="clean geometry")
        session = accept_ai_proposal(session, "P2", user_acceptance_provenance=user("accept"))
        forged = copy.deepcopy(session); forged["candidate_directions"] = []
        with self.assertRaises(MIDSDiscoveryError) as ctx: validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_DECISION_RELATION_MISSING")

    def test_accepted_ai_proposal_requires_live_confirmed_copy(self):
        session = add_ai_proposal(transition_session(), proposal_id="P2", statement="先白模验证", rationale="reduce contamination", expected_effect="clean geometry")
        session = accept_ai_proposal(session, "P2", user_acceptance_provenance=user("accept"))
        forged = copy.deepcopy(session)
        forged["confirmed_decisions"] = [x for x in forged["confirmed_decisions"] if x.get("decision_id") != "P2"]
        with self.assertRaises(MIDSDiscoveryError) as ctx: validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_DECISION_RELATION_MISSING")

    def test_accepted_ai_copies_must_be_exactly_synchronized(self):
        session = add_ai_proposal(transition_session(), proposal_id="P2", statement="先白模验证", rationale="reduce contamination", expected_effect="clean geometry")
        session = accept_ai_proposal(session, "P2", user_acceptance_provenance=user("accept"))
        forged = copy.deepcopy(session)
        next(x for x in forged["confirmed_decisions"] if x.get("decision_id") == "P2")["expected_effect"] = "tampered"
        with self.assertRaises(MIDSDiscoveryError) as ctx: validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_DECISION_COPY_MISMATCH")

    def test_tacit_confirmation_receipt_is_bound_to_exact_candidate_statement(self):
        session = add_tacit_candidate(
            main_session(), decision_id="T1", statement="用户可能偏好让动作笑点服从角色能力感",
            confidence="MEDIUM", provenance=[{"source": "PROJECT_FEEDBACK_INFERENCE", "ref": "case-a"}],
        )
        forged = copy.deepcopy(session); forged["inferred_preferences"][0]["statement"] = "用户其实偏好笨拙小丑"
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            confirm_tacit_candidate(forged, "T1", user_confirmation_provenance=user("confirm-t1"))
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_confirmed_tacit_candidate_requires_both_synchronized_copies(self):
        session = add_tacit_candidate(
            main_session(), decision_id="T1", statement="用户可能偏好让动作笑点服从角色能力感",
            confidence="MEDIUM", provenance=[{"source": "PROJECT_FEEDBACK_INFERENCE", "ref": "case-a"}],
        )
        session = confirm_tacit_candidate(session, "T1", user_confirmation_provenance=user("confirm-t1"))
        forged = copy.deepcopy(session); forged["inferred_preferences"] = []
        with self.assertRaises(MIDSDiscoveryError) as ctx: validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_DECISION_RELATION_MISSING")

    def test_rejection_reason_is_bound_to_user_receipt(self):
        session = add_ai_proposal(transition_session(), proposal_id="P1", statement="用夸张动作", rationale="candidate", expected_effect="more comedy")
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            reject_alternative(session, "P1", user_rejection_provenance=user("reject"), reason="AI伪造的另一个理由")
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_rejection_reason_cannot_be_rewritten_after_transition(self):
        session = add_ai_proposal(transition_session(), proposal_id="P1", statement="用夸张动作", rationale="candidate", expected_effect="more comedy")
        session = reject_alternative(session, "P1", user_rejection_provenance=user("reject"), reason="破坏能力感")
        forged = copy.deepcopy(session); forged["rejected_alternatives"][0]["reason"] = "事后篡改理由"
        with self.assertRaises(MIDSDiscoveryError) as ctx: validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_REJECTION_REASON_MISMATCH")

    def test_revocation_reason_is_bound_and_cannot_be_rewritten(self):
        session = add_ai_proposal(transition_session(), proposal_id="P2", statement="先白模验证", rationale="reduce contamination", expected_effect="clean geometry")
        session = accept_ai_proposal(session, "P2", user_acceptance_provenance=user("accept"))
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            revoke_accepted_ai_proposal(session, "P2", user_revocation_provenance=user("revoke"), reason="AI虚构撤销理由")
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")
        session = revoke_accepted_ai_proposal(session, "P2", user_revocation_provenance=user("revoke"), reason="用户明确撤销")
        forged = copy.deepcopy(session); forged["rejected_alternatives"][0]["reason"] = "事后改写"
        with self.assertRaises(MIDSDiscoveryError) as ctx2: validate_session(forged)
        self.assertEqual(ctx2.exception.code, "MIDS_REJECTION_REASON_MISMATCH")


if __name__ == "__main__":
    unittest.main()
