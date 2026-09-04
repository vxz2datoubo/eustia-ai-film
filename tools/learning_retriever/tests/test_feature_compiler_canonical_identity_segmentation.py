from pathlib import Path
import unittest

import yaml

from learning_retriever.entity_semantics import load_canonical_character_identity_map
from learning_retriever.feature_compiler import compile_director_features, compile_retrieval_task


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTE_DATA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/director_route_index.yaml").read_text(encoding="utf-8")
)
TARGET_ROUTE = "TARGET_ORIENTED_SPATIAL_BINDING"


class CanonicalActorIdentitySegmentationTests(unittest.TestCase):
    def _relations(self, text: str) -> set[str]:
        features = compile_director_features(text, strict=False)
        return set(features.relation_type)

    def _task(self, text: str) -> dict:
        return compile_retrieval_task(text, route_data=ROUTE_DATA, strict=False)

    def test_next_explicit_actor_is_not_previous_kneel_target(self):
        relations = self._relations("群众下跪且凯姆面向圣女。")
        self.assertNotIn("kneeling_to_target", relations)

    def test_aliases_share_canonical_character_row_identity(self):
        identity = load_canonical_character_identity_map(REPO_ROOT)
        self.assertEqual(identity["爱丽丝"], identity["艾莉丝"])
        self.assertEqual(identity["格兰"], identity["副队长"])

        for text in (
            "艾莉丝下跪且爱丽丝面向圣女。",
            "副队长下跪且格兰面向圣女。",
        ):
            with self.subTest(text=text):
                task = self._task(text)
                self.assertIn("kneeling_to_target", task["relation_type"])
                self.assertIn(TARGET_ROUTE, task["hard_routes"])

    def test_unknown_explicit_subject_clears_stale_actor_agency(self):
        relations = self._relations("菲奥奈看向远处，乌云掠过，随后面向圣女。")
        self.assertNotIn("facing_to_target", relations)

    def test_unknown_explicit_subject_inside_coordinated_clause_clears_agency(self):
        relations = self._relations("菲奥奈看向圣女且乌云面向教会。")
        self.assertIn("gaze_to_target", relations)
        self.assertNotIn("facing_to_target", relations)

    def test_possessive_actor_body_leader_keeps_facing_relation(self):
        task = self._task("菲奥奈的身体面向圣女。")
        self.assertIn("facing_to_target", task["relation_type"])
        self.assertIn(TARGET_ROUTE, task["hard_routes"])

    def test_canonical_names_with_punctuation_or_digits_are_valid_subjects(self):
        for text in (
            "吉克弗里德·古拉德面向圣女。",
            "第29代圣女伊莲面向教会。",
        ):
            with self.subTest(text=text):
                task = self._task(text)
                self.assertIn("facing_to_target", task["relation_type"])
                self.assertIn(TARGET_ROUTE, task["hard_routes"])

    def test_pronoun_is_not_guessed_as_prior_named_character(self):
        relations = self._relations("艾莉丝看向圣女。她跪下。")
        self.assertIn("gaze_to_target", relations)
        self.assertNotIn("kneeling_to_target", relations)

    def test_target_before_new_subject_remains_owned_by_first_event(self):
        relations = self._relations("群众看向圣女并凯姆面向教会。")
        self.assertIn("gaze_to_target", relations)

    def test_receipt_exposes_canonical_row_and_local_segmentation_boundary(self):
        task = self._task("菲奥奈面向圣女。")
        receipt = task["feature_compiler_receipt"]
        self.assertEqual(receipt["actor_identity_authority"], "canonical_character_row_v1")
        self.assertEqual(receipt["event_target_segmentation"], "predicate_local_subject_boundary_v1")
        self.assertGreater(receipt["canonical_character_row_count"], 0)
        self.assertFalse(receipt["caller_actor_terms_supported"])


if __name__ == "__main__":
    unittest.main()
