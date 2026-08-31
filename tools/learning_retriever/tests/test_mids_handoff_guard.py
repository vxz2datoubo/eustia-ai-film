import unittest

from learning_retriever.feature_compiler import compile_director_features
from learning_retriever.mids_discovery import (
    MIDSDiscoveryError,
    add_user_confirmed_decision,
    new_session,
    set_material_director_intent,
)
from learning_retriever.mids_handoff_guard import compile_guarded_spec_candidate


def user_prov(ref="u"):
    return [{"source": "USER", "ref": ref}]


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
        session["confirmed_decisions"][0]["provenance"] = [
            {"source": "AI", "ref": "self-attestation"}
        ]
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            compile_guarded_spec_candidate(session)
        self.assertEqual(ctx.exception.code, "MIDS_USER_EXPLICIT_PROVENANCE_MUST_BE_USER")

    def test_work_item_projection_cannot_carry_caller_authority_assertions(self):
        session = ready_session(
            {
                "mode": "TRUSTED_EXISTING",
                "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
                "trust_basis": "canonical_github_readback_verified_snapshot",
            }
        )
        session["work_item_binding"]["canonical_authority_verified"] = True
        with self.assertRaises(MIDSDiscoveryError) as ctx:
            compile_guarded_spec_candidate(session)
        self.assertEqual(ctx.exception.code, "MIDS_WORK_ITEM_AUTHORITY_ASSERTION_FORBIDDEN")

    def test_existing_work_item_is_downgraded_to_projection_and_requires_downstream_awi_gate(self):
        spec = compile_guarded_spec_candidate(
            ready_session(
                {
                    "mode": "TRUSTED_EXISTING",
                    "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
                    "trust_basis": "canonical_github_readback_verified_snapshot",
                }
            )
        )
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


if __name__ == "__main__":
    unittest.main()
