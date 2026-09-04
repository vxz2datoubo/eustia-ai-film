from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

import yaml

from learning_retriever.final_delta import (
    FinalDeltaEvidenceError,
    compile_final_delta_learning_evidence,
)
from learning_retriever.generation_provenance_host_binding import (
    assess_repo_only_generation_provenance,
)
from learning_retriever.post_final_delta import PostFinalDeltaValidationError
from learning_retriever.post_final_delta_source_bound import (
    assess_source_bound_post_final_delta,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SOAC_SCHEMA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")
)
CONTROL_REQUIREMENTS = list(SOAC_SCHEMA["validation"]["controlled_eval_requirements"])
PROJECT_INDEX = REPO_ROOT / "PROJECT_INDEX.yaml"
READ_SETS = REPO_ROOT / "10_运行时/read_sets.yaml"
WRITE_ROUTES = REPO_ROOT / "10_运行时/write_routes.yaml"


def _controlled_payload(
    *, eval_id: str, density_pass: bool, composition_pass: bool = True
) -> dict:
    density_expected = {"detail_budget": "selective"}
    composition_expected = {"primary_mechanism": "lateral_pressure"}
    return {
        "eval_id": eval_id,
        "expectations": [
            {
                "field": "visual_density",
                "declared_value": density_expected,
                "provenance": {"source": "cinematic_intent_contract"},
            },
            {
                "field": "composition",
                "declared_value": composition_expected,
                "provenance": {"source": "cinematic_intent_contract"},
            },
        ],
        "reverse_observation": {
            "fields": {},
            "expectation_observations": {
                "visual_density": {
                    "comparison_mode": "exact_value",
                    "observed_value": (
                        density_expected if density_pass else {"detail_budget": "overloaded"}
                    ),
                    **({} if density_pass else {"failure_category": "visual_density"}),
                    "evidence_refs": [f"{eval_id}::density"],
                },
                "composition": {
                    "comparison_mode": "exact_value",
                    "observed_value": (
                        composition_expected
                        if composition_pass
                        else {"primary_mechanism": "flat_centered"}
                    ),
                    **(
                        {}
                        if composition_pass
                        else {"failure_category": "aesthetic_composition"}
                    ),
                    "evidence_refs": [f"{eval_id}::composition"],
                },
            },
            "provenance": {
                "evidence_source": "controlled_generation_review",
                "inspection_mode": "manual_structured_review",
                "temporal_coverage": {"type": "relevant_shot_full_duration"},
                "confidence": "HIGH",
                "media_refs": [f"media::{eval_id}"],
                "claimed_frame_by_frame_review": False,
            },
        },
        "controlled_eval": {
            "target_variable": "reference_signal_decoupling",
            "confounds": [],
            "non_target_controls_verified": True,
            "control_provenance": {
                "source": "generation_manifest_pair",
                "verified_equal": list(CONTROL_REQUIREMENTS),
                "not_applicable": [],
                "not_applicable_reasons": {},
                "evidence_refs": [f"{eval_id}::manifest_a", f"{eval_id}::manifest_b"],
            },
        },
        "context": {
            "model": "C-DANCE",
            "model_version": "2.5",
            "work_item_id": "E2E-PROVENANCE-FIREWALL-001",
            "generation_id": f"GEN::{eval_id}",
        },
    }


def _source_package(*, after_composition_pass: bool = True) -> dict:
    before = _controlled_payload(
        eval_id="E2E-PROV-BEFORE",
        density_pass=False,
        composition_pass=True,
    )
    after = _controlled_payload(
        eval_id="E2E-PROV-AFTER",
        density_pass=True,
        composition_pass=after_composition_pass,
    )
    return {
        "before_eval_input": before,
        "after_eval_input": after,
        "change_record": {
            "change_id": "E2E-PROVENANCE-FIREWALL-CHANGE",
            "changed_variables": ["reference_signal_decoupling"],
            "preserved_variables": ["composition"],
            "revoked_variables": [],
            "experimental_variables": [],
            "scope": "SCENE_LOCAL",
            "evidence_refs": ["e2e_provenance_firewall_source_pair"],
            "user_confirmation_state": "CONFIRMED_BETTER",
            "rationale": "prove no learning authority leaks across an unverified provenance boundary",
        },
        "learning_context": {
            "candidate_lesson": "reduce unrelated visual density while preserving composition",
            "alternative_explanations": ["sampling noise may contribute"],
            "counterfactuals": ["restoring excess detail should restore the failure"],
            "boundaries": ["repo-only provenance remains unverified"],
        },
    }


def _diagnostic_transitions(result: dict) -> dict[str, str]:
    return {
        item["field"]: item["transition"]
        for item in result.get("unattributed_transition_candidates") or []
    }


