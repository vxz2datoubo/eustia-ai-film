import unittest
from unittest.mock import patch

from learning_retriever import runtime
from learning_retriever.active_work_item import ActiveWorkItemResolutionError


class RuntimeTransitiveProvenanceTests(unittest.TestCase):
    def _expect_substitution(self, name, replacement):
        obj = runtime.DirectorLearningRuntime.__new__(runtime.DirectorLearningRuntime)
        obj.project_root = None
        with patch.object(runtime, name, replacement):
            with self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                runtime.DirectorLearningRuntime.retrieve(obj, "继续当前工作项")
        self.assertEqual(ctx.exception.code, "WORK_ITEM_RUNTIME_PROVENANCE_SUBSTITUTED")

    def test_build_context_global_substitution_fails_before_receipt_consumption(self):
        self._expect_substitution(
            "build_work_item_context_packet",
            lambda *_args, **_kwargs: {"work_item_id": "FORGED", "constraints": {"locked": []}},
        )

    def test_resolver_global_substitution_fails_before_receipt_consumption(self):
        self._expect_substitution("resolve_work_item", lambda *_args, **_kwargs: None)

    def test_source_revalidation_global_substitution_fails_before_receipt_consumption(self):
        self._expect_substitution("revalidate_source_revision", lambda *_args, **_kwargs: {"status": "PASS"})

    def test_feature_compiler_global_substitution_fails_before_receipt_consumption(self):
        self._expect_substitution("compile_retrieval_task", lambda *_args, **_kwargs: {})

    def test_retriever_class_substitution_fails_before_constructor_use(self):
        class ForgedRetriever:
            pass
        with patch.object(runtime, "LearningRetriever", ForgedRetriever):
            with self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                runtime.DirectorLearningRuntime(".")
        self.assertEqual(ctx.exception.code, "WORK_ITEM_RUNTIME_PROVENANCE_SUBSTITUTED")


if __name__ == "__main__":
    unittest.main()
