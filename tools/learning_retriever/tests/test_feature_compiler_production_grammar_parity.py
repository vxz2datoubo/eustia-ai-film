from pathlib import Path
import unittest

import yaml

from learning_retriever.feature_compiler import (
    FeatureCompilationError,
    compile_director_features,
    compile_retrieval_task,
)
from learning_retriever.predicate_semantics import (
    TARGET_DETERMINER_PREFIXES,
    TARGET_LOCATION_PREFIXES,
    TARGET_PREFIX_TOKENS,
    normalize_post_action_target_prefixes,
    target_starts_after_bounded_prefix,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTE_DATA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/director_route_index.yaml").read_text(encoding="utf-8")
)
TARGET_ROUTE = "TARGET_ORIENTED_SPATIAL_BINDING"


class FeatureCompilerProductionGrammarParityTests(unittest.TestCase):
    def _task(self, text: str) -> dict:
        return compile_retrieval_task(text, route_data=ROUTE_DATA, strict=False)

    def _relations(self, text: str) -> set[str]:
        try:
            return set(compile_director_features(text).relation_type)
        except FeatureCompilationError as exc:
            if str(exc) == "NO_RECOGNIZED_DIRECTOR_FEATURES":
                return set()
            raise

    def test_shared_target_grammar_contains_locations_determiners_and_classifiers(self):
        for token in (
            "高台上的", "远处的", "门口", "那位", "这个",
            "那扇", "这扇", "一扇", "那座", "这座", "一座",
        ):
            with self.subTest(token=token):
                self.assertIn(token, TARGET_PREFIX_TOKENS)
        self.assertIn("那扇", TARGET_DETERMINER_PREFIXES)
        self.assertIn("高台上的", TARGET_LOCATION_PREFIXES)

    def test_shared_grammar_normalizes_only_bounded_post_action_target_prefixes(self):
        normalized, changed = normalize_post_action_target_prefixes(
            "菲奥奈面向高台上的圣女。",
            action_terms=("面向",),
            target_terms=("圣女", "大门"),
        )
        self.assertTrue(changed)
        self.assertEqual(normalized, "菲奥奈面向圣女。")

        normalized, changed = normalize_post_action_target_prefixes(
            "菲奥奈面向那扇大门。",
            action_terms=("面向",),
            target_terms=("圣女", "大门"),
        )
        self.assertTrue(changed)
        self.assertEqual(normalized, "菲奥奈面向大门。")

        unchanged, changed = normalize_post_action_target_prefixes(
            "菲奥奈面向广告牌后的圣女。",
            action_terms=("面向",),
            target_terms=("圣女",),
        )
        self.assertFalse(changed)
        self.assertEqual(unchanged, "菲奥奈面向广告牌后的圣女。")
        self.assertFalse(
            target_starts_after_bounded_prefix("广告牌后的圣女", ("圣女",))
        )

    def test_location_and_classifier_target_phrases_preserve_facing_route(self):
        for text in (
            "菲奥奈面向高台上的圣女。",
            "菲奥奈面向远处的圣女。",
            "菲奥奈面向那扇大门。",
            "菲奥奈面向这扇大门。",
            "菲奥奈面向一扇大门。",
            "菲奥奈面向那座教会。",
        ):
            with self.subTest(text=text):
                task = self._task(text)
                self.assertIn("facing_to_target", task.get("relation_type") or [])
                self.assertIn(TARGET_ROUTE, task.get("hard_routes") or [])
                self.assertEqual(
                    task["feature_compiler_receipt"]["shared_target_grammar"],
                    "predicate_semantics_v1",
                )

    def test_target_prefix_grammar_does_not_rescue_non_actor_or_arbitrary_prefix(self):
        for text in (
            "雕像面向高台上的圣女。",
            "钟楼面向那扇大门。",
            "英格兰面向远处的圣女。",
            "广告牌面向这座教会。",
        ):
            with self.subTest(text=text):
                task = self._task(text)
                self.assertNotIn("facing_to_target", task.get("relation_type") or [])
                self.assertNotIn(TARGET_ROUTE, task.get("hard_routes") or [])

        task = self._task("菲奥奈面向广告牌后的圣女。")
        self.assertNotIn("facing_to_target", task.get("relation_type") or [])

    def test_possessive_gaze_observable_owner_preserves_valid_actor_target(self):
        for text in (
            "菲奥奈的目光看向圣女。",
            "菲奥奈的视线望向圣女。",
            "她的视线望向圣女。",
            "她的目光缓缓看向圣女。",
        ):
            with self.subTest(text=text):
                task = self._task(text)
                self.assertIn("gaze_to_target", task.get("relation_type") or [])
                self.assertIn(TARGET_ROUTE, task.get("hard_routes") or [])

    def test_possessive_gaze_owner_still_rejects_non_actor_and_suffix_collision(self):
        for text in (
            "雕像的视线望向圣女。",
            "钟楼的目光看向圣女。",
            "英格兰的目光看向圣女。",
            "吉他的视线望向舞台。",
        ):
            with self.subTest(text=text):
                task = self._task(text)
                self.assertNotIn("gaze_to_target", task.get("relation_type") or [])
                self.assertNotIn(TARGET_ROUTE, task.get("hard_routes") or [])

    def test_punctuated_or_digit_canonical_name_plus_modifier_survives_before_cjk_gate(self):
        for text in (
            "吉克弗里德·古拉德缓缓地面向圣女。",
            "吉克弗里德·古拉德缓缓面向圣女。",
            "第29代圣女伊莲缓缓面向教会。",
            "第29代圣女伊莲郑重地面向教会。",
        ):
            with self.subTest(text=text):
                task = self._task(text)
                self.assertIn("facing_to_target", task.get("relation_type") or [])
                self.assertIn(TARGET_ROUTE, task.get("hard_routes") or [])
                self.assertTrue(
                    task["feature_compiler_receipt"][
                        "canonical_actor_modifier_normalized_for_core"
                    ]
                )

    def test_canonical_modifier_fix_does_not_accept_structural_or_location_tail(self):
        for text in (
            "吉克弗里德·古拉德基地面向圣女。",
            "第29代圣女伊莲出生地面向教会。",
            "英格兰缓缓面向圣女。",
        ):
            with self.subTest(text=text):
                task = self._task(text)
                self.assertNotIn("facing_to_target", task.get("relation_type") or [])
                self.assertNotIn(TARGET_ROUTE, task.get("hard_routes") or [])

    def test_existing_cross_actor_and_next_subject_boundaries_remain_closed(self):
        relations = self._relations("群众下跪且凯姆面向圣女。")
        self.assertNotIn("kneeling_to_target", relations)
        self.assertIn("facing_to_target", relations)

        relations = self._relations("菲奥奈看向圣女。骑士跪下。凯姆面向圣女。")
        self.assertIn("gaze_to_target", relations)
        self.assertIn("facing_to_target", relations)
        self.assertNotIn("kneeling_to_target", relations)


if __name__ == "__main__":
    unittest.main()
