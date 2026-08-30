from pathlib import Path
import unittest

import yaml

from learning_retriever import DirectorLearningRuntime
from learning_retriever.feature_compiler import compile_director_features
from learning_retriever.route_resolver import resolve_hard_routes


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTES = yaml.safe_load((REPO_ROOT / "10_运行时/director_route_index.yaml").read_text(encoding="utf-8"))
TARGET_ROUTE = "TARGET_ORIENTED_SPATIAL_BINDING"


class BareChaoSpatialSafetyTests(unittest.TestCase):
    def _assert_no_target_spatial_route(self, description: str) -> None:
        features = compile_director_features(description, strict=False)
        self.assertNotIn("facing_to_target", features.relation_type)
        self.assertNotIn("kneeling_to_target", features.relation_type)
        self.assertNotIn("target_oriented_action", features.dramatic_function)
        task = {"task_id": "CHAO-SAFETY", **features.as_dict()}
        hard_routes = resolve_hard_routes(task, ROUTES, description=description)
        self.assertNotIn(TARGET_ROUTE, hard_routes)

    def test_dynasty_word_does_not_become_facing_action(self) -> None:
        self._assert_no_target_spatial_route("讲述王朝时期圣女的历史。")

    def test_dynasty_system_word_does_not_become_facing_action(self) -> None:
        self._assert_no_target_spatial_route("介绍这个朝代的教会制度。")

    def test_explicit_body_facing_still_compiles(self) -> None:
        features = compile_director_features("人物身体朝圣女，随后跪下。")
        self.assertIn("facing_to_target", features.relation_type)
        self.assertIn("kneeling_to_target", features.relation_type)
        self.assertIn("body_orientation", features.spatial_action_features)

    def test_preposed_chao_target_before_kneel_is_bounded_positive(self) -> None:
        description = "群众朝她跪下。"
        features = compile_director_features(description)
        self.assertNotIn("facing_to_target", features.relation_type)
        self.assertIn("kneeling_to_target", features.relation_type)
        self.assertIn("locatable_target", features.spatial_action_features)
        hard_routes = resolve_hard_routes(
            {"task_id": "CHAO-POSITIVE", **features.as_dict()},
            ROUTES,
            description=description,
        )
        self.assertIn(TARGET_ROUTE, hard_routes)

    def test_existing_metamorphic_phrase_still_hits_mandatory_target_route(self) -> None:
        description = "钟楼平台上圣女伊莲现身，群众先看向圣女，随后朝她跪下。"
        result = DirectorLearningRuntime(REPO_ROOT).retrieve(
            description,
            task_id="CHAO-METAMORPHIC-POSITIVE",
            top_k=5,
        )
        receipt = result["retrieval_receipt"]
        self.assertIn(TARGET_ROUTE, receipt["hard_routes"])
        self.assertIn("CROWD-GAZE-BODY-CAMERA-BINDING-001", receipt["mandatory_case_ids"])
        self.assertTrue(receipt["mandatory_recall_satisfied"])


if __name__ == "__main__":
    unittest.main()
