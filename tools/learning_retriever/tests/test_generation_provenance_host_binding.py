from __future__ import annotations

import inspect
from pathlib import Path
import unittest

import yaml

from learning_retriever.generation_provenance_host_binding import (
    assess_repo_only_generation_provenance,
    future_host_attestation_requirements,
)
from learning_retriever.immutable_byte_identity import ByteIdentityError


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO_ROOT / "10_运行时/generation_provenance_host_binding_candidate.yaml"
REGRESSION_PATH = REPO_ROOT / "11_验收/generation_provenance_host_binding_regression_cases.yaml"
RUNTIME_PATH = REPO_ROOT / "tools/learning_retriever/learning_retriever/generation_provenance_host_binding.py"
PROJECT_INDEX = REPO_ROOT / "PROJECT_INDEX.yaml"
READ_SETS = REPO_ROOT / "10_运行时/read_sets.yaml"
WRITE_ROUTES = REPO_ROOT / "10_运行时/write_routes.yaml"


class GenerationProvenanceHostBindingTests(unittest.TestCase):
    def test_same_bytes_prove_only_same_content(self):
        result = assess_repo_only_generation_provenance(b"same", b"same")
        self.assertTrue(result.byte_pair.same_content)
        self.assertFalse(result.byte_pair.distinct_content_observed)
        self.assertEqual(result.status, "UNVERIFIED_HOST_ATTESTATION_REQUIRED")
        self.assertTrue(result.byte_content_identity_verified)
        self.assertFalse(result.source_artifact_binding_verified)
        self.assertFalse(result.generation_event_binding_verified)
        self.assertFalse(result.distinct_generation_events_verified)

    def test_distinct_bytes_do_not_prove_distinct_generation_events(self):
        result = assess_repo_only_generation_provenance(b"abc", b"abd")
        self.assertTrue(result.byte_pair.distinct_content_observed)
        self.assertFalse(result.distinct_generation_events_verified)
        self.assertFalse(result.generation_event_binding_verified)
        self.assertFalse(result.causal_attribution_authorized)
        self.assertFalse(result.regression_support_authorized)
        self.assertFalse(result.maturity_support_authorized)
        self.assertFalse(result.writeback_authorized)

    def test_public_api_has_no_attestation_or_metadata_input_surface(self):
        params = inspect.signature(assess_repo_only_generation_provenance).parameters
        self.assertEqual(list(params), ["before", "after"])
        for forbidden in (
            "host_attestation",
            "generation_id",
            "media_ref",
            "sha256",
            "digest",
            "verified",
            "artifact_id",
            "source_path",
            "provider_job_id",
        ):
            self.assertNotIn(forbidden, params)
        with self.assertRaises(TypeError):
            assess_repo_only_generation_provenance(
                b"a", b"b", host_attestation={"verified": True}  # type: ignore[call-arg]
            )

    def test_non_bytes_and_bytes_subclasses_fail_before_provenance_assessment(self):
        class HostileBytes(bytes):
            hook_called = False

            def __len__(self):  # pragma: no cover - must never run
                type(self).hook_called = True
                return 999

        for value in (
            bytearray(b"mutable"),
            memoryview(b"view"),
            "artifact.bin",
            {"generation_id": "fake"},
            HostileBytes(b"abc"),
        ):
            HostileBytes.hook_called = False
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ByteIdentityError):
                    assess_repo_only_generation_provenance(value, b"after")  # type: ignore[arg-type]
                self.assertFalse(HostileBytes.hook_called)

    def test_diagnostic_receipt_denies_replay_and_downstream_authority(self):
        diagnostic = assess_repo_only_generation_provenance(b"a", b"b").diagnostic_dict()
        self.assertFalse(diagnostic["serialized_receipt_reusable_as_authority"])
        self.assertFalse(diagnostic["source_artifact_binding_verified"])
        self.assertFalse(diagnostic["generation_event_binding_verified"])
        self.assertFalse(diagnostic["distinct_generation_events_verified"])
        self.assertFalse(diagnostic["formal_asset_binding_verified"])
        self.assertFalse(diagnostic["generation_reference_binding_verified"])
        self.assertFalse(diagnostic["causal_attribution_authorized"])
        self.assertFalse(diagnostic["regression_support_authorized"])
        self.assertFalse(diagnostic["maturity_support_authorized"])
        self.assertFalse(diagnostic["writeback_authorized"])
        with self.assertRaises(TypeError):
            assess_repo_only_generation_provenance(
                b"a", b"b", receipt=diagnostic  # type: ignore[call-arg]
            )

    def test_future_host_contract_is_descriptive_only(self):
        requirements = future_host_attestation_requirements()
        self.assertEqual(
            requirements["status"],
            "DESCRIPTIVE_ONLY_NOT_ACCEPTED_AS_INPUT",
        )
        self.assertTrue(requirements["must_be_host_originated"])
        self.assertTrue(requirements["must_not_be_caller_mintable"])
        self.assertTrue(requirements["must_bind_exact_output_bytes_or_content_identity"])
        self.assertTrue(requirements["must_bind_provider_or_tool_generation_event_identity"])
        self.assertTrue(requirements["serialized_mapping_alone_is_insufficient"])
        self.assertTrue(requirements["repo_embedded_secret_is_forbidden"])
        self.assertTrue(requirements["python_private_token_is_not_a_security_boundary"])
        self.assertTrue(requirements["positive_verifier_requires_fresh_independent_trust_review"])

    def test_candidate_contract_locks_negative_capability(self):
        policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
        regression = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["status"], "candidate")
        self.assertFalse(policy["public_runtime"]["host_attestation_parameter_present"])
        self.assertFalse(policy["public_runtime"]["positive_generation_verification_path_present"])
        self.assertFalse(policy["relationship_to_final_delta"]["may_set_artifact_provenance_verified"])
        self.assertTrue(policy["hard_invariants"]["python_private_token_is_not_security_boundary"])
        self.assertTrue(policy["hard_invariants"]["repo_embedded_secret_forbidden"])
        self.assertTrue(regression["invariants"]["repo_only_positive_generation_verification_absent"])

    def test_runtime_has_no_filesystem_network_process_or_generation_surface(self):
        source = RUNTIME_PATH.read_text(encoding="utf-8")
        forbidden_imports = (
            "import os",
            "from os",
            "import pathlib",
            "from pathlib",
            "import socket",
            "from socket",
            "import subprocess",
            "from subprocess",
            "import requests",
            "from requests",
            "import urllib",
            "from urllib",
        )
        for token in forbidden_imports:
            self.assertNotIn(token, source)
        for token in ("open(", ".read(", ".stat(", "image_gen", "seedance", "seedream"):
            self.assertNotIn(token, source.casefold())

    def test_candidate_is_not_registered_or_activated(self):
        index = PROJECT_INDEX.read_text(encoding="utf-8")
        read_sets = READ_SETS.read_text(encoding="utf-8")
        write_routes = WRITE_ROUTES.read_text(encoding="utf-8")
        marker = "generation_provenance_host_binding"
        self.assertNotIn(marker, index)
        self.assertNotIn(marker, read_sets)
        self.assertNotIn(marker, write_routes)


if __name__ == "__main__":
    unittest.main()
