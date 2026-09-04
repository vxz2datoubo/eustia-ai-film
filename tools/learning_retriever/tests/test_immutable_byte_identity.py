from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
import unittest

import yaml

from learning_retriever.immutable_byte_identity import (
    ByteIdentityError,
    ImmutableByteObservation,
    compare_immutable_byte_pair,
    observe_immutable_bytes,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "10_运行时/immutable_byte_identity_candidate.yaml"
REGRESSION_PATH = REPO_ROOT / "11_验收/immutable_byte_identity_regression_cases.yaml"


class ImmutableByteIdentityTests(unittest.TestCase):
    def test_single_value_identity_is_computed_from_exact_supplied_bytes(self):
        payload = b"actual-media-bytes\x00\x01"
        observation = observe_immutable_bytes(payload)
        self.assertEqual(observation.content_sha256, hashlib.sha256(payload).hexdigest())
        self.assertEqual(observation.byte_length, len(payload))
        self.assertEqual(observation.observation_state, "IMMUTABLE_BYTES_OBSERVED")
        self.assertEqual(observation.input_contract, "PYTHON_BYTES_ONLY")
        self.assertEqual(observation.source_artifact_binding_state, "UNVERIFIED")
        self.assertEqual(observation.generation_binding_state, "UNVERIFIED")
        self.assertEqual(observation.formal_asset_binding_state, "UNVERIFIED")
        self.assertEqual(observation.semantic_verification_state, "NOT_PERFORMED")

    def test_same_bytes_are_same_content_without_source_identity_claim(self):
        pair = compare_immutable_byte_pair(b"same-real-bytes", b"same-real-bytes")
        self.assertTrue(pair.same_content)
        self.assertFalse(pair.distinct_content_observed)
        self.assertEqual(pair.before.content_identity, pair.after.content_identity)
        self.assertEqual(pair.source_artifact_binding_state, "UNVERIFIED")
        self.assertEqual(pair.generation_binding_state, "UNVERIFIED")
        diagnostic = pair.diagnostic_dict()
        self.assertFalse(diagnostic["source_artifacts_verified"])
        self.assertFalse(diagnostic["distinct_generation_events_verified"])

    def test_one_byte_difference_proves_only_in_memory_content_difference(self):
        pair = compare_immutable_byte_pair(b"abcdef", b"abcdeg")
        self.assertFalse(pair.same_content)
        self.assertTrue(pair.distinct_content_observed)
        self.assertNotEqual(pair.before.content_sha256, pair.after.content_sha256)
        self.assertEqual(pair.claim_scope, "IN_MEMORY_BYTE_CONTENT_IDENTITY_ONLY")
        self.assertEqual(pair.source_artifact_binding_state, "UNVERIFIED")
        self.assertEqual(pair.generation_binding_state, "UNVERIFIED")
        self.assertEqual(pair.formal_asset_binding_state, "UNVERIFIED")
        diagnostic = pair.diagnostic_dict()
        self.assertFalse(diagnostic["source_artifacts_verified"])
        self.assertFalse(diagnostic["distinct_generation_events_verified"])
        self.assertFalse(diagnostic["formal_assets_verified"])

    def test_empty_bytes_have_deterministic_identity(self):
        observation = observe_immutable_bytes(b"")
        self.assertEqual(observation.byte_length, 0)
        self.assertEqual(
            observation.content_sha256,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

    def test_repeated_observation_is_deterministic(self):
        payload = b"stable immutable value"
        first = observe_immutable_bytes(payload)
        second = observe_immutable_bytes(payload)
        self.assertEqual(first, second)
        self.assertEqual(first.content_identity, second.content_identity)

    def test_public_surface_has_no_digest_locator_or_provenance_parameters(self):
        single = inspect.signature(observe_immutable_bytes).parameters
        pair = inspect.signature(compare_immutable_byte_pair).parameters
        self.assertEqual(list(single), ["payload"])
        self.assertEqual(list(pair), ["before", "after"])
        for forbidden in (
            "sha256", "digest", "byte_length", "verified", "receipt",
            "generation_id", "artifact_path", "path", "locator", "media_ref",
        ):
            self.assertNotIn(forbidden, single)
            self.assertNotIn(forbidden, pair)
        with self.assertRaises(TypeError):
            observe_immutable_bytes(b"x", sha256="0" * 64)

    def test_mutable_or_source_like_inputs_are_rejected_without_coercion(self):
        forged_observation = ImmutableByteObservation(
            content_sha256="0" * 64,
            byte_length=1,
        )
        rejected = (
            bytearray(b"mutable"),
            memoryview(b"view"),
            "/tmp/artifact.bin",
            Path("artifact.bin"),
            {"content_sha256": "0" * 64, "byte_length": 1},
            forged_observation,
            123,
            None,
        )
        for value in rejected:
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ByteIdentityError) as ctx:
                    observe_immutable_bytes(value)  # type: ignore[arg-type]
                self.assertEqual(ctx.exception.code, "BYTE_INPUT_NOT_IMMUTABLE_BYTES")

    def test_serialized_or_constructed_observation_cannot_be_pair_authority(self):
        forged = ImmutableByteObservation(content_sha256="0" * 64, byte_length=999)
        with self.assertRaises(ByteIdentityError) as ctx:
            compare_immutable_byte_pair(forged, b"actual")  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "BYTE_INPUT_NOT_IMMUTABLE_BYTES")
        with self.assertRaises(ByteIdentityError) as ctx:
            compare_immutable_byte_pair(b"actual", forged)  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "BYTE_INPUT_NOT_IMMUTABLE_BYTES")

    def test_diagnostic_receipts_explicitly_deny_provenance_authority(self):
        observation = observe_immutable_bytes(b"x").diagnostic_dict()
        self.assertFalse(observation["source_artifact_verified"])
        self.assertFalse(observation["generation_event_verified"])
        self.assertFalse(observation["formal_asset_verified"])
        self.assertFalse(observation["serialized_receipt_reusable_as_authority"])

    def test_candidate_policy_and_machine_registry_lock_narrow_claim_scope(self):
        policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
        regression = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["status"], "candidate")
        hard = policy["hard_invariants"]
        self.assertTrue(hard["python_bytes_only"])
        self.assertTrue(hard["filesystem_io_forbidden"])
        self.assertTrue(hard["path_resolution_forbidden"])
        self.assertTrue(hard["distinct_bytes_do_not_prove_distinct_source_artifacts"])
        self.assertTrue(hard["distinct_bytes_do_not_prove_distinct_generation_events"])
        self.assertEqual(
            policy["pair_comparison"]["output_claim_limit"],
            "in_memory_byte_content_identity_only",
        )
        self.assertTrue(regression["invariants"]["filesystem_io_surface_absent"])


if __name__ == "__main__":
    unittest.main()
