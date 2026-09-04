from pathlib import Path
import unittest

from learning_retriever import feature_compiler as fc


REPO_ROOT = Path(__file__).resolve().parents[3]


class FeatureCompilerV5InternalParityTests(unittest.TestCase):
    def test_next_subject_facing_survives_both_core_and_facade_layers(self):
        text = "群众下跪且凯姆面向圣女。"
        identity_map, terms = fc._canonical_actor_authority()
        core_text, normalization = fc._core_input_projection(
            text,
            canonical_identity_map=identity_map,
            canonical_terms=terms,
        )
        parsed = fc._legacy._core.compile_director_features(
            core_text,
            strict=False,
            known_actor_terms=terms,
        )
        support = fc._scan_actor_event_support(
            text,
            canonical_terms=terms,
            canonical_identity_map=identity_map,
        )
        self.assertIn(
            "facing_to_target",
            parsed.relation_type,
            msg=f"core_text={core_text!r} normalization={normalization!r} parsed={parsed.as_dict()!r}",
        )
        self.assertTrue(
            support["facing_target"],
            msg=f"support={support!r} core_text={core_text!r}",
        )

    def test_shared_prefix_positive_is_emitted_by_core_then_kept_by_facade(self):
        text = "菲奥奈面向高台上的圣女。"
        identity_map, terms = fc._canonical_actor_authority()
        core_text, normalization = fc._core_input_projection(
            text,
            canonical_identity_map=identity_map,
            canonical_terms=terms,
        )
        parsed = fc._legacy._core.compile_director_features(
            core_text,
            strict=False,
            known_actor_terms=terms,
        )
        support = fc._scan_actor_event_support(
            text,
            canonical_terms=terms,
            canonical_identity_map=identity_map,
        )
        self.assertTrue(normalization["shared_target_prefix_normalized"])
        self.assertEqual(core_text, "菲奥奈面向圣女。")
        self.assertIn("facing_to_target", parsed.relation_type)
        self.assertTrue(support["facing_target"])


if __name__ == "__main__":
    unittest.main()
