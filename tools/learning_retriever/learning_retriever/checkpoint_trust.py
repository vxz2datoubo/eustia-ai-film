"""Checkpoint-only trust adapter over the canonical Active Work Item v3 trust root.

This module introduces no repository/branch/story authority of its own. Every
remote read, identity classifier and materialization check delegates to the
already-canonical ``_active_work_item_remote`` implementation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from . import _active_work_item_remote as _remote


class CheckpointTrustError(_remote.ActiveWorkItemResolutionError):
    pass


def _error(code: str, **details: Any) -> CheckpointTrustError:
    return CheckpointTrustError(code, details=details or None)


def _full_sha(value: Any, *, code: str) -> str:
    sha = str(value or "").strip().casefold()
    if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
        raise _error(code, observed=value)
    return sha


@dataclass(frozen=True)
class TrustedCheckpointBaseline:
    """Provenance-bearing current baseline minted only by fixed GitHub readback."""

    canonical_sha: str
    state: dict[str, Any]
    continuity_markdown: str
    snapshot_fingerprint: str
    latest_structured_source_checkpoint: str
    materialization_commit_sha: str
    authority_boundary: str = "fixed_github_active_work_item_v3_projection"


@dataclass(frozen=True)
class FixedCommitContinuity:
    commit_sha: str
    continuity_markdown: str
    continuity_sha256: str
    authority_boundary: str = "fixed_repository_commit_readback_only"


def _issue_checkpoint_state(source_issue: Any, applied_ref: Any) -> tuple[str, str]:
    try:
        issue = int(str(source_issue).strip())
        applied = int(str(applied_ref).strip())
    except (TypeError, ValueError, AttributeError) as exc:
        raise _error("CHECKPOINT_SOURCE_IDENTITY_INVALID", source_issue=source_issue, checkpoint_ref=applied_ref) from exc

    comments = _remote._github_issue_comments(issue)
    by_id = {
        int(comment["id"]): comment
        for comment in comments
        if isinstance(comment.get("id"), int)
    }
    applied_comment = by_id.get(applied)
    if applied_comment is None:
        raise _error(
            "CHECKPOINT_SOURCE_COMMENT_MISSING",
            source_issue=issue,
            checkpoint_ref=str(applied),
        )
    if not _remote._is_structured_revision_comment(applied_comment.get("body")):
        raise _error(
            "CHECKPOINT_SOURCE_COMMENT_NOT_STRUCTURED_REVISION",
            source_issue=issue,
            checkpoint_ref=str(applied),
        )

    structured = sorted(
        int(comment["id"])
        for comment in comments
        if isinstance(comment.get("id"), int)
        and _remote._is_structured_revision_comment(comment.get("body"))
    )
    if not structured:
        raise _error("CHECKPOINT_SOURCE_STRUCTURED_SET_EMPTY", source_issue=issue)
    return str(applied), str(structured[-1])


def load_trusted_checkpoint_baseline(project_root: str | Path) -> TrustedCheckpointBaseline:
    """Read current canonical baseline with the same fixed-GitHub trust primitives as v3.

    Unlike normal continuation resolution, checkpoint compilation deliberately
    permits the source Issue to have newer structured revision comments: those
    are exactly what a checkpoint is reconciling. The *applied* canonical
    checkpoint must still exist and be structured.
    """
    branch = _remote._github_api_json(
        f"/repos/{_remote.CANONICAL_REPOSITORY}/branches/{_remote.CANONICAL_BRANCH}"
    )
    sha = _full_sha(
        ((branch.get("commit") or {}) if isinstance(branch, Mapping) else {}).get("sha"),
        code="CHECKPOINT_CANONICAL_MAIN_SHA_INVALID",
    )

    index_text = _remote._github_file_text(_remote.PROJECT_INDEX_PATH, sha)
    continuity_text = _remote._github_file_text(_remote.CONTINUITY_PATH, sha)
    try:
        index = yaml.safe_load(index_text) or {}
    except yaml.YAMLError as exc:
        raise _error("CHECKPOINT_CANONICAL_PROJECT_INDEX_INVALID") from exc
    if not isinstance(index, Mapping):
        raise _error("CHECKPOINT_CANONICAL_PROJECT_INDEX_INVALID")
    _remote._validate_project_index(index)
    state = _remote._extract_state_payload(continuity_text)

    root = Path(project_root)
    try:
        local_index = (root / _remote.PROJECT_INDEX_PATH).read_text(encoding="utf-8")
        local_continuity = (root / _remote.CONTINUITY_PATH).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise _error("CHECKPOINT_LOCAL_CANONICAL_PROJECTION_MISSING") from exc
    if _remote._normalize_repo_text(local_index) != _remote._normalize_repo_text(index_text):
        raise _error("CHECKPOINT_PROJECT_INDEX_DRIFT_FROM_FIXED_GITHUB")
    if _remote._normalize_repo_text(local_continuity) != _remote._normalize_repo_text(continuity_text):
        raise _error("CHECKPOINT_CONTINUITY_DRIFT_FROM_FIXED_GITHUB")

    materialization = _remote._remote_materialization(sha, state)
    applied = _remote._normalize_checkpoint(state.get("latest_applied_checkpoint_ref"))
    if applied is None:
        raise _error("CHECKPOINT_BASELINE_APPLIED_REF_MISSING")
    applied, latest = _issue_checkpoint_state(state.get("source_issue"), applied)

    receipt = {
        "repository": _remote.CANONICAL_REPOSITORY,
        "branch": _remote.CANONICAL_BRANCH,
        "canonical_sha": sha,
        "continuity_sha256": hashlib.sha256(continuity_text.encode("utf-8")).hexdigest(),
        "materialization": materialization,
        "applied_checkpoint": applied,
        "latest_structured_source_checkpoint": latest,
        "projection": _remote._snapshot_projection(state),
    }
    fingerprint = hashlib.sha256(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return TrustedCheckpointBaseline(
        canonical_sha=sha,
        state=dict(state),
        continuity_markdown=continuity_text,
        snapshot_fingerprint=fingerprint,
        latest_structured_source_checkpoint=latest,
        materialization_commit_sha=materialization,
    )


def validate_live_checkpoint(
    source_issue: Any,
    checkpoint_ref: Any,
    *,
    require_latest: bool,
) -> str:
    """Prove an exact fixed-Issue comment exists and is a structured revision checkpoint."""
    checkpoint, latest = _issue_checkpoint_state(source_issue, checkpoint_ref)
    if require_latest and checkpoint != latest:
        raise _error(
            "CHECKPOINT_SOURCE_REF_NOT_LATEST_STRUCTURED_REVISION",
            source_issue=source_issue,
            checkpoint_ref=checkpoint,
            latest_structured_checkpoint_ref=latest,
        )
    return checkpoint


def fetch_fixed_continuity_at_commit(commit_sha: str) -> FixedCommitContinuity:
    """Read continuity from an exact commit in the fixed canonical repository.

    This proves commit existence and document bytes only. It deliberately does
    not claim that the commit is on a governed branch/ref.
    """
    sha = _full_sha(commit_sha, code="CHECKPOINT_COMMIT_SHA_INVALID")
    commit = _remote._github_api_json(f"/repos/{_remote.CANONICAL_REPOSITORY}/commits/{sha}")
    if not isinstance(commit, Mapping) or str(commit.get("sha") or "").casefold() != sha:
        raise _error("CHECKPOINT_FIXED_REPOSITORY_COMMIT_MISSING", commit_sha=sha)
    markdown = _remote._github_file_text(_remote.CONTINUITY_PATH, sha)
    return FixedCommitContinuity(
        commit_sha=sha,
        continuity_markdown=markdown,
        continuity_sha256=hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
    )
