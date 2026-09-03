from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

import yaml

from learning_retriever.final_delta import compile_final_delta_learning_evidence
from learning_retriever.post_final_delta import PostFinalDeltaValidationError
from learning_retriever.post_final_delta_source_bound import assess_source_bound_post_final_delta


REPO_ROOT = Path(__file__).resolve().parents[3]
SOAC_SCHEMA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")
)
CONTROL_REQUIREMENTS = list(SOAC_SCHEMA["validation"]["controlled_eval_requirements"])


def _controlled_payload(*, eval_id: str, density_pass: bool) -> dict:
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
                    "observed_value": density_expected if density_pass else {"detail_budget": "overloaded"},
                    **({} if density_pass else {"failure_category": "visual_density"}),
                    "evidence_refs": [f"{eval_id}::density"],
                },
                "composition": {
                    "comparison_mode": "exact_value",
                    "observed_value": composition_expected,
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
            "work_item_id": "PFD-ARTIFACT-GATE-WORK-ITEM",
            "generation_id": f"GEN::{eval_id}",
        },
    }


def _source_package() -> dict:
    before = _controlled_payload(eval_id="PFD-ARTIFACT-BEFORE", density_pass=False)
    after = _controlled_payload(eval_id="PFD-ARTIFACT-AFTER", density_pass=True)
    return {
        "before_eval_input": before,
        "after_eval_input": after,
        "change_record": {
            "change_id": "PFD-ARTIFACT-GATE-CHANGE",
            "changed_variables": ["reference_signal_decoupling"],
            "preserved_variables": ["composition"],
            "revoked_variables": [],
            "experimental_variables": [],
            "scope": "SCENE_LOCAL",
            "evidence_refs": ["pfd_artifact_gate_source_pair"],
            "user_confirmation_state": "CONFIRMED_BETTER",
            "rationale": "prove downstream cannot restore attribution while artifact provenance is unverified",
        },
        "learning_context": {
            "candidate_lesson": "reduce unrelated visual density while preserving composition",
            "alternative_explanations": ["sampling noise may contribute"],
            "counterfactuals": ["restoring excess detail should restore the failure"],
            "boundaries": ["single source-bound comparison only"],
        },
    }


class PostFinalDeltaArtifactGateTests(unittest.TestCase):
    def test_real_final_delta_diagnostic_resolved_stays_inconclusive_downstream(self):
        source = _source_package()
        upstream = compile_final_delta_learning_evidence(source, project_root=REPO_ROOT)
        diagnostic = {
            item["field"]: item["transition"]
            for item in upstream.get("unattributed_transition_candidates") or []
        }
        self.assertEqual(diagnostic["visual_density"], "RESOLVED")
        self.assertEqual(upstream["comparison_status"], "NOT_COMPARABLE")
        self.assertFalse(upstream["artifact_provenance_binding"]["verified"])
        self.assertEqual(upstream["field_transitions"], [])
        self.assertFalse(upstream["regression_candidate_handoff"]["eligible"])

        result = assess_source_bound_post_final_delta(
            {
                "assessment_id": "PFD-ARTIFACT-GATE-ASSESS",
                "hypothesis_id": "PFD-ARTIFACT-GATE-HYPOTHESIS",
                "final_delta_inputs": [source],
                "requested_maturity": "scene_verified",
            },
            project_root=REPO_ROOT,
        )

        self.assertEqual(len(result["evidence_rows"]), 1)
        self.assertEqual(result["evidence_rows"][0]["classification"], "INCONCLUSIVE")
        self.assertEqual(result["evidence_rows"][0]["resolved_fields"], [])
        self.assertEqual(result["cohorts"][0]["supporting_count"], 0)
        self.assertEqual(result["cohorts"][0]["inconclusive_count"], 1)
        self.assertEqual(result["regression_proposals"], [])
        self.assertEqual(
            result["maturity_assessment"]["route"],
            "INSUFFICIENT_SUPPORT_FOR_SCENE_VERIFICATION",
        )
        self.assertFalse(result["maturity_assessment"]["promotion_authorized"])
        self.assertFalse(result["maturity_promotion_authorized"])
        self.assertFalse(result["regression_write_authorized"])
        self.assertEqual(result["source_binding"]["mode"], "canonical_final_delta_reexecution")
        self.assertTrue(result["source_binding"]["upstream_attribution_gate_preserved"])
        self.assertFalse(
            result["source_binding"]["unattributed_transition_candidates_consumed_as_attributed"]
        )

    def test_source_wrapper_rejects_not_comparable_with_attributed_transitions(self):
        forged = {
            "comparison_status": "NOT_COMPARABLE",
            "field_transitions": [{"field": "visual_density", "transition": "RESOLVED"}],
            "repair_outcome": {
                "resolved_fields": ["visual_density"],
                "persistent_failure_fields": [],
                "regressed_fields": [],
            },
            "regression_candidate_handoff": {"eligible": False},
        }
        with patch(
            "learning_retriever.post_final_delta_source_bound.compile_final_delta_learning_evidence",
            return_value=forged,
        ), patch(
            "learning_retriever.post_final_delta_source_bound._assess_internal_projection"
        ) as projection:
            with self.assertRaises(PostFinalDeltaValidationError) as ctx:
                assess_source_bound_post_final_delta(
                    {
                        "assessment_id": "A",
                        "hypothesis_id": "H",
                        "final_delta_inputs": [{"source": "synthetic"}],
                    },
                    project_root=REPO_ROOT,
                )
        self.assertEqual(ctx.exception.code, "POST_FD_INVALID_FINAL_DELTA")
        projection.assert_not_called()

    def test_source_wrapper_rejects_not_comparable_regression_eligibility(self):
        forged = {
            "comparison_status": "NOT_COMPARABLE",
            "field_transitions": [],
            "repair_outcome": {
                "resolved_fields": [],
                "persistent_failure_fields": [],
                "regressed_fields": [],
            },
            "regression_candidate_handoff": {"eligible": True},
            "unattributed_transition_candidates": [
                {"field": "visual_density", "transition": "RESOLVED"}
            ],
        }
        with patch(
            "learning_retriever.post_final_delta_source_bound.compile_final_delta_learning_evidence",
            return_value=forged,
        ), patch(
            "learning_retriever.post_final_delta_source_bound._assess_internal_projection"
        ) as projection:
            with self.assertRaises(PostFinalDeltaValidationError) as ctx:
                assess_source_bound_post_final_delta(
                    {
                        "assessment_id": "A",
                        "hypothesis_id": "H",
                        "final_delta_inputs": [{"source": "synthetic"}],
                    },
                    project_root=REPO_ROOT,
                )
        self.assertEqual(ctx.exception.code, "POST_FD_AUTHORITY_VIOLATION")
        projection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
