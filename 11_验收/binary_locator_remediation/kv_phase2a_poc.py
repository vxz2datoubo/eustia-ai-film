from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

from kv_adapter import (
    AuthUnavailable,
    CloudflareKVClient,
    CloudflareKVLocator,
    ImageDecodeFailed,
    LocatorNamespaceMismatch,
    LocatorNamespaceRefMismatch,
    LocatorNotFound,
    Sha256Mismatch,
    require_kv_environment,
    retrieve_and_verify,
    retrieve_with_retry,
    same_version_fallback,
    sha256_bytes,
    validate_namespace_ref,
    verify_image_payload,
)

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "synthetic_probe.png"


def emit(payload):
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def expect_error(call, expected_code):
    try:
        call()
    except Exception as exc:
        code = getattr(exc, "code", exc.__class__.__name__)
        if code != expected_code:
            raise AssertionError(f"expected {expected_code}, got {code}: {exc}") from exc
        return code
    raise AssertionError(f"expected failure {expected_code}")


class AlwaysMissingClient:
    def get(self, key):
        raise LocatorNotFound(key)


def structural_contract_tests():
    payload = FIXTURE.read_bytes()
    expected = sha256_bytes(payload)
    env = {
        "EUSTIA_KV_API_TOKEN": "redacted-test-token",
        "EUSTIA_KV_ACCOUNT_ID": "redacted-test-account",
        "EUSTIA_KV_NAMESPACE_ID": "redacted-test-namespace-id",
        "EUSTIA_KV_NAMESPACE": "eustia-asset-locator-poc",
    }

    expect_error(
        lambda: CloudflareKVLocator.from_mapping(
            {
                "namespace": "r2_object",
                "namespace_ref": "eustia-asset-locator-poc",
                "key": "synthetic.png",
                "expected_content_sha256": expected,
            }
        ),
        "LOCATOR_NAMESPACE_MISMATCH",
    )
    expect_error(
        lambda: CloudflareKVLocator.from_mapping(
            {
                "namespace": "cloudflare_kv",
                "namespace_ref": "eustia-asset-locator-poc",
                "key": "synthetic.png",
                "expected_content_sha256": expected,
                "api_token": "forbidden",
            }
        ),
        "LOCATOR_NAMESPACE_MISMATCH",
    )
    expect_error(lambda: require_kv_environment({}), "AUTH_UNAVAILABLE")
    expect_error(lambda: verify_image_payload(payload, "0" * 64), "SHA256_MISMATCH")
    expect_error(lambda: verify_image_payload(b"not-an-image", sha256_bytes(b"not-an-image")), "IMAGE_DECODE_FAILED")

    good = CloudflareKVLocator(
        namespace="cloudflare_kv",
        namespace_ref="eustia-asset-locator-poc",
        key="synthetic.png",
        expected_content_sha256=expected,
    )
    wrong_ref = CloudflareKVLocator(
        namespace="cloudflare_kv",
        namespace_ref="another-namespace",
        key="synthetic.png",
        expected_content_sha256=expected,
    )
    expect_error(lambda: validate_namespace_ref(wrong_ref, env), "LOCATOR_NAMESPACE_REF_MISMATCH")

    missing_a = CloudflareKVLocator(
        namespace="cloudflare_kv",
        namespace_ref="eustia-asset-locator-poc",
        key="missing-a.png",
        expected_content_sha256=expected,
    )
    missing_b = CloudflareKVLocator(
        namespace="cloudflare_kv",
        namespace_ref="eustia-asset-locator-poc",
        key="missing-b.png",
        expected_content_sha256=expected,
    )
    expect_error(
        lambda: same_version_fallback(AlwaysMissingClient(), [missing_a, missing_b], env=env),
        "LOCATOR_NOT_FOUND",
    )

    return {
        "status": "PASS",
        "wrong_namespace_fail_closed": True,
        "runtime_secret_fields_rejected_from_durable_locator": True,
        "credential_unavailable_fail_closed": True,
        "namespace_ref_mismatch_fail_closed": True,
        "wrong_sha256_fail_closed": True,
        "corrupt_non_image_fail_closed": True,
        "all_locators_fail_closed": True,
    }


def capability_report():
    required = [
        "EUSTIA_KV_POC_ENABLED",
        "EUSTIA_KV_API_TOKEN",
        "EUSTIA_KV_ACCOUNT_ID",
        "EUSTIA_KV_NAMESPACE_ID",
        "EUSTIA_KV_NAMESPACE",
    ]
    present = {name: bool(os.environ.get(name)) for name in required}
    enabled = os.environ.get("EUSTIA_KV_POC_ENABLED", "").lower() == "true"
    ready = enabled and all(present[name] for name in required[1:])
    emit(
        {
            "phase": "PHASE_2A_CLOUDFLARE_KV_SYNTHETIC_RUNTIME_POC",
            "runtime_config_present": present,
            "live_runtime_ready": ready,
            "status": "READY_FOR_LIVE_KV_POC" if ready else "STOP_FOR_EXTERNAL_CAPABILITY",
            "note": "booleans only; no account id, namespace id, token, or bearer value is emitted",
        }
    )
    return 0 if ready else 78


