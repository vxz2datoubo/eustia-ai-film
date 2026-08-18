from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from PIL import Image


class LocatorError(RuntimeError):
    code = "BINARY_NOT_RETRIEVED"


class LocatorNamespaceMismatch(LocatorError):
    code = "LOCATOR_NAMESPACE_MISMATCH"


class LocatorNotFound(LocatorError):
    code = "LOCATOR_NOT_FOUND"


class AuthUnavailable(LocatorError):
    code = "AUTH_UNAVAILABLE"


class BinaryTransportUnavailable(LocatorError):
    code = "BINARY_TRANSPORT_UNAVAILABLE"


class Sha256Mismatch(LocatorError):
    code = "SHA256_MISMATCH"


class ImageDecodeFailed(LocatorError):
    code = "IMAGE_DECODE_FAILED"


@dataclass(frozen=True)
class R2ObjectLocator:
    namespace: str
    bucket_ref: str
    object_key: str
    expected_content_sha256: str

    @classmethod
    def from_mapping(cls, value: Dict[str, Any]) -> "R2ObjectLocator":
        forbidden = {"presigned_url", "url", "bearer_url", "access_key", "secret_key"}
        if forbidden.intersection(value):
            raise LocatorNamespaceMismatch("durable r2_object locator contains forbidden capability/secret field")
        if value.get("namespace") != "r2_object":
            raise LocatorNamespaceMismatch("locator namespace must be r2_object")
        required = ("bucket_ref", "object_key", "expected_content_sha256")
        missing = [k for k in required if not value.get(k)]
        if missing:
            raise LocatorNamespaceMismatch(f"missing durable locator fields: {missing}")
        expected = str(value["expected_content_sha256"]).lower().removeprefix("sha256:")
        return cls(
            namespace="r2_object",
            bucket_ref=str(value["bucket_ref"]),
            object_key=str(value["object_key"]),
            expected_content_sha256=expected,
        )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify_image_payload(payload: bytes, expected_sha256: str) -> Dict[str, Any]:
    observed = sha256_bytes(payload)
    expected = expected_sha256.lower().removeprefix("sha256:")
    if observed != expected:
        raise Sha256Mismatch(f"expected {expected}, observed {observed}")
    try:
        with Image.open(io.BytesIO(payload)) as img:
            img.load()
            return {
                "byte_count": len(payload),
                "sha256": observed,
                "image_format": img.format,
                "dimensions": [img.width, img.height],
                "pixels_opened": True,
            }
    except Exception as exc:
        raise ImageDecodeFailed(str(exc)) from exc


def require_r2_environment(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = dict(os.environ if env is None else env)
    required = [
        "R2_ENDPOINT_URL",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET",
    ]
    missing = [name for name in required if not env.get(name)]
    if missing:
        raise AuthUnavailable("missing R2 runtime configuration: " + ",".join(missing))
    return {name: env[name] for name in required}


def build_s3_client(env: Optional[Dict[str, str]] = None):
    cfg = require_r2_environment(env)
    try:
        import boto3
    except Exception as exc:
        raise BinaryTransportUnavailable("boto3 unavailable") from exc
    return boto3.client(
        "s3",
        endpoint_url=cfg["R2_ENDPOINT_URL"],
        aws_access_key_id=cfg["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=cfg["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def _map_client_error(exc: Exception) -> LocatorError:
    response = getattr(exc, "response", {}) or {}
    error = response.get("Error", {}) or {}
    code = str(error.get("Code", ""))
    http_status = (response.get("ResponseMetadata", {}) or {}).get("HTTPStatusCode")
    if code in {"NoSuchKey", "NoSuchBucket", "NotFound"} or http_status == 404:
        return LocatorNotFound(code or "404")
    if code in {
        "AccessDenied",
        "InvalidAccessKeyId",
        "ExpiredToken",
        "ExpiredRequest",
        "SignatureDoesNotMatch",
        "Unauthorized",
    } or http_status in {401, 403}:
        return AuthUnavailable(code or str(http_status))
    return BinaryTransportUnavailable(code or exc.__class__.__name__)


def get_object_bytes(client, locator: R2ObjectLocator) -> bytes:
    try:
        response = client.get_object(Bucket=locator.bucket_ref, Key=locator.object_key)
        body = response.get("Body")
        if body is None or not hasattr(body, "read"):
            raise BinaryTransportUnavailable("GetObject did not return a readable body")
        payload = body.read()
        if not isinstance(payload, (bytes, bytearray)):
            raise BinaryTransportUnavailable("GetObject body did not yield bytes")
        return bytes(payload)
    except LocatorError:
        raise
    except Exception as exc:
        raise _map_client_error(exc) from exc


def retrieve_and_verify(client, locator: R2ObjectLocator) -> Dict[str, Any]:
    payload = get_object_bytes(client, locator)
    evidence = verify_image_payload(payload, locator.expected_content_sha256)
    evidence.update(
        {
            "namespace": locator.namespace,
            "bucket_ref": locator.bucket_ref,
            "object_key": locator.object_key,
            "binary_retrieved": True,
        }
    )
    return evidence


def same_version_fallback(client, locators: Iterable[R2ObjectLocator]) -> Dict[str, Any]:
    trace = []
    for locator in locators:
        try:
            evidence = retrieve_and_verify(client, locator)
            trace.append({"object_key": locator.object_key, "outcome": "RETRIEVED"})
            evidence["locator_trace"] = trace
            return evidence
        except LocatorError as exc:
            trace.append({"object_key": locator.object_key, "outcome": "FAILED", "failure_code": exc.code})
    raise LocatorNotFound(f"all locators failed: {trace}")
