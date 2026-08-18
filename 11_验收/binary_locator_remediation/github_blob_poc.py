#!/usr/bin/env python3
"""Synthetic GitHub Blob dereference PoC for REG-ASSET-BINARY-LOCATOR-REMEDIATION-001.

This validates provider protocol behavior only. It does NOT prove that the ChatGPT
GitHub connector can transport arbitrary binary bytes to a multimodal runtime.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import urllib.error
import urllib.request

from PIL import Image

REPO = "vxz2datoubo/eustia-ai-film"
BLOB_SHA = "8251a66290e1619b2262fa2d6ac0429d134e4b23"
EXPECTED_SHA256 = "36f1626eebe1985b0ac4bb691f40ebe586a47c5a1c442d2cfe12e8e4c8bfa3b3"
EXPECTED_DIMENSIONS = (2, 2)
BAD_BLOB_SHA = "0" * 40


class NamespaceMismatch(ValueError):
    pass


def validate_namespace(locator_type: str) -> None:
    if locator_type != "github_blob":
        raise NamespaceMismatch(f"github_blob adapter rejects namespace: {locator_type}")


def fetch_blob(blob_sha: str) -> bytes:
    url = f"https://api.github.com/repos/{REPO}/git/blobs/{blob_sha}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.load(response)
    if payload.get("encoding") != "base64":
        raise RuntimeError(f"unexpected blob encoding: {payload.get('encoding')}")
    return base64.b64decode(payload["content"])


def inspect_image(data: bytes) -> tuple[str, tuple[int, int], str]:
    digest = hashlib.sha256(data).hexdigest()
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        return digest, image.size, image.format or "UNKNOWN"


def main() -> int:
    validate_namespace("github_blob")

    first = fetch_blob(BLOB_SHA)
    first_hash, first_size, first_format = inspect_image(first)
    assert first_hash == EXPECTED_SHA256, (first_hash, EXPECTED_SHA256)
    assert first_size == EXPECTED_DIMENSIONS, (first_size, EXPECTED_DIMENSIONS)
    assert first_format == "PNG", first_format

    second = fetch_blob(BLOB_SHA)
    second_hash, second_size, second_format = inspect_image(second)
    assert second_hash == first_hash
    assert second_size == first_size
    assert second_format == first_format

    try:
        fetch_blob(BAD_BLOB_SHA)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404, exc.code
    else:
        raise AssertionError("unknown blob locator did not fail closed")

    for wrong_namespace in ("chatgpt_file_id", "openai_api_file_id"):
        try:
            validate_namespace(wrong_namespace)
        except NamespaceMismatch:
            pass
        else:
            raise AssertionError(f"namespace collision accepted: {wrong_namespace}")

    print(json.dumps({
        "locator_type": "github_blob",
        "blob_sha": BLOB_SHA,
        "byte_count": len(first),
        "sha256": first_hash,
        "dimensions": list(first_size),
        "image_format": first_format,
        "second_retrieval_sha256_identical": True,
        "unknown_locator_fail_closed": True,
        "namespace_collision_rejected": ["chatgpt_file_id", "openai_api_file_id"],
        "evidence_class": "SYNTHETIC_PROVIDER_PROTOCOL_POC_ONLY"
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
