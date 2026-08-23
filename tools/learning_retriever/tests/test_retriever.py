from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from learning_retriever import LearningRetriever, RetrievalGateError, validate_index


REPO_ROOT = Path(__file__).resolve().parents[3]


class LearningRetrieverIntegrationTests(unittest.TestCase):
    def test_index_references_and_embedding_policy_are_valid(self) -> None:
        errors = validate_index(REPO_ROOT)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_target_oriented_spatial_binding_hard_route_hits_mandatory_case(self) -> None:
        r = LearningRetriever(REPO_ROOT)
        task = {
            "task_id": "REG-TARGET-BINDING-POSITIVE",
            "hard_routes": ["TARGET_ORIENTED_SPATIAL_BINDING"],
            "dramatic_function": ["worship"],
            "failure_mechanism": ["gaze_target_spatial_binding_fail"],
            "relation_type": ["kneeling_to_target"],
            "spatial_action_features": ["target_world_position", "body_orientation", "camera_side", "action_end_orientation"],
            "scene_context": ["crowd", "ritual"],
            "model": {"family": "seedance", "version": "2.5", "aliases": ["C-DANCE 2.5"]},
        }
        result = r.retrieve(task)
        self.assertEqual(result["status"], "PASS")
        self.assertIn("CROWD-GAZE-BODY-CAMERA-BINDING-001", result["retrieval_receipt"]["selected_case_ids"])
        self.assertTrue(result["retrieval_receipt"]["mandatory_recall_satisfied"])

    def test_mechanism_outranks_surface_similarity(self) -> None:
        r = LearningRetriever(REPO_ROOT)
        task = {
            "task_id": "REG-MECHANISM-FIRST",
            "failure_mechanism": ["camera_side_target_conflict"],
            "relation_type": ["gaze_to_target"],
            "surface_similarity": ["圣女", "群众", "广场"],
            "model": {"family": "seedance", "version": "2.5"},
        }
        result = r.retrieve(task, top_k=3)
        self.assertEqual(result["retrieval_receipt"]["selected_case_ids"][0], "CROWD-GAZE-BODY-CAMERA-BINDING-001")

    def test_negative_example_prevents_false_positive(self) -> None:
        r = LearningRetriever(REPO_ROOT)
        task = {
            "task_id": "REG-FALSE-POSITIVE-NEGATIVE",
            "surface_similarity": ["仰头", "看向"],
            "spatial_action_features": ["abstract_upward_gaze", "no_locatable_target"],
            "negative_features": ["abstract_upward_gaze", "no_locatable_target"],
        }
        result = r.retrieve(task, top_k=5)
        self.assertNotIn("CROWD-GAZE-BODY-CAMERA-BINDING-001", result["retrieval_receipt"]["selected_case_ids"])
        excluded = {x["case_id"]: x["reason"] for x in result["retrieval_receipt"]["excluded_candidates"]}
        self.assertEqual(excluded.get("CROWD-GAZE-BODY-CAMERA-BINDING-001"), "negative_retrieval_example")

    def test_alias_and_relation_recover_false_negative(self) -> None:
        r = LearningRetriever(REPO_ROOT)
        task = {
            "task_id": "REG-FALSE-NEGATIVE-ALIAS",
            "aliases": ["朝目标下跪"],
            "relation_type": ["kneeling_to_target"],
            "spatial_action_features": ["action_end_orientation"],
        }
        result = r.retrieve(task, top_k=5)
        self.assertIn("CROWD-GAZE-BODY-CAMERA-BINDING-001", result["retrieval_receipt"]["selected_case_ids"])

    def test_model_version_mismatch_filters_exclusive_model_lesson(self) -> None:
        r = LearningRetriever(REPO_ROOT)
        task = {
            "task_id": "REG-MODEL-MISMATCH",
            "failure_mechanism": ["contact_binding_fail"],
            "surface_similarity": ["凯姆", "窗"],
            "model": {"family": "minimax_h3", "version": "1"},
        }
        result = r.retrieve(task, top_k=8)
        self.assertNotIn("CD25-KAIM-WINDOW-AB-20260815", result["retrieval_receipt"]["selected_case_ids"])
        excluded = {x["case_id"]: x["reason"] for x in result["retrieval_receipt"]["excluded_candidates"]}
        self.assertEqual(excluded.get("CD25-KAIM-WINDOW-AB-20260815"), "model_version_mismatch")

    def test_receipt_is_complete_and_preoutput_validatable(self) -> None:
        r = LearningRetriever(REPO_ROOT)
        result = r.retrieve({"task_id": "REG-RECEIPT", "dramatic_function": ["crowd_reaction"]})
        receipt = result["retrieval_receipt"]
        self.assertTrue(receipt["receipt_complete"])
        self.assertTrue(r.validate_receipt(receipt))

    def test_expand_only_selected_top_k_case_payloads(self) -> None:
        r = LearningRetriever(REPO_ROOT)
        result = r.retrieve(
            {
                "task_id": "REG-TOPK-EXPAND",
                "failure_mechanism": ["gaze_target_spatial_binding_fail"],
                "relation_type": ["gaze_to_target"],
            },
            top_k=1,
            expand=True,
        )
        self.assertEqual(len(result["expanded_cases"]), 1)
        self.assertIn("CROWD-GAZE-BODY-CAMERA-BINDING-001", result["expanded_cases"])

    def test_final_yaml_case_expansion_stops_before_top_level_learning_checkpoint(self) -> None:
        r = LearningRetriever(REPO_ROOT)
        expanded = r.expand_authority_ref(
            "08_系统学习/导演反馈学习案例.yaml#CROWD-GAZE-BODY-CAMERA-BINDING-001"
        )
        self.assertIsNotNone(expanded)
        payload = expanded["payload"]
        self.assertEqual(payload["case_id"], "CROWD-GAZE-BODY-CAMERA-BINDING-001")
        self.assertNotIn("learning_checkpoint", payload)
        self.assertIn("operational_candidate", payload)


