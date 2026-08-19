from __future__ import annotations

import hashlib
import io
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

from PIL import Image


class LocatorError(RuntimeError):
    code = "BINARY_NOT_RETRIEVED"


class LocatorNamespaceMismatch(LocatorError):
    code = "LOCATOR_NAMESPACE_MISMATCH"


class LocatorNamespaceRefMismatch(LocatorError):
    code = "LOCATOR_NAMESPACE_REF_MISMATCH"


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
class CloudflareKVLocator:
    namespace: str
    namespace_ref: str
    key: str
    expected_content_sha256: str

    @classmethod
    def from_mapping(cls, value: Dict[str, Any]) -> "CloudflareKVLocator":
        forbidden = {
            "api_token",
            "bearer_token",
            "bearer_url",
            "url",
            "account_id",
            "namespace_id",
            "secret",
        }
        if forbidden.intersection(value):
            raise LocatorNamespaceMismatch(
                "durable cloudflare_kv locator contains forbidden runtime capability/secret field"
            )
        if value.get("namespace") != "cloudflare_kv":
            raise LocatorNamespaceMismatch("locator namespace must be cloudflare_kv")
        required = ("namespace_ref", "key", "expected_content_sha256")
        missing = [name for name in required if not value.get(name)]
        if missing:
            raise LocatorNamespaceMismatch(f"missing durable locator fields: {missing}")
        expected = str(value["expected_content_sha256"]).lower().removeprefix("sha256:")
        return cls(
            namespace="cloudflare_kv",
            namespace_ref=str(value["namespace_ref"]),
            key=str(value["key"]),
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


def require_kv_environment(env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = dict(os.environ if env is None else env)
    required = [
        "EUSTIA_KV_API_TOKEN",
        "EUSTIA_KV_ACCOUNT_ID",
        "EUSTIA_KV_NAMESPACE_ID",
        "EUSTIA_KV_NAMESPACE",
    ]
    missing = [name for name in required if not env.get(name)]
    if missing:
        raise AuthUnavailable("missing Workers KV runtime configuration: " + ",".join(missing))
    return {name: env[name] for name in required}


class CloudflareKVClient:
    def __init__(self, *, api_token: str, account_id: str, namespace_id: str, timeout: float = 20.0):
        self._api_token = api_token
        self._account_id = account_id
        self._namespace_id = namespace_id
        self._timeout = timeout

    @classmethod
    def from_environment(cls, env: Optional[Dict[str, str]] = None) -> "CloudflareKVClient":
        cfg = require_kv_environment(env)
        return cls(
            api_token=cfg["EUSTIA_KV_API_TOKEN"],
            account_id=cfg["EUSTIA_KV_ACCOUNT_ID"],
            namespace_id=cfg["EUSTIA_KV_NAMESPACE_ID"],
        )

    def _value_url(self, key: str) -> str:
        encoded = urllib.parse.quote(key, safe="")
        return (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self._account_id}/storage/kv/namespaces/{self._namespace_id}/values/{encoded}"
        )

    def _request(self, *, key: str, method: str, body: Optional[bytes] = None) -> bytes:
        headers = {"Authorization": f"Bearer {self._api_token}"}
        if body is not None:
            headers["Content-Type"] = "application/octet-stream"
        req = urllib.request.Request(self._value_url(key), data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise LocatorNotFound("404") from exc
            if exc.code in {401, 403}:
                raise AuthUnavailable(str(exc.code)) from exc
            raise BinaryTransportUnavailable(f"HTTP_{exc.code}") from exc
        except urllib.error.URLError as exc:
            raise BinaryTransportUnavailable(exc.__class__.__name__) from exc

    def put(self, key: str, payload: bytes) -> None:
        self._request(key=key, method="PUT", body=payload)

    def get(self, key: str) -> bytes:
        payload = self._request(key=key, method="GET")
        if not isinstance(payload, (bytes, bytearray)):
            raise BinaryTransportUnavailable("Workers KV GET did not yield bytes")
        return bytes(payload)

    def delete(self, key: str) -> None:
        self._request(key=key, method="DELETE")


def validate_namespace_ref(locator: CloudflareKVLocator, env: Optional[Dict[str, str]] = None) -> None:
    cfg = require_kv_environment(env)
    if locator.namespace_ref != cfg["EUSTIA_KV_NAMESPACE"]:
        raise LocatorNamespaceRefMismatch(
            f"locator namespace_ref {locator.namespace_ref!r} does not match secret-bound namespace alias"
        )


def retrieve_and_verify(
    client: CloudflareKVClient,
    locator: CloudflareKVLocator,
    *,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    validate_namespace_ref(locator, env)
    payload = client.get(locator.key)
    evidence = verify_image_payload(payload, locator.expected_content_sha256)
    evidence.update(
        {
            "namespace": locator.namespace,
            "namespace_ref": locator.namespace_ref,
            "key": locator.key,
            "binary_retrieved": True,
        }
    )
    return evidence


def retrieve_with_retry(
    client: CloudflareKVClient,
    locator: CloudflareKVLocator,
    *,
    env: Optional[Dict[str, str]] = None,
    attempts: int = 6,
    initial_delay: float = 0.5,
) -> Dict[str, Any]:
    delay = initial_delay
    last_error: Optional[Exception] = None
    for index in range(attempts):
        try:
            result = retrieve_and_verify(client, locator, env=env)
            result["read_attempts"] = index + 1
            return result
        except LocatorNotFound as exc:
            last_error = exc
            if index == attempts - 1:
                break
            time.sleep(delay)
            delay = min(delay * 2, 4.0)
    if last_error is not None:
        raise last_error
    raise LocatorNotFound("object unavailable after retry budget")


def same_version_fallback(
    client: CloudflareKVClient,
    locators: Iterable[CloudflareKVLocator],
    *,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    trace = []
    for locator in locators:
        try:
            evidence = retrieve_and_verify(client, locator, env=env)
            trace.append({"key": locator.key, "outcome": "RETRIEVED"})
            evidence["locator_trace"] = trace
            return evidence
        except LocatorError as exc:
            trace.append({"key": locator.key, "outcome": "FAILED", "failure_code": exc.code})
    raise LocatorNotFound(f"all locators failed: {trace}")
