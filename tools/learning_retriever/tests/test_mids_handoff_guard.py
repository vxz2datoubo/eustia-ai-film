import copy
import unittest

from learning_retriever.feature_compiler import compile_director_features
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


def user_prov(ref="u"):
    return [{"source": "USER", "ref": ref}]


def evidence_basis(ref="eval-1"):
    return {
        "type": "RESEARCH_EVIDENCE",
        "provenance": [{"source": "EVIDENCE", "ref": ref}],
        "result_ref": ref,
    }


def user_basis(ref="user-decision-1"):
    return {
        "type": "USER_DECISION",
        "provenance": user_prov(ref),
        "result_ref": ref,
    }


def ready_session(binding=None):
    session = new_session(
        "群众出现强烈宗教反应",
        provenance=user_prov("raw"),
        work_item_binding=binding or {"mode": "NEW_UNBOUND"},
    )
    session = set_material_director_intent(
        session,
        "群众看到圣女后转身面向圣女并跪拜。",
        provenance=user_prov("intent"),
    )
    session = add_user_confirmed_decision(
        session,
        decision_id="D1",
        statement="群众跪拜的目标明确是圣女。",
        provenance=user_prov("decision"),
    )
    session["success_criteria"].append({"statement": "跪拜目标和身体朝向可读"})
    session["examples"].append({"kind": "POSITIVE", "statement": "群众看到圣女后面向她跪拜"})
    session["counterexamples"].append({"statement": "群众朝摄影机跪而圣女在侧后方"})
    session["downstream_dependencies"].append({"task_class": "DIRECTOR_FEATURE_COMPILATION"})
    return session


