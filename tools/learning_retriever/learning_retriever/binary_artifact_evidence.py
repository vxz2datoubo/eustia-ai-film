"""Read-only binary artifact identity evidence for the EUSTIA AI-film runtime.

This candidate proves only what it actually reads. A locator, File ID, filename,
caller digest, serialized receipt, or generation label is never content identity.
The runtime opens ordinary files itself, streams their bytes through SHA-256, and
returns invocation-local evidence. Distinct byte content does NOT prove distinct
model generation events and does NOT register a formal project asset.
"""
from __future__ import annotations

from dataclasses import dataclass
import errno
import hashlib
import os
from pathlib import Path
import stat
from typing import Any, Mapping


class ArtifactEvidenceError(ValueError):
    """Fail-closed binary evidence error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


_DEFAULT_CHUNK_SIZE = 1024 * 1024
_MIN_CHUNK_SIZE = 4096
_MAX_CHUNK_SIZE = 8 * 1024 * 1024


@dataclass(frozen=True)
class ArtifactByteObservation:
    content_sha256: str
    byte_length: int
    locator_fingerprint: str
    locator_class: str = "local_path_invocation"
    byte_verification_state: str = "BYTE_VERIFIED"
    generation_binding_state: str = "UNVERIFIED"
    formal_asset_state: str = "UNVERIFIED"
    pixel_semantic_verification_state: str = "NOT_PERFORMED"

    @property
    def content_identity(self) -> str:
        return f"sha256:{self.content_sha256}:{self.byte_length}"

    def diagnostic_dict(self) -> dict[str, Any]:
        """Serialize diagnostics only; serialized output is never verifier input."""
        return {
            "content_sha256": self.content_sha256,
            "byte_length": self.byte_length,
            "locator_fingerprint": self.locator_fingerprint,
            "locator_class": self.locator_class,
            "byte_verification_state": self.byte_verification_state,
            "generation_binding_state": self.generation_binding_state,
            "formal_asset_state": self.formal_asset_state,
            "pixel_semantic_verification_state": self.pixel_semantic_verification_state,
            "serialized_receipt_reusable_as_authority": False,
        }


@dataclass(frozen=True)
class ArtifactPairEvidence:
    before: ArtifactByteObservation
    after: ArtifactByteObservation
    same_content: bool
    distinct_content_verified: bool
    pair_digest: str
    claim_scope: str = "BYTE_CONTENT_IDENTITY_ONLY"
    generation_binding_state: str = "UNVERIFIED"
    formal_asset_binding_state: str = "UNVERIFIED"

    def diagnostic_dict(self) -> dict[str, Any]:
        return {
            "before": self.before.diagnostic_dict(),
            "after": self.after.diagnostic_dict(),
            "same_content": self.same_content,
            "distinct_content_verified": self.distinct_content_verified,
            "pair_digest": self.pair_digest,
            "claim_scope": self.claim_scope,
            "generation_binding_state": self.generation_binding_state,
            "formal_asset_binding_state": self.formal_asset_binding_state,
            "distinct_generation_events_verified": False,
            "formal_assets_verified": False,
            "serialized_receipt_reusable_as_authority": False,
        }


def _locator_path(value: Any) -> Path:
    # Mapping/dict input is rejected explicitly so a serialized diagnostic
    # receipt cannot be replayed into the verifier as if it were a locator.
    if isinstance(value, Mapping):
        raise ArtifactEvidenceError(
            "ARTIFACT_LOCATOR_INVALID",
            "serialized mappings/receipts are not artifact locator authority",
        )
    if not isinstance(value, (str, os.PathLike)):
        raise ArtifactEvidenceError(
            "ARTIFACT_LOCATOR_INVALID",
            "artifact locator must be an actual local path string or PathLike",
        )
    raw = os.fspath(value)
    if isinstance(raw, bytes):
        raw = os.fsdecode(raw)
    if not isinstance(raw, str) or not raw.strip():
        raise ArtifactEvidenceError("ARTIFACT_LOCATOR_INVALID", "artifact locator is empty")
    return Path(raw)


def _locator_fingerprint(path: Path) -> str:
    # Locator fingerprint is deliberately separate from content identity.
    absolute = os.path.abspath(os.fspath(path))
    return hashlib.sha256(absolute.encode("utf-8", errors="surrogatepass")).hexdigest()[:24]


def _validated_chunk_size(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ArtifactEvidenceError("ARTIFACT_LOCATOR_INVALID", "chunk_size must be an integer")
    if not (_MIN_CHUNK_SIZE <= value <= _MAX_CHUNK_SIZE):
        raise ArtifactEvidenceError(
            "ARTIFACT_LOCATOR_INVALID",
            f"chunk_size must be between {_MIN_CHUNK_SIZE} and {_MAX_CHUNK_SIZE}",
        )
    return value


def _preclassify_locator(path: Path) -> None:
    """Reject obvious locator-type violations consistently across operating systems.

    This lstat result is not content authority. The opened file descriptor is still
    revalidated with fstat before and after reading so a path race cannot mint byte
    identity from this precheck.
    """

    try:
        observed = os.lstat(os.fspath(path))
    except FileNotFoundError as exc:
        raise ArtifactEvidenceError("ARTIFACT_NOT_FOUND", "artifact file does not exist") from exc
    except OSError as exc:
        if exc.errno in {errno.EACCES, errno.EPERM}:
            raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact locator cannot be inspected") from exc
        raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact locator precheck failed") from exc

    if stat.S_ISLNK(observed.st_mode):
        raise ArtifactEvidenceError(
            "ARTIFACT_LOCATOR_INDIRECTION_FORBIDDEN",
            "symbolic-link artifact locators are rejected by candidate v1",
        )
    if not stat.S_ISREG(observed.st_mode):
        raise ArtifactEvidenceError(
            "ARTIFACT_NOT_REGULAR_FILE",
            "artifact locator must resolve to a regular file",
        )


def inspect_artifact_bytes(
    artifact_path: str | os.PathLike[str], *, chunk_size: int = _DEFAULT_CHUNK_SIZE
) -> ArtifactByteObservation:
    """Open and hash actual bytes read-only; never trust caller-supplied digest metadata."""

    path = _locator_path(artifact_path)
    chunk_size = _validated_chunk_size(chunk_size)
    _preclassify_locator(path)

    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    if nofollow:
        flags |= nofollow

    try:
        fd = os.open(os.fspath(path), flags)
    except FileNotFoundError as exc:
        # The file disappeared after lstat. This is a fail-closed race, not proof.
        raise ArtifactEvidenceError("ARTIFACT_NOT_FOUND", "artifact file disappeared before read") from exc
    except OSError as exc:
        if exc.errno in {errno.ELOOP}:
            raise ArtifactEvidenceError(
                "ARTIFACT_LOCATOR_INDIRECTION_FORBIDDEN",
                "artifact locator became symbolic-link indirection before read",
            ) from exc
        if exc.errno in {errno.EACCES, errno.EPERM}:
            raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact file is not readable") from exc
        raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact file could not be opened") from exc

    hasher = hashlib.sha256()
    total = 0
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ArtifactEvidenceError(
                "ARTIFACT_NOT_REGULAR_FILE",
                "opened artifact is no longer a regular file",
            )
        while True:
            try:
                block = os.read(fd, chunk_size)
            except OSError as exc:
                raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact byte read failed") from exc
            if not block:
                break
            hasher.update(block)
            total += len(block)
        after = os.fstat(fd)
    finally:
        os.close(fd)

    stable_identity = (
        before.st_dev == after.st_dev
        and before.st_ino == after.st_ino
        and before.st_size == after.st_size
        and getattr(before, "st_mtime_ns", None) == getattr(after, "st_mtime_ns", None)
    )
    if not stable_identity or total != after.st_size:
        raise ArtifactEvidenceError(
            "ARTIFACT_MUTATED_DURING_READ",
            "artifact identity/size/mtime changed while bytes were being observed",
        )

    return ArtifactByteObservation(
        content_sha256=hasher.hexdigest(),
        byte_length=total,
        locator_fingerprint=_locator_fingerprint(path),
    )


def verify_distinct_artifact_pair(
    before_path: str | os.PathLike[str],
    after_path: str | os.PathLike[str],
    *,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
) -> ArtifactPairEvidence:
    """Re-read both actual artifacts and compare byte-content identity.

    This API intentionally accepts locators only, never receipts. Consumers that
    need byte authority must invoke this function in their trusted call path.
    """

    before = inspect_artifact_bytes(before_path, chunk_size=chunk_size)
    after = inspect_artifact_bytes(after_path, chunk_size=chunk_size)
    same_content = (
        before.content_sha256 == after.content_sha256
        and before.byte_length == after.byte_length
    )
    pair_payload = f"{before.content_identity}\n{after.content_identity}".encode("utf-8")
    return ArtifactPairEvidence(
        before=before,
        after=after,
        same_content=same_content,
        distinct_content_verified=not same_content,
        pair_digest=hashlib.sha256(pair_payload).hexdigest(),
    )
