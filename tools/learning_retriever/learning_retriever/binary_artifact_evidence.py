"""Read-only binary artifact identity evidence for the EUSTIA AI-film runtime.

This candidate proves only what it actually reads. A locator, File ID, filename,
caller digest, serialized receipt, or generation label is never content identity.
The runtime opens ordinary files itself, streams their bytes through SHA-256, and
returns invocation-local evidence. Distinct byte content does NOT prove distinct
model generation events and does NOT register a formal project asset.

Security note: BYTE_VERIFIED is currently emitted only on platforms where Python
exposes POSIX component-by-component ``dir_fd`` traversal with ``O_NOFOLLOW`` and
mutation-sensitive ``ctime`` metadata. Other platforms fail closed before any
artifact filesystem access instead of silently weakening the locator contract.
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
_PLATFORM_SECURITY_ERROR = "ARTIFACT_PLATFORM_SECURITY_UNSUPPORTED"


@dataclass(frozen=True)
class ArtifactByteObservation:
    content_sha256: str
    byte_length: int
    locator_fingerprint: str
    locator_class: str = "local_path_invocation"
    byte_verification_state: str = "BYTE_VERIFIED"
    locator_security_state: str = "POSIX_COMPONENT_NOFOLLOW_VERIFIED"
    read_stability_state: str = "FD_DEV_INO_SIZE_MTIME_CTIME_STABLE"
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
            "locator_security_state": self.locator_security_state,
            "read_stability_state": self.read_stability_state,
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


def _raw_locator(value: Any) -> str:
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
    if "\x00" in raw:
        raise ArtifactEvidenceError("ARTIFACT_LOCATOR_INVALID", "artifact locator contains NUL")

    # Reject Windows UNC/device namespaces before any stat/open call. On Windows
    # these forms can trigger caller-directed SMB/device access with ambient auth.
    normalized_slashes = raw.replace("/", "\\")
    if normalized_slashes.startswith("\\\\"):
        raise ArtifactEvidenceError(
            "ARTIFACT_NETWORK_OR_DEVICE_LOCATOR_FORBIDDEN",
            "UNC/device/network-backed locator namespaces are not accepted",
        )
    return raw


def _locator_path(value: Any) -> Path:
    return Path(_raw_locator(value))


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


def _require_secure_platform() -> None:
    """Require a platform where the declared no-indirection contract is enforceable."""
    required_flags = all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY"))
    dir_fd_open = os.open in getattr(os, "supports_dir_fd", set())
    dir_fd_stat = os.stat in getattr(os, "supports_dir_fd", set())
    nofollow_stat = os.stat in getattr(os, "supports_follow_symlinks", set())
    if os.name != "posix" or not (required_flags and dir_fd_open and dir_fd_stat and nofollow_stat):
        raise ArtifactEvidenceError(
            _PLATFORM_SECURITY_ERROR,
            "secure component-by-component no-follow artifact inspection is unavailable on this platform",
        )


def _open_flags(*, directory: bool) -> int:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if directory:
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _lstat_at(parent_fd: int, component: str) -> os.stat_result:
    try:
        return os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise ArtifactEvidenceError("ARTIFACT_NOT_FOUND", "artifact path component does not exist") from exc
    except OSError as exc:
        if exc.errno in {errno.EACCES, errno.EPERM}:
            raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact path component is not inspectable") from exc
        raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact path component precheck failed") from exc


def _open_directory_component(parent_fd: int, component: str) -> int:
    observed = _lstat_at(parent_fd, component)
    if stat.S_ISLNK(observed.st_mode):
        raise ArtifactEvidenceError(
            "ARTIFACT_LOCATOR_INDIRECTION_FORBIDDEN",
            "symbolic-link path components are forbidden",
        )
    if not stat.S_ISDIR(observed.st_mode):
        raise ArtifactEvidenceError(
            "ARTIFACT_PATH_COMPONENT_INVALID",
            "intermediate artifact path component must be a real directory",
        )
    try:
        fd = os.open(component, _open_flags(directory=True), dir_fd=parent_fd)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise ArtifactEvidenceError(
                "ARTIFACT_LOCATOR_INDIRECTION_FORBIDDEN",
                "intermediate artifact path changed to indirection during traversal",
            ) from exc
        if exc.errno in {errno.EACCES, errno.EPERM}:
            raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact directory is not readable") from exc
        if exc.errno == errno.ENOENT:
            raise ArtifactEvidenceError("ARTIFACT_NOT_FOUND", "artifact path changed during traversal") from exc
        raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact directory could not be opened") from exc
    opened = os.fstat(fd)
    if not stat.S_ISDIR(opened.st_mode):
        os.close(fd)
        raise ArtifactEvidenceError(
            "ARTIFACT_LOCATOR_INDIRECTION_FORBIDDEN",
            "opened intermediate component is not a stable directory",
        )
    return fd


def _secure_open_regular_file(path: Path) -> int:
    """Open an absolute local path without following any symlink component."""
    _require_secure_platform()
    absolute = Path(os.path.abspath(os.fspath(path)))
    parts = absolute.parts
    if not parts or parts[0] != os.sep or len(parts) < 2:
        raise ArtifactEvidenceError("ARTIFACT_LOCATOR_INVALID", "artifact path cannot be normalized safely")

    directory_fds: list[int] = []
    try:
        current_fd = os.open(os.sep, _open_flags(directory=True))
        directory_fds.append(current_fd)
        for component in parts[1:-1]:
            if component in {"", ".", ".."}:
                raise ArtifactEvidenceError(
                    "ARTIFACT_LOCATOR_INVALID", "artifact path contains unsafe traversal component"
                )
            current_fd = _open_directory_component(current_fd, component)
            directory_fds.append(current_fd)

        final_component = parts[-1]
        if final_component in {"", ".", ".."}:
            raise ArtifactEvidenceError("ARTIFACT_LOCATOR_INVALID", "artifact filename is invalid")
        observed = _lstat_at(current_fd, final_component)
        if stat.S_ISLNK(observed.st_mode):
            raise ArtifactEvidenceError(
                "ARTIFACT_LOCATOR_INDIRECTION_FORBIDDEN",
                "symbolic-link artifact locators are forbidden",
            )
        if not stat.S_ISREG(observed.st_mode):
            raise ArtifactEvidenceError(
                "ARTIFACT_NOT_REGULAR_FILE",
                "artifact locator must identify a regular file",
            )
        try:
            fd = os.open(final_component, _open_flags(directory=False), dir_fd=current_fd)
        except OSError as exc:
            if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
                raise ArtifactEvidenceError(
                    "ARTIFACT_LOCATOR_INDIRECTION_FORBIDDEN",
                    "artifact locator changed to indirection before open",
                ) from exc
            if exc.errno == errno.ENOENT:
                raise ArtifactEvidenceError("ARTIFACT_NOT_FOUND", "artifact file disappeared before read") from exc
            if exc.errno in {errno.EACCES, errno.EPERM}:
                raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact file is not readable") from exc
            raise ArtifactEvidenceError("ARTIFACT_READ_FAILED", "artifact file could not be opened") from exc
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            os.close(fd)
            raise ArtifactEvidenceError(
                "ARTIFACT_NOT_REGULAR_FILE",
                "opened artifact is no longer a regular file",
            )
        return fd
    finally:
        for directory_fd in reversed(directory_fds):
            try:
                os.close(directory_fd)
            except OSError:
                pass


def _stable_stat_signature(observed: os.stat_result) -> tuple[int, ...]:
    mtime_ns = getattr(observed, "st_mtime_ns", None)
    ctime_ns = getattr(observed, "st_ctime_ns", None)
    if mtime_ns is None or ctime_ns is None:
        raise ArtifactEvidenceError(
            _PLATFORM_SECURITY_ERROR,
            "nanosecond mtime/ctime are required for verified byte observation",
        )
    return (
        int(observed.st_dev),
        int(observed.st_ino),
        int(stat.S_IFMT(observed.st_mode)),
        int(observed.st_size),
        int(mtime_ns),
        int(ctime_ns),
        int(getattr(observed, "st_nlink", 0)),
    )


def inspect_artifact_bytes(
    artifact_path: str | os.PathLike[str], *, chunk_size: int = _DEFAULT_CHUNK_SIZE
) -> ArtifactByteObservation:
    """Open and hash actual bytes read-only; never trust caller-supplied digest metadata."""

    path = _locator_path(artifact_path)
    chunk_size = _validated_chunk_size(chunk_size)
    fd = _secure_open_regular_file(path)

    hasher = hashlib.sha256()
    total = 0
    try:
        before = os.fstat(fd)
        before_signature = _stable_stat_signature(before)
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
        after_signature = _stable_stat_signature(after)
    finally:
        os.close(fd)

    if before_signature != after_signature or total != before.st_size or total != after.st_size:
        raise ArtifactEvidenceError(
            "ARTIFACT_MUTATED_DURING_READ",
            "artifact dev/inode/type/size/mtime/ctime/link state changed while bytes were observed",
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
