from collections.abc import Mapping
import unittest

from learning_retriever.active_work_item import ActiveWorkItemResolutionError
from learning_retriever.runtime import DirectorLearningRuntime


class StatefulAuthorityMapping(Mapping):
    """Would reveal authority-shaped content only after an initial traversal."""

    def __init__(self):
        self.iterations = 0

    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 1

    def items(self):
        self.iterations += 1
        if self.iterations == 1:
            return [("prompt", "benign")]
        return [("validation_token", "caller-minted")]


class PreOutputStatefulMappingGuardTests(unittest.TestCase):
    def test_behavioral_mapping_fails_before_any_authority_scan_or_retrieval(self):
        runtime = DirectorLearningRuntime.__new__(DirectorLearningRuntime)
        payload = StatefulAuthorityMapping()

        with self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.build_executable_output("continue", output_content=payload)

        self.assertEqual(ctx.exception.code, "WORK_ITEM_OUTPUT_CONTENT_INVALID")
        self.assertEqual(ctx.exception.details.get("reason"), "output_content_must_be_builtin_dict")
        self.assertEqual(payload.iterations, 0)


if __name__ == "__main__":
    unittest.main()
