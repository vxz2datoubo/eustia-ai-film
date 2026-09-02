import copy
import unittest

from learning_retriever.mids_discovery import (
    MIDSDiscoveryError,
    accept_ai_proposal,
    add_ai_proposal,
    add_user_confirmed_decision,
    new_session,
    set_material_director_intent,
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
    return session


def guard_session():
    session = new_session(
        "群众出现强烈宗教反应",
        provenance=user("raw"),
        work_item_binding={"mode": "NEW_UNBOUND"},
    )
    session = set_material_director_intent(
        session,
        "群众看到圣女后转身面向圣女并跪拜。",
        provenance=user("intent"),
    )
    session = add_user_confirmed_decision(
        session,
        decision_id="D1",
        statement="群众跪拜的目标明确是圣女。",
        provenance=user("decision"),
    )
    return session


class MIDSUserEvidenceReceiptTests(unittest.TestCase):
    def test_user_label_with_unknown_ref_is_not_authority(self):
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            new_session(
                "继续这个镜头，但还有几个关键问题没想清楚",
                provenance=user("self-minted-user-ref"),
                work_item_binding={"mode": "NEW_UNBOUND"},
            )
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_RECEIPT_NOT_TRUSTED")

    def test_receipt_is_bound_to_exact_session_context(self):
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            new_session(
                "群众出现强烈宗教反应",
                provenance=user("turn-user-1"),
                work_item_binding={"mode": "NEW_UNBOUND"},
            )
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_receipt_is_bound_to_purpose(self):
        session = add_ai_proposal(
            transition_session(),
            proposal_id="P2",
            statement="先白模验证",
            rationale="reduce contamination",
            expected_effect="clean geometry",
        )
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            accept_ai_proposal(
                session,
                "P2",
                user_acceptance_provenance=user("revoke"),
            )
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_receipt_is_bound_to_subject(self):
        session = add_ai_proposal(
            transition_session(),
            proposal_id="P1",
            statement="用夸张动作",
            rationale="candidate",
            expected_effect="more comedy",
        )
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            accept_ai_proposal(
                session,
                "P1",
                user_acceptance_provenance=user("accept"),
            )
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_same_alias_cannot_cross_session_even_when_source_label_is_user(self):
        session = add_ai_proposal(
            guard_session(),
            proposal_id="P2",
            statement="先白模验证",
            rationale="candidate",
            expected_effect="clean geometry",
        )
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            accept_ai_proposal(
                session,
                "P2",
                user_acceptance_provenance=user("accept"),
            )
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_direct_session_mutation_cannot_swap_in_other_valid_receipt(self):
        session = guard_session()
        forged = copy.deepcopy(session)
        forged["confirmed_decisions"][0]["provenance"] = user("accept")
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            validate_session(forged)
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")

    def test_statement_binding_prevents_receipt_reuse_for_rewritten_user_decision(self):
        session = transition_session()
        forged = copy.deepcopy(session)
        forged["confirmed_decisions"][0]["statement"] = "其实拍成笨拙小丑也可以"
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            validate_session(forged)
        self.assertEqual(ctx.exception.code, "USER_EVIDENCE_BINDING_MISMATCH")


if __name__ == "__main__":
    unittest.main()
