import inspect
import unittest

from learning_retriever.binary_artifact_evidence import compare_artifact_bytes, observe_artifact_bytes


class BinaryArtifactEvidenceBridgeAPISurfaceTests(unittest.TestCase):
    def test_observer_does_not_accept_caller_digest_or_verified_receipt_parameters(self):
        params = inspect.signature(observe_artifact_bytes).parameters
        for forbidden in ("sha256", "digest", "receipt", "verified", "generation_id", "media_ref"):
            self.assertNotIn(forbidden, params)

    def test_pair_verifier_requires_actual_locators_not_serialized_receipts(self):
        params = inspect.signature(compare_artifact_bytes).parameters
        self.assertEqual(list(params)[:2], ["before_locator", "after_locator"])
        for forbidden in ("before_receipt", "after_receipt", "generation_id", "verified"):
            self.assertNotIn(forbidden, params)


if __name__ == "__main__":
    unittest.main()