def live_runtime_poc():
    cfg = require_kv_environment()
    fixture = FIXTURE.read_bytes()
    fixture_sha = sha256_bytes(fixture)
    client = CloudflareKVClient.from_environment()
    prefix = os.environ.get("KV_TEST_PREFIX", "eustia-binary-locator-poc")
    run_id = uuid.uuid4().hex[:12]
    good_key = f"{prefix}/{run_id}/synthetic_probe.png"
    corrupt_key = f"{prefix}/{run_id}/corrupt.bin"
    unknown_key_a = f"{prefix}/{run_id}/missing-a.png"
    unknown_key_b = f"{prefix}/{run_id}/missing-b.png"
    namespace_ref = cfg["EUSTIA_KV_NAMESPACE"]

    created = []
    try:
        client.put(good_key, fixture)
        created.append(good_key)
        locator = CloudflareKVLocator(
            namespace="cloudflare_kv",
            namespace_ref=namespace_ref,
            key=good_key,
            expected_content_sha256=fixture_sha,
        )
        first = retrieve_with_retry(client, locator)
        second = retrieve_and_verify(client, locator)
        if first["sha256"] != second["sha256"]:
            raise AssertionError("second retrieval SHA-256 differs")

        missing = CloudflareKVLocator(
            namespace="cloudflare_kv",
            namespace_ref=namespace_ref,
            key=unknown_key_a,
            expected_content_sha256=fixture_sha,
        )
        expect_error(lambda: client.get(missing.key), "LOCATOR_NOT_FOUND")

        wrong_hash = CloudflareKVLocator(
            namespace="cloudflare_kv",
            namespace_ref=namespace_ref,
            key=good_key,
            expected_content_sha256="0" * 64,
        )
        expect_error(lambda: retrieve_and_verify(client, wrong_hash), "SHA256_MISMATCH")

        corrupt = b"EUSTIA-KV-CORRUPT-NON-IMAGE"
        client.put(corrupt_key, corrupt)
        created.append(corrupt_key)
        corrupt_locator = CloudflareKVLocator(
            namespace="cloudflare_kv",
            namespace_ref=namespace_ref,
            key=corrupt_key,
            expected_content_sha256=sha256_bytes(corrupt),
        )
        expect_error(lambda: retrieve_and_verify(client, corrupt_locator), "IMAGE_DECODE_FAILED")

        missing_b = CloudflareKVLocator(
            namespace="cloudflare_kv",
            namespace_ref=namespace_ref,
            key=unknown_key_b,
            expected_content_sha256=fixture_sha,
        )
        expect_error(lambda: same_version_fallback(client, [missing, missing_b]), "LOCATOR_NOT_FOUND")

        bad_env = dict(os.environ)
        bad_env["EUSTIA_KV_API_TOKEN"] = "intentionally-invalid-token-for-negative-test"
        bad_client = CloudflareKVClient.from_environment(bad_env)
        auth_failure = None
        try:
            bad_client.get(good_key)
        except AuthUnavailable as exc:
            auth_failure = exc.code
        if auth_failure != "AUTH_UNAVAILABLE":
            raise AssertionError("invalid credential did not fail closed as AUTH_UNAVAILABLE")

        retrieved_payload = client.get(good_key)
        if sha256_bytes(retrieved_payload) != fixture_sha:
            raise AssertionError("artifact bridge payload hash differs from fixture")

        output_dir = os.environ.get("EUSTIA_KV_OUTPUT_DIR")
        artifact_written = False
        if output_dir:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            image_path = out / "kv_retrieved_synthetic.png"
            image_path.write_bytes(retrieved_payload)
            evidence_path = out / "kv_provider_runtime_evidence.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "evidence_class": "CLOUDFLARE_KV_AUTHENTICATED_PROVIDER_RUNTIME_POC",
                        "locator_namespace": "cloudflare_kv",
                        "namespace_ref": namespace_ref,
                        "key_class": "synthetic_ephemeral_test_key",
                        "byte_count": first["byte_count"],
                        "sha256": first["sha256"],
                        "image_format": first["image_format"],
                        "dimensions": first["dimensions"],
                        "pixels_opened_in_runner": first["pixels_opened"],
                        "second_retrieval_sha256_identical": True,
                        "account_id_persisted": False,
                        "namespace_id_persisted": False,
                        "api_token_persisted": False,
                        "formal_media_used": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            artifact_written = True

        emit(
            {
                "phase": "PHASE_2A_CLOUDFLARE_KV_SYNTHETIC_RUNTIME_POC",
                "status": "PROVIDER_RUNTIME_POC_PASS",
                "evidence_class": "CLOUDFLARE_KV_AUTHENTICATED_PROVIDER_RUNTIME_POC",
                "locator_namespace": "cloudflare_kv",
                "namespace_ref": namespace_ref,
                "key_class": "synthetic_ephemeral_test_key",
                "byte_count": first["byte_count"],
                "sha256": first["sha256"],
                "image_format": first["image_format"],
                "dimensions": first["dimensions"],
                "pixels_opened_in_runner": first["pixels_opened"],
                "second_retrieval_sha256_identical": True,
                "unknown_object_fail_closed": True,
                "invalid_credential_fail_closed": True,
                "wrong_sha256_fail_closed": True,
                "corrupt_non_image_fail_closed": True,
                "all_locators_fail_closed": True,
                "durable_bearer_capability_persisted": False,
                "secret_values_emitted": False,
                "artifact_bridge_payload_written": artifact_written,
                "actual_chatgpt_runtime_binary_transport_verified": False,
                "phase_2a_full_pass": False,
                "next_gate": "DOWNLOAD_PRIVATE_WORKFLOW_ARTIFACT_IN_CHATGPT_AND_OPEN_PIXELS",
            }
        )
        return 0
    finally:
        for key in created:
            try:
                client.delete(key)
            except Exception:
                pass


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--structural"
    if mode == "--structural":
        emit({"phase": "PHASE_2A_CLOUDFLARE_KV_STRUCTURAL_CONTRACT", **structural_contract_tests()})
        return 0
    if mode == "--capability-report":
        return capability_report()
    if mode == "--live":
        structural_contract_tests()
        return live_runtime_poc()
    raise SystemExit(f"unknown mode: {mode}")


if __name__ == "__main__":
    raise SystemExit(main())