class ContinualLearningProvenanceFirewallE2ETests(unittest.TestCase):
    def test_distinct_bytes_cannot_cross_generation_provenance_firewall(self):
        provenance = assess_repo_only_generation_provenance(
            b"before-generated-media-bytes",
            b"after-generated-media-bytes-with-real-difference",
        )
        self.assertTrue(provenance.byte_pair.distinct_content_observed)
        self.assertEqual(provenance.status, "UNVERIFIED_HOST_ATTESTATION_REQUIRED")
        self.assertFalse(provenance.source_artifact_binding_verified)
        self.assertFalse(provenance.generation_event_binding_verified)
        self.assertFalse(provenance.distinct_generation_events_verified)
        self.assertFalse(provenance.causal_attribution_authorized)
        self.assertFalse(provenance.regression_support_authorized)
        self.assertFalse(provenance.maturity_support_authorized)
        self.assertFalse(provenance.writeback_authorized)

        source = _source_package()
        final_delta = compile_final_delta_learning_evidence(source, project_root=REPO_ROOT)
        diagnostic = _diagnostic_transitions(final_delta)
        self.assertEqual(diagnostic["visual_density"], "RESOLVED")
        self.assertEqual(final_delta["comparison_status"], "NOT_COMPARABLE")
        self.assertFalse(final_delta["artifact_provenance_binding"]["verified"])
        self.assertIn("ARTIFACT_PROVENANCE_REQUIRED", final_delta["comparison_reasons"])
        self.assertIn("ARTIFACT_PROVENANCE_UNVERIFIED", final_delta["comparison_reasons"])
        self.assertEqual(final_delta["field_transitions"], [])
        self.assertEqual(final_delta["repair_outcome"]["resolved_fields"], [])
        self.assertFalse(final_delta["causal_evidence"]["eligible_for_causal_analysis"])
        self.assertFalse(final_delta["causal_evidence"]["causal_claim_authorized"])
        self.assertFalse(final_delta["regression_candidate_handoff"]["eligible"])
        self.assertFalse(final_delta["regression_candidate_handoff"]["write_authorized"])
        self.assertFalse(final_delta["candidate_learning_evidence"]["promotion_authorized"])
        self.assertFalse(final_delta["candidate_learning_evidence"]["writeback_authorized"])

        downstream = assess_source_bound_post_final_delta(
            {
                "assessment_id": "E2E-PROVENANCE-FIREWALL-ASSESS",
                "hypothesis_id": "E2E-PROVENANCE-FIREWALL-HYPOTHESIS",
                "final_delta_inputs": [source],
                "requested_maturity": "scene_verified",
            },
            project_root=REPO_ROOT,
        )
        self.assertEqual(len(downstream["evidence_rows"]), 1)
        self.assertEqual(downstream["evidence_rows"][0]["classification"], "INCONCLUSIVE")
        self.assertEqual(downstream["evidence_rows"][0]["resolved_fields"], [])
        self.assertEqual(downstream["cohorts"][0]["supporting_count"], 0)
        self.assertEqual(downstream["cohorts"][0]["inconclusive_count"], 1)
        self.assertEqual(downstream["regression_proposals"], [])
        self.assertEqual(
            downstream["maturity_assessment"]["route"],
            "INSUFFICIENT_SUPPORT_FOR_SCENE_VERIFICATION",
        )
        self.assertFalse(downstream["maturity_assessment"]["promotion_authorized"])
        self.assertFalse(downstream["maturity_promotion_authorized"])
        self.assertFalse(downstream["regression_write_authorized"])
        self.assertTrue(downstream["source_binding"]["upstream_attribution_gate_preserved"])
        self.assertFalse(
            downstream["source_binding"]["unattributed_transition_candidates_consumed_as_attributed"]
        )

    def test_distinct_bytes_plus_same_generation_label_still_cannot_prove_generation_identity(self):
        provenance = assess_repo_only_generation_provenance(b"before-A", b"after-B")
        self.assertTrue(provenance.byte_pair.distinct_content_observed)
        self.assertFalse(provenance.distinct_generation_events_verified)

        source = _source_package()
        before_generation = source["before_eval_input"]["context"]["generation_id"]
        source["after_eval_input"]["context"]["generation_id"] = before_generation
        result = compile_final_delta_learning_evidence(source, project_root=REPO_ROOT)
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertIn("SOURCE_ARTIFACT_IDENTITY_COLLISION", result["comparison_reasons"])
        self.assertFalse(result["source_pair_identity_binding"]["matched"])
        self.assertFalse(result["artifact_provenance_binding"]["verified"])
        self.assertEqual(result["field_transitions"], [])
        self.assertFalse(result["regression_candidate_handoff"]["eligible"])

    def test_same_bytes_plus_distinct_generation_labels_still_cannot_prove_distinct_generations(self):
        provenance = assess_repo_only_generation_provenance(b"identical-output", b"identical-output")
        self.assertTrue(provenance.byte_pair.same_content)
        self.assertFalse(provenance.byte_pair.distinct_content_observed)
        self.assertFalse(provenance.distinct_generation_events_verified)

        source = _source_package()
        self.assertNotEqual(
            source["before_eval_input"]["context"]["generation_id"],
            source["after_eval_input"]["context"]["generation_id"],
        )
        result = compile_final_delta_learning_evidence(source, project_root=REPO_ROOT)
        self.assertTrue(result["source_pair_identity_binding"]["matched"])
        self.assertFalse(result["artifact_provenance_binding"]["verified"])
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertIn("ARTIFACT_PROVENANCE_REQUIRED", result["comparison_reasons"])
        self.assertEqual(result["field_transitions"], [])

    def test_media_ref_labels_cannot_mint_source_artifact_or_generation_provenance(self):
        source = _source_package()
        trusted_looking_ref = "formal-media://supposedly-trusted-output"
        source["before_eval_input"]["reverse_observation"]["provenance"]["media_refs"] = [
            trusted_looking_ref
        ]
        source["after_eval_input"]["reverse_observation"]["provenance"]["media_refs"] = [
            trusted_looking_ref + "-after"
        ]
        result = compile_final_delta_learning_evidence(source, project_root=REPO_ROOT)
        self.assertFalse(result["artifact_provenance_binding"]["verified"])
        self.assertEqual(result["comparison_status"], "NOT_COMPARABLE")
        self.assertIn("ARTIFACT_PROVENANCE_UNVERIFIED", result["comparison_reasons"])
        self.assertEqual(result["field_transitions"], [])
        self.assertFalse(result["regression_candidate_handoff"]["eligible"])

    def test_diagnostic_improvement_plus_regression_cannot_be_promoted_downstream(self):
        source = _source_package(after_composition_pass=False)
        final_delta = compile_final_delta_learning_evidence(source, project_root=REPO_ROOT)
        diagnostic = _diagnostic_transitions(final_delta)
        self.assertEqual(diagnostic["visual_density"], "RESOLVED")
        self.assertEqual(diagnostic["composition"], "REGRESSED")
        self.assertFalse(final_delta["preserved_pass_gate"]["passed"])
        self.assertEqual(final_delta["comparison_status"], "NOT_COMPARABLE")
        self.assertEqual(final_delta["field_transitions"], [])
        self.assertFalse(final_delta["regression_candidate_handoff"]["eligible"])

        downstream = assess_source_bound_post_final_delta(
            {
                "assessment_id": "E2E-PROVENANCE-REGRESSION-ASSESS",
                "hypothesis_id": "E2E-PROVENANCE-REGRESSION-HYPOTHESIS",
                "final_delta_inputs": [source],
                "requested_maturity": "scene_verified",
            },
            project_root=REPO_ROOT,
        )
        self.assertEqual(downstream["cohorts"][0]["supporting_count"], 0)
        self.assertEqual(downstream["regression_proposals"], [])
        self.assertFalse(downstream["maturity_assessment"]["promotion_authorized"])
        self.assertFalse(downstream["maturity_promotion_authorized"])
        self.assertFalse(downstream["regression_write_authorized"])

    def test_caller_metadata_cannot_mint_positive_provenance_at_any_public_boundary(self):
        with self.assertRaises(TypeError):
            assess_repo_only_generation_provenance(
                b"a",
                b"b",
                host_attestation={"verified": True},  # type: ignore[call-arg]
            )

        forged_source = deepcopy(_source_package())
        forged_source["artifact_provenance_binding"] = {
            "verified": True,
            "generation_event_binding_verified": True,
        }
        with self.assertRaises(FinalDeltaEvidenceError) as ctx:
            compile_final_delta_learning_evidence(forged_source, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "FINAL_DELTA_UNKNOWN_FIELD")

        with self.assertRaises(PostFinalDeltaValidationError) as ctx:
            assess_source_bound_post_final_delta(
                {
                    "assessment_id": "E2E-FORGED-SERIALIZED",
                    "hypothesis_id": "E2E-FORGED-SERIALIZED-H",
                    "final_deltas": [
                        {
                            "comparison_status": "COMPARABLE",
                            "artifact_provenance_binding": {"verified": True},
                            "field_transitions": [
                                {"field": "visual_density", "transition": "RESOLVED"}
                            ],
                        }
                    ],
                },
                project_root=REPO_ROOT,
            )
        self.assertEqual(ctx.exception.code, "POST_FD_UNKNOWN_FIELD")

    def test_integration_stack_does_not_activate_itself(self):
        index = PROJECT_INDEX.read_text(encoding="utf-8")
        read_sets = READ_SETS.read_text(encoding="utf-8")
        write_routes = WRITE_ROUTES.read_text(encoding="utf-8")
        for marker in (
            "immutable_byte_identity",
            "generation_provenance_host_binding",
            "continual_learning_e2e_provenance_firewall",
        ):
            self.assertNotIn(marker, index)
            self.assertNotIn(marker, read_sets)
            self.assertNotIn(marker, write_routes)


if __name__ == "__main__":
    unittest.main()