class LearningRetrieverSyntheticGateTests(unittest.TestCase):
    def _retriever(self, mutate=None) -> LearningRetriever:
        index = yaml.safe_load((REPO_ROOT / "10_运行时/learning_recall_index.yaml").read_text(encoding="utf-8"))
        if mutate:
            mutate(index)
        routes = {
            "routes": [
                {
                    "id": "TARGET_ORIENTED_SPATIAL_BINDING",
                    "mandatory_reads": ["08_系统学习/导演反馈学习案例.yaml#CROWD-GAZE-BODY-CAMERA-BINDING-001"],
                }
            ]
        }
        return LearningRetriever(REPO_ROOT, index_data=index, route_data=routes)

    def test_expired_scene_local_experience_is_filtered(self) -> None:
        def mutate(index):
            e = next(x for x in index["entries"] if x["case_id"] == "MOTIVE-FIRST-CROWD-001")
            e["scope"] = {
                "classes": ["SCENE_LOCAL"],
                "scenes": ["OLD-SCENE"],
                "work_items": [],
                "expiration_condition": "scene_end",
            }

        r = self._retriever(mutate)
        result = r.retrieve(
            {
                "task_id": "REG-EXPIRED-SCENE",
                "dramatic_function": ["crowd_reaction"],
                "scope": {"scene": "NEW-SCENE"},
            },
            top_k=8,
        )
        self.assertNotIn("MOTIVE-FIRST-CROWD-001", result["retrieval_receipt"]["selected_case_ids"])
        excluded = {x["case_id"]: x["reason"] for x in result["retrieval_receipt"]["excluded_candidates"]}
        self.assertEqual(excluded.get("MOTIVE-FIRST-CROWD-001"), "expired_scene_local_scope")

    def test_unresolved_material_conflict_fails_closed(self) -> None:
        def mutate(index):
            e = next(x for x in index["entries"] if x["case_id"] == "MOTIVE-FIRST-CROWD-001")
            e["conflict_refs"] = [{"with": "SYNTHETIC-OPPOSITE", "type": "TRUE_CONTRADICTION", "material": True, "resolved": False}]

        r = self._retriever(mutate)
        with self.assertRaises(RetrievalGateError):
            r.retrieve({"task_id": "REG-CONFLICT", "dramatic_function": ["crowd_reaction"]})

    def test_missing_mandatory_recall_fails_closed(self) -> None:
        def mutate(index):
            index["entries"] = [e for e in index["entries"] if e["case_id"] != "CROWD-GAZE-BODY-CAMERA-BINDING-001"]

        r = self._retriever(mutate)
        with self.assertRaises(RetrievalGateError):
            r.retrieve({"task_id": "REG-MANDATORY-MISSING", "hard_routes": ["TARGET_ORIENTED_SPATIAL_BINDING"]})


if __name__ == "__main__":
    unittest.main()
