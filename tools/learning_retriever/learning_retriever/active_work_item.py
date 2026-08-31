"""Public Active Work Item API.

Implementation lives in the fixed-GitHub trust-root module so local Git cannot
become an authority surface. This public wrapper adds two runtime invariants:
1) the canonical applied checkpoint must still exist as a live structured
   revision comment on the fixed source Issue;
2) callers can revalidate the same source revision immediately before the first
   downstream compiler use, closing the post-resolution remote TOCTOU window.
"""

from __future__ import annotations

from typing import Any

from . import _active_work_item_remote as _remote

ActiveWorkItemResolutionError = _remote.ActiveWorkItemResolutionError
CANONICAL_BRANCH = _remote.CANONICAL_BRANCH
CANONICAL_REPOSITORY = _remote.CANONICAL_REPOSITORY
CONTINUITY_PATH = _remote.CONTINUITY_PATH
PROJECT_INDEX_PATH = _remote.PROJECT_INDEX_PATH
WorkItemResolution = _remote.WorkItemResolution
apply_constraint_ledger = _remote.apply_constraint_ledger
build_work_item_context_packet = _remote.build_work_item_context_packet
is_continuation_request = _remote.is_continuation_request
load_active_work_item_state = _remote.load_active_work_item_state
validate_output_work_item = _remote.validate_output_work_item
validate_state_transition = _remote.validate_state_transition
validate_work_item_context_packet = _remote.validate_work_item_context_packet


def _validate_live_applied_checkpoint(
    resolution: WorkItemResolution,
    *,
    phase: str,
) -> dict[str, Any]:
    """Re-read the fixed source Issue and prove the applied checkpoint is live.

    Source-Issue comments remain revision/evidence trace only. This function does
    not infer story, map, asset, camera or prompt truth from comments; it only
    proves that canonical continuity's applied checkpoint identity still exists,
    still classifies as a structured revision checkpoint, and that no newer
    structured checkpoint has appeared.
    """
    if not resolution.resolution_required or not resolution.checkpoint_ref:
        return {
            "status": "NOT_REQUIRED",
            "phase": phase,
            "source_issue": resolution.source_issue,
            "applied_checkpoint_ref": resolution.checkpoint_ref,
        }

    try:
        issue = int(str(resolution.source_issue).strip())
        applied = int(str(resolution.checkpoint_ref).strip())
    except (TypeError, ValueError, AttributeError) as exc:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SOURCE_ISSUE_UNAVAILABLE",
            details={
                "reason": "non_numeric_issue_or_checkpoint",
                "phase": phase,
            },
        ) from exc

    try:
        comments = _remote._github_issue_comments(issue)
    except ActiveWorkItemResolutionError as exc:
        if exc.code == "WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE":
            raise ActiveWorkItemResolutionError(
                "WORK_ITEM_SOURCE_ISSUE_UNAVAILABLE",
                details={"source_issue": issue, "phase": phase, **exc.details},
            ) from exc
        raise

    by_id = {
        int(comment["id"]): comment
        for comment in comments
        if isinstance(comment.get("id"), int)
    }
    applied_comment = by_id.get(applied)
    if applied_comment is None:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SOURCE_APPLIED_CHECKPOINT_INVALID",
            details={
                "source_issue": issue,
                "latest_applied_checkpoint_ref": str(applied),
                "reason": "applied_checkpoint_comment_missing",
                "phase": phase,
            },
        )
    if not _remote._is_structured_revision_comment(applied_comment.get("body")):
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SOURCE_APPLIED_CHECKPOINT_INVALID",
            details={
                "source_issue": issue,
                "latest_applied_checkpoint_ref": str(applied),
                "reason": "applied_checkpoint_not_structured_revision",
                "phase": phase,
            },
        )

    structured_ids = sorted(
        int(comment["id"])
        for comment in comments
        if isinstance(comment.get("id"), int)
        and _remote._is_structured_revision_comment(comment.get("body"))
    )
    if not structured_ids:
        # Defensive; the applied comment was proven structured above, so this
        # branch should be unreachable unless the classification logic changes.
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SOURCE_APPLIED_CHECKPOINT_INVALID",
            details={
                "source_issue": issue,
                "latest_applied_checkpoint_ref": str(applied),
                "reason": "structured_revision_set_empty",
                "phase": phase,
            },
        )

    latest = structured_ids[-1]
    if latest > applied:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SOURCE_REVISION_AHEAD_OF_CANONICAL",
            details={
                "source_issue": issue,
                "latest_applied_checkpoint_ref": str(applied),
                "latest_source_checkpoint_ref": str(latest),
                "gate_status": "RECONCILE_REQUIRED",
                "phase": phase,
            },
        )

    observed_from_initial_resolution = str(
        resolution.latest_source_checkpoint_ref or ""
    ).strip()
    if observed_from_initial_resolution and observed_from_initial_resolution != str(latest):
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SOURCE_REVISION_CHANGED_AFTER_RESOLUTION",
            details={
                "source_issue": issue,
                "latest_applied_checkpoint_ref": str(applied),
                "initial_latest_source_checkpoint_ref": observed_from_initial_resolution,
                "revalidated_latest_source_checkpoint_ref": str(latest),
                "gate_status": "RECONCILE_REQUIRED",
                "phase": phase,
            },
        )

    return {
        "status": "PASS",
        "phase": phase,
        "source_issue": issue,
        "applied_checkpoint_ref": str(applied),
        "latest_structured_checkpoint_ref": str(latest),
        "applied_checkpoint_live": True,
        "applied_checkpoint_structured": True,
    }


def resolve_work_item(
    description: str,
    *,
    project_root: str | Any,
) -> WorkItemResolution:
    """Resolve through the fixed-GitHub authority and verify applied identity."""
    resolution = _remote.resolve_work_item(
        description,
        project_root=project_root,
    )
    _validate_live_applied_checkpoint(resolution, phase="post_resolution")
    return resolution


def revalidate_source_revision(resolution: WorkItemResolution) -> dict[str, Any]:
    """Final source-revision check immediately before downstream compiler use."""
    return _validate_live_applied_checkpoint(
        resolution,
        phase="pre_compiler",
    )


__all__ = [
    "ActiveWorkItemResolutionError",
    "CANONICAL_BRANCH",
    "CANONICAL_REPOSITORY",
    "CONTINUITY_PATH",
    "PROJECT_INDEX_PATH",
    "WorkItemResolution",
    "apply_constraint_ledger",
    "build_work_item_context_packet",
    "is_continuation_request",
    "load_active_work_item_state",
    "revalidate_source_revision",
    "resolve_work_item",
    "validate_output_work_item",
    "validate_state_transition",
    "validate_work_item_context_packet",
]
