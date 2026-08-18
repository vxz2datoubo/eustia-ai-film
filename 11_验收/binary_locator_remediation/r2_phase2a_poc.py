from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

from r2_adapter import (
    AuthUnavailable,
    ImageDecodeFailed,
    LocatorNamespaceMismatch,
    LocatorNotFound,
    R2ObjectLocator,
    Sha256Mismatch,
    build_s3_client,
    get_object_bytes,
    require_r2_environment,
    retrieve_and_verify,
    same_version_fallback,
    sha256_bytes,
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


def structural_contract_tests():
    payload = FIXTURE.read_bytes()
    expected = sha256_bytes(payload)

    expect_error(
        lambda: R2ObjectLocator.from_mapping(
            {
                "namespace": "chatgpt_file_id",
                "bucket_ref": "redacted",
                "object_key": "synthetic.png",
                "expected_content_sha256": expected,
            }
        ),
        "LOCATOR_NAMESPACE_MISMATCH",
    )
    expect_error(
        lambda: R2ObjectLocator.from_mapping(
            {
                "namespace": "r2_object",
                "bucket_ref": "redacted",
                "object_key": "synthetic.png",
                "expected_content_sha256": expected,
                "presigned_url": "https://example.invalid/?X-Amz-Signature=REDACTED",
            }
        ),
        "LOCATOR_NAMESPACE_MISMATCH",
    )
    expect_error(lambda: require_r2_environment({}), "AUTH_UNAVAILABLE")
    expect_error(lambda: verify_image_payload(payload, "0" * 64), "SHA256_MISMATCH")
    expect_error(lambda: verify_image_payload(b"not-an-image", sha256_bytes(b"not-an-image")), "IMAGE_DECODE_FAILED")

    return {
        "status": "PASS",
        "wrong_namespace_fail_closed": True,
        "presigned_url_rejected_as_durable_locator": True,
        "credential_unavailable_fail_closed": True,
        "wrong_sha256_fail_closed": True,
        "corrupt_non_image_fail_closed": True,
    }


def capability_report():
    required = [
        "EUSTIA_R2_POC_ENABLED",
        "R2_ENDPOINT_URL",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
    ]
    present = {name: bool(os.environ.get(name)) for name in required}
    enabled = os.environ.get("EUSTIA_R2_POC_ENABLED", "").lower() == "true"
    ready = enabled and all(present[name] for name in required[1:])
    emit(
        {
            "phase": "PHASE_2A_R2_SYNTHETIC_RUNTIME_POC",
            "runtime_config_present": present,
            "live_runtime_ready": ready,
            "status": "READY_FOR_LIVE_R2_POC" if ready else "STOP_FOR_EXTERNAL_CAPABILITY",
            "note": "booleans only; no credential or endpoint value is emitted",
        }
    )
    return 0 if ready else 78


def live_runtime_poc():
    cfg = require_r2_environment()
    fixture = FIXTURE.read_bytes()
    fixture_sha = sha256_bytes(fixture)
    client = build_s3_client()
    prefix = os.environ.get("R2_TEST_PREFIX", "eustia-binary-locator-poc")
    run_id = uuid.uuid4().hex[:12]
    good_key = f"{prefix}/{run_id}/synthetic_probe.png"
    corrupt_key = f"{prefix}/{run_id}/corrupt.bin"
    unknown_key_a = f"{prefix}/{run_id}/missing-a.png"
    unknown_key_b = f"{prefix}/{run_id}/missing-b.png"
    bucket = cfg["R2_BUCKET"]

    created = []
    try:
        client.put_object(Bucket=bucket, Key=good_key, Body=fixture, ContentType="image/png")
        created.append(good_key)
        locator = R2ObjectLocator(
            namespace="r2_object",
            bucket_ref=bucket,
            object_key=good_key,
            expected_content_sha256=fixture_sha,
        )
        first = retrieve_and_verify(client, locator)
        second = retrieve_and_verify(client, locator)
        if first["sha256"] != second["sha256"]:
            raise AssertionError("second retrieval SHA-256 differs")

        missing = R2ObjectLocator(
            namespace="r2_object",
            bucket_ref=bucket,
            object_key=unknown_key_a,
            expected_content_sha256=fixture_sha,
        )
        expect_error(lambda: get_object_bytes(client, missing), "LOCATOR_NOT_FOUND")

        wrong_hash = R2ObjectLocator(
            namespace="r2_object",
            bucket_ref=bucket,
            object_key=good_key,
            expected_content_sha256="0" * 64,
        )
        expect_error(lambda: retrieve_and_verify(client, wrong_hash), "SHA256_MISMATCH")

        corrupt = b"EUSTIA-R2-CORRUPT-NON-IMAGE"
        client.put_object(Bucket=bucket, Key=corrupt_key, Body=corrupt, ContentType="application/octet-stream")
        created.append(corrupt_key)
        corrupt_locator = R2ObjectLocator(
            namespace="r2_object",
            bucket_ref=bucket,
            object_key=corrupt_key,
            expected_content_sha256=sha256_bytes(corrupt),
        )
        expect_error(lambda: retrieve_and_verify(client, corrupt_locator), "IMAGE_DECODE_FAILED")

        missing_b = R2ObjectLocator(
            namespace="r2_object",
            bucket_ref=bucket,
            object_key=unknown_key_b,
            expected_content_sha256=fixture_sha,
        )
        expect_error(lambda: same_version_fallback(client, [missing, missing_b]), "LOCATOR_NOT_FOUND")

        bad_env = dict(os.environ)
        bad_env["R2_SECRET_ACCESS_KEY"] = "intentionally-invalid-secret-for-negative-test"
        bad_client = build_s3_client(bad_env)
        auth_failure = None
        try:
            get_object_bytes(bad_client, locator)
        except AuthUnavailable as exc:
            auth_failure = exc.code
        if auth_failure != "AUTH_UNAVAILABLE":
            raise AssertionError("invalid credential did not fail closed as AUTH_UNAVAILABLE")

        emit(
            {
                "phase": "PHASE_2A_R2_SYNTHETIC_RUNTIME_POC",
                "status": "PROVIDER_RUNTIME_POC_PASS",
                "evidence_class": "R2_AUTHENTICATED_PROVIDER_RUNTIME_POC",
                "locator_namespace": "r2_object",
                "bucket_ref": "REDACTED_RUNTIME_SECRET_BOUNDARY",
                "object_key_class": "synthetic_ephemeral_test_key",
                "byte_count": first["byte_count"],
                "sha256": first["sha256"],
                "image_format": first["image_format"],
                "dimensions": first["dimensions"],
                "pixels_opened": first["pixels_opened"],
                "second_retrieval_sha256_identical": True,
                "unknown_object_fail_closed": True,
                "invalid_credential_fail_closed": True,
                "wrong_sha256_fail_closed": True,
                "corrupt_non_image_fail_closed": True,
                "all_locators_fail_closed": True,
                "presigned_url_persisted": False,
                "secret_values_emitted": False,
                "chatgpt_binary_transport_verified": False,
                "next_gate": "ACTUAL_CHATGPT_RUNTIME_BINARY_TRANSPORT_STILL_REQUIRED",
            }
        )
        return 0
    finally:
        for key in created:
            try:
                client.delete_object(Bucket=bucket, Key=key)
            except Exception:
                pass


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--structural"
    if mode == "--structural":
        emit({"phase": "PHASE_2A_STRUCTURAL_CONTRACT", **structural_contract_tests()})
        return 0
    if mode == "--capability-report":
        return capability_report()
    if mode == "--live":
        structural_contract_tests()
        return live_runtime_poc()
    raise SystemExit(f"unknown mode: {mode}")


if __name__ == "__main__":
    raise SystemExit(main())
