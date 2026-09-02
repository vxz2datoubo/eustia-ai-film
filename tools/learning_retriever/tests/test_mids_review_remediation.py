import copy
import unittest

from learning_retriever.mids_discovery import (
    MIDSDiscoveryError,
    accept_ai_proposal,
    add_ai_proposal,
    add_tacit_candidate,
    add_unknown,
    add_user_confirmed_decision,
    confirm_tacit_candidate,
    new_session,
    set_material_director_intent,
    validate_handoff_ready,
    validate_session,
)


def user(ref):
    return [{"source": "USER", "ref": ref}]


def transition_session():
    session = new_session(
        "继续这个镜头，但还有几个关键问题没想清楚",
        provenance=user("raw"),
        work_item_binding={"mode": "NEW_UNBOUND"},
    )
    session = set_material_director_intent(
        session,
        "凯姆保持熟练，笑点来自意外。",
        provenance=user("intent"),
    )
    session = add_user_confirmed_decision(
        session,
        decision_id="D1",
        statement="不能拍成笨拙小丑。",
        provenance=user("d1"),
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
        provenance=user("turn-user-1"),
        work_item_binding={"mode": "NEW_UNBOUND"},
    )


class MIDSReviewRemediationTests(unittest.TestCase):
    def test_lowercase_high_unknown_still_blocks_handoff(self):
        session = transition_session()
        session["unknowns"].append({
            "unknown_id": "U-LOWER-HIGH",
            "question": "这个关键选择还没解决吗？",
            "epistemic_class": "USER_TACIT_CANDIDATE",
            "materiality": "high",
            "status": "OPEN",
            "blocks_handoff": False,
        })
        receipt = validate_handoff_ready(session)
        self.assertFalse(receipt["ready"])
        self.assertIn("MATERIAL_UNKNOWN_UNRESOLVED", receipt["blockers"])

    def test_lowercase_material_unknown_still_blocks_handoff(self):
        session = transition_session()
        session["unknowns"].append({
            "unknown_id": "U-LOWER-MATERIAL",
            "question": "这个材料级未知还没解决吗？",
            "epistemic_class": "USER_TACIT_CANDIDATE",
            "materiality": "material",
            "status": "open",
            "blocks_handoff": False,
        })
        receipt = validate_handoff_ready(session)
        self.assertFalse(receipt["ready"])
        self.assertIn("MATERIAL_UNKNOWN_UNRESOLVED", receipt["blockers"])

    def test_add_unknown_rejects_duplicate_identifier(self):
        session = add_unknown(
            transition_session(),
            unknown_id="U-DUP",
            question="第一次",
            epistemic_class="USER_TACIT_CANDIDATE",
            materiality="MEDIUM",
        )
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            add_unknown(
                session,
                unknown_id="U-DUP",
                question="第二次",
                epistemic_class="USER_TACIT_CANDIDATE",
                materiality="HIGH",
            )
        self.assertEqual(ctx.exception.code, "MIDS_UNKNOWN_ID_DUPLICATE")

    def test_mutated_session_with_duplicate_unknown_ids_is_rejected(self):
        session = add_unknown(
            transition_session(),
            unknown_id="U-DUP-MUTATED",
            question="第一次",
            epistemic_class="USER_TACIT_CANDIDATE",
            materiality="MEDIUM",
        )
        forged = copy.deepcopy(session)
        duplicate = copy.deepcopy(forged["unknowns"][0])
        duplicate["question"] = "伪造的第二条"
        forged["unknowns"].append(duplicate)
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            validate_session(forged)
        self.assertEqual(ctx.exception.code, "MIDS_UNKNOWN_ID_DUPLICATE")

    def test_accept_receipt_cannot_authorize_rewritten_same_id_proposal(self):
        session = add_ai_proposal(
            transition_session(),
            proposal_id="P2",
            statement="先白模验证",
            rationale="reduce contamination",
            expected_effect="clean geometry",
        )
        forged = copy.deepcopy(session)
        forged["candidate_directions"][0]["statement"] = "直接改成完全不同的导演方案"
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            accept_ai_proposal(
                forged,
                "P2",
                user_acceptance_provenance=user("accept"),
            )
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_accepted_proposal_statement_cannot_be_rewritten_after_acceptance(self):
        session = add_ai_proposal(
            transition_session(),
            proposal_id="P2",
            statement="先白模验证",
            rationale="reduce contamination",
            expected_effect="clean geometry",
        )
        session = accept_ai_proposal(session, "P2", user_acceptance_provenance=user("accept"))
        forged = copy.deepcopy(session)
        for field in ("candidate_directions", "confirmed_decisions"):
            for record in forged[field]:
                if record.get("decision_id") == "P2":
                    record["statement"] = "接受后偷偷替换成另一个方案"
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            validate_session(forged)
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_tacit_confirmation_receipt_is_bound_to_exact_candidate_statement(self):
        session = add_tacit_candidate(
            main_session(),
            decision_id="T1",
            statement="用户可能偏好让动作笑点服从角色能力感",
            confidence="MEDIUM",
            provenance=[{"source": "PROJECT_FEEDBACK_INFERENCE", "ref": "case-a"}],
        )
        forged = copy.deepcopy(session)
        forged["inferred_preferences"][0]["statement"] = "用户其实偏好让角色变成笨拙小丑"
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            confirm_tacit_candidate(
                forged,
                "T1",
                user_confirmation_provenance=user("confirm-t1"),
            )
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")


if __name__ == "__main__":
    unittest.main()