class MIDSHandoffGuardTests(unittest.TestCase):
    def test_ai_cannot_mint_user_explicit_confirmed_by_supplying_non_user_provenance(self):
        session = ready_session()
        session["confirmed_decisions"][0]["provenance"] = [{"source": "AI", "ref": "self-attestation"}]
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            compile_guarded_spec_candidate(session)
        self.assertEqual(ctx.exception.code, "MIDS_TRUSTED_USER_RECEIPT_REQUIRED")

    def test_work_item_projection_cannot_carry_caller_authority_assertions(self):
        session = ready_session({
            "mode": "TRUSTED_EXISTING",
            "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
            "trust_basis": "canonical_github_readback_verified_snapshot",
        })
        session["work_item_binding"]["canonical_authority_verified"] = True
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            compile_guarded_spec_candidate(session)
        self.assertEqual(ctx.exception.code, "MIDS_WORK_ITEM_AUTHORITY_ASSERTION_FORBIDDEN")

    def test_existing_work_item_is_downgraded_to_projection_and_requires_downstream_awi_gate(self):
        spec = compile_guarded_spec_candidate(ready_session({
            "mode": "TRUSTED_EXISTING",
            "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
            "trust_basis": "canonical_github_readback_verified_snapshot",
        }))
        binding = spec["work_item_binding"]
        self.assertEqual(binding["mode"], "EXISTING_WORK_ITEM_CONTEXT_PROJECTION")
        self.assertFalse(binding["authority_granted_by_mids"])
        self.assertTrue(binding["downstream_active_work_item_revalidation_required"])
        self.assertTrue(spec["authority_boundary"]["work_item_projection_is_not_authority"])
        self.assertTrue(spec["authority_boundary"]["downstream_must_use_existing_active_work_item_gate"])
        self.assertTrue(spec["authority_boundary"]["mids_receipt_cannot_replace_active_work_item_receipt"])
        self.assertFalse(spec["handoff_guard_receipt"]["canonical_authority_granted"])

    def test_new_unbound_target_never_claims_work_item_authority(self):
        spec = compile_guarded_spec_candidate(ready_session())
        binding = spec["work_item_binding"]
        self.assertEqual(binding["mode"], "NEW_UNBOUND_DISCOVERY_TARGET")
        self.assertIsNone(binding["work_item_id"])
        self.assertFalse(binding["authority_granted_by_mids"])
        self.assertFalse(binding["downstream_active_work_item_revalidation_required"])

    def test_guarded_handoff_still_enters_existing_feature_compiler(self):
        spec = compile_guarded_spec_candidate(ready_session())
        self.assertNotIn("feature_compiler_receipt", spec)
        self.assertNotIn("hard_routes", spec)
        features = compile_director_features(spec["director_intent_text"])
        self.assertTrue(features.recognized)

    def test_ai_source_cannot_forge_rejection(self):
        session = add_ai_proposal(
            ready_session(), proposal_id="P1", statement="换成喜剧夸张动作",
            rationale="候选", expected_effect="更明显",
        )
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            reject_alternative(
                session, "P1",
                user_rejection_provenance=[{"source": "AI", "ref": "self"}],
                reason="AI自己拒绝",
            )
        self.assertEqual(ctx.exception.code, "MIDS_TRUSTED_USER_RECEIPT_REQUIRED")

    def test_nonexistent_rejection_target_fails_closed(self):
        with self.assertRaises(MIDSDiscoveryError):
            reject_alternative(
                ready_session(), "D1",
                user_rejection_provenance=user_prov("reject-collision"),
                reason="试图用ID碰撞删掉用户决定",
            )

    def test_rejection_id_collision_never_deletes_user_confirmed_decision(self):
        session = ready_session()
        original = copy.deepcopy(session["confirmed_decisions"])
        with self.assertRaises(MIDSDiscoveryError):
            reject_alternative(
                session, "D1", user_rejection_provenance=user_prov("reject"), reason="collision"
            )
        self.assertEqual(session["confirmed_decisions"], original)

    def test_accepted_ai_proposal_requires_explicit_revocation_and_preserves_history(self):
        session = add_ai_proposal(
            ready_session(), proposal_id="P-REV", statement="先用白模",
            rationale="减少污染", expected_effect="几何更稳定",
        )
        session = accept_ai_proposal(session, "P-REV", user_acceptance_provenance=user_prov("accept"))
        with self.assertRaises(MIDSDiscoveryError):
            reject_alternative(session, "P-REV", user_rejection_provenance=user_prov("reject"), reason="改变主意")
        revoked = revoke_accepted_ai_proposal(
            session, "P-REV", user_revocation_provenance=user_prov("revoke"), reason="用户明确撤销"
        )
        self.assertFalse(any(x["decision_id"] == "P-REV" for x in revoked["confirmed_decisions"]))
        self.assertEqual(len(revoked["revoked_decisions"]), 1)
        self.assertEqual(revoked["revoked_decisions"][0]["decision_id"], "P-REV")
        self.assertEqual(revoked["revoked_decisions"][0]["status"], "REVOKED")
        self.assertEqual(revoked["revoked_decisions"][0]["user_revocation_provenance"][0]["source"], "USER")

    def test_direct_unknown_status_mutation_cannot_self_clear(self):
        session = add_unknown(
            ready_session(), unknown_id="U1", question="是否会污染纹理",
            epistemic_class="EXPERT_BLIND_ZONE", materiality="HIGH",
            next_information_action="controlled_AB", blocks_handoff=True,
        )
        session["unknowns"][0]["status"] = "RESOLVED"
        with self.assertRaises(MIDSDiscoveryError):
            validate_session(session)

    def test_arbitrary_string_resolution_ref_is_rejected(self):
        session = add_unknown(
            ready_session(), unknown_id="U1", question="是否会污染纹理",
            epistemic_class="EXPERT_BLIND_ZONE", materiality="HIGH",
            next_information_action="controlled_AB", blocks_handoff=True,
        )
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            resolve_unknown(session, "U1", resolution_ref="caller-says-resolved")
        self.assertEqual(ctx.exception.code, "MIDS_TYPED_RESOLUTION_BASIS_REQUIRED")

    def test_forged_resolved_contradiction_fails_closed(self):
        session = ready_session()
        session["contradictions"].append({
            "contradiction_id": "C1", "statement": "两个目标冲突",
            "materiality": "MATERIAL", "status": "RESOLVED",
        })
        with self.assertRaises(MIDSDiscoveryError):
            validate_handoff_ready(session)

    def test_user_resolution_path_can_clear_material_blockers(self):
        session = add_unknown(
            ready_session(), unknown_id="U-USER", question="用户是否接受更克制的动作",
            epistemic_class="USER_TACIT_CANDIDATE", materiality="HIGH",
            user_facing_choice="是否接受更克制", blocks_handoff=True,
        )
        session = resolve_unknown(session, "U-USER", resolution_basis=user_basis())
        session = add_contradiction(session, contradiction_id="C1", statement="两个用户目标冲突")
        session = resolve_contradiction(session, "C1", resolution_basis=user_basis("priority"))
        receipt = validate_handoff_ready(session)
        self.assertTrue(receipt["ready"])
        self.assertGreaterEqual(len(session["mids_transition_log"]), 2)

    def test_self_asserted_external_evidence_cannot_clear_material_blocker(self):
        session = add_unknown(
            ready_session(), unknown_id="U-EVIDENCE", question="模型是否污染参考纹理",
            epistemic_class="EXPERT_BLIND_ZONE", materiality="HIGH",
            next_information_action="controlled_AB", blocks_handoff=True,
        )
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            resolve_unknown(session, "U-EVIDENCE", resolution_basis=evidence_basis())
        self.assertEqual(ctx.exception.code, "MIDS_EXTERNAL_RESOLUTION_REQUIRES_AUTHORITY_ADAPTER")
        self.assertFalse(validate_handoff_ready(session)["ready"])

    def test_self_asserted_external_evidence_cannot_clear_contradiction(self):
        session = add_contradiction(ready_session(), contradiction_id="C-EVIDENCE", statement="两条资料冲突")
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            resolve_contradiction(session, "C-EVIDENCE", resolution_basis=evidence_basis("research-2"))
        self.assertEqual(ctx.exception.code, "MIDS_EXTERNAL_RESOLUTION_REQUIRES_AUTHORITY_ADAPTER")


if __name__ == "__main__":
    unittest.main()
