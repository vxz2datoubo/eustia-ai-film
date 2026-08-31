from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import learning_retriever.active_work_item as active
import learning_retriever.runtime as runtime_module
from learning_retriever.active_work_item import (
    ActiveWorkItemResolutionError,
    WorkItemResolution,
    revalidate_source_revision,
)


def _resolution(
    *,
    applied: str = "10",
    latest: str = "10",
) -> WorkItemResolution:
    return WorkItemResolution(
        resolution_required=True,
        resolved_work_item_id="KAIM-SCARF-CLOTHESLINE-TRAVERSE",
        continuation_resolution_source="active_work_item_pointer",
        checkpoint_ref=applied,
        freshness_verified=True,
        gate_status="RESOLVED_VERIFIED",
        source_issue=19,
        latest_source_checkpoint_ref=latest,
        target_metadata={
            "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
            "current_effective_state_summary": "scarf traverse",
            "locked_constraints": [],
            "preserved_constraints": [],
            "revoked_constraints": [],
            "experimental_constraints": [],
            "unresolved_failures": [],
            "bound_media_or_reference_refs": [],
        },
        verification_basis="canonical_github_readback_verified_snapshot",
        snapshot_fingerprint="abc123",
    )


def _structured(comment_id: int, heading: str = "Micro Capture") -> dict:
    return {
        "id": comment_id,
        "body": f"## {heading} — regression checkpoint\n\nOBSERVED: bounded evidence",
    }


def _evidence(comment_id: int) -> dict:
    return {
        "id": comment_id,
        "body": "## Evidence clarification\n\nThis is evidence only, not a revision checkpoint.",
    }


def test_public_resolve_rejects_missing_applied_checkpoint_identity():
    resolution = _resolution(applied="10", latest="10")
    with patch.object(active._remote, "resolve_work_item", return_value=resolution), patch.object(
        active._remote,
        "_github_issue_comments",
        return_value=[_structured(9)],
    ):
        with pytest.raises(ActiveWorkItemResolutionError) as exc:
            active.resolve_work_item("继续上一版", project_root=".")
    assert exc.value.code == "WORK_ITEM_SOURCE_APPLIED_CHECKPOINT_INVALID"
    assert exc.value.details["reason"] == "applied_checkpoint_comment_missing"


def test_public_resolve_rejects_applied_checkpoint_edited_to_evidence_only():
    resolution = _resolution(applied="10", latest="10")
    with patch.object(active._remote, "resolve_work_item", return_value=resolution), patch.object(
        active._remote,
        "_github_issue_comments",
        return_value=[_evidence(10)],
    ):
        with pytest.raises(ActiveWorkItemResolutionError) as exc:
            active.resolve_work_item("继续上一版", project_root=".")
    assert exc.value.code == "WORK_ITEM_SOURCE_APPLIED_CHECKPOINT_INVALID"
    assert exc.value.details["reason"] == "applied_checkpoint_not_structured_revision"


def test_public_resolve_rejects_fabricated_applied_id_ahead_of_real_structured_set():
    resolution = _resolution(applied="99", latest="99")
    with patch.object(active._remote, "resolve_work_item", return_value=resolution), patch.object(
        active._remote,
        "_github_issue_comments",
        return_value=[_structured(10), _structured(20, "Revision checkpoint")],
    ):
        with pytest.raises(ActiveWorkItemResolutionError) as exc:
            active.resolve_work_item("继续上一版", project_root=".")
    assert exc.value.code == "WORK_ITEM_SOURCE_APPLIED_CHECKPOINT_INVALID"


def test_pre_compiler_revalidation_rejects_new_structured_checkpoint():
    resolution = _resolution(applied="10", latest="10")
    with patch.object(
        active._remote,
        "_github_issue_comments",
        return_value=[_structured(10), _structured(11, "Revision checkpoint")],
    ):
        with pytest.raises(ActiveWorkItemResolutionError) as exc:
            revalidate_source_revision(resolution)
    assert exc.value.code == "WORK_ITEM_SOURCE_REVISION_AHEAD_OF_CANONICAL"
    assert exc.value.details["phase"] == "pre_compiler"
    assert exc.value.details["latest_source_checkpoint_ref"] == "11"


def test_pre_compiler_revalidation_accepts_live_applied_checkpoint_and_evidence_only_tail():
    resolution = _resolution(applied="10", latest="10")
    with patch.object(
        active._remote,
        "_github_issue_comments",
        return_value=[_structured(10), _evidence(11)],
    ):
        receipt = revalidate_source_revision(resolution)
    assert receipt == {
        "status": "PASS",
        "phase": "pre_compiler",
        "source_issue": 19,
        "applied_checkpoint_ref": "10",
        "latest_structured_checkpoint_ref": "10",
        "applied_checkpoint_live": True,
        "applied_checkpoint_structured": True,
    }


def test_runtime_aborts_before_feature_compiler_when_remote_revision_changes():
    resolution = _resolution(applied="10", latest="10")
    director_runtime = runtime_module.DirectorLearningRuntime.__new__(
        runtime_module.DirectorLearningRuntime
    )
    director_runtime.project_root = Path(".")
    director_runtime.retriever = SimpleNamespace(routes={}, retrieve=lambda *a, **k: {})

    packet = {
        "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
        "effective_state_summary": "scarf traverse",
        "constraints": {"unresolved": [], "locked": []},
    }
    failure = ActiveWorkItemResolutionError(
        "WORK_ITEM_SOURCE_REVISION_AHEAD_OF_CANONICAL",
        details={"phase": "pre_compiler"},
    )

    with patch.object(runtime_module, "resolve_work_item", return_value=resolution), patch.object(
        runtime_module,
        "build_work_item_context_packet",
        return_value=packet,
    ), patch.object(
        runtime_module,
        "revalidate_source_revision",
        side_effect=failure,
    ), patch.object(runtime_module, "compile_retrieval_task") as compiler:
        with pytest.raises(ActiveWorkItemResolutionError) as exc:
            director_runtime.retrieve("继续上一版")

    assert exc.value.code == "WORK_ITEM_SOURCE_REVISION_AHEAD_OF_CANONICAL"
    compiler.assert_not_called()


def test_runtime_revalidates_immediately_before_compiler_use():
    resolution = _resolution(applied="10", latest="10")
    director_runtime = runtime_module.DirectorLearningRuntime.__new__(
        runtime_module.DirectorLearningRuntime
    )
    director_runtime.project_root = Path(".")
    director_runtime.retriever = SimpleNamespace(
        routes={},
        retrieve=lambda task, **kwargs: {"selected": [], "task": task},
    )
    packet = {
        "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
        "effective_state_summary": "scarf traverse",
        "constraints": {"unresolved": [], "locked": []},
    }
    calls: list[str] = []

    def _revalidate(_resolution):
        calls.append("revalidate")
        return {
            "status": "PASS",
            "phase": "pre_compiler",
            "source_issue": 19,
            "applied_checkpoint_ref": "10",
            "latest_structured_checkpoint_ref": "10",
        }

    def _compile(*args, **kwargs):
        calls.append("compile")
        return {
            "hard_routes": [],
            "feature_compiler_receipt": {"status": "PASS"},
        }

    with patch.object(runtime_module, "resolve_work_item", return_value=resolution), patch.object(
        runtime_module,
        "build_work_item_context_packet",
        return_value=packet,
    ), patch.object(runtime_module, "revalidate_source_revision", side_effect=_revalidate), patch.object(
        runtime_module,
        "compile_retrieval_task",
        side_effect=_compile,
    ):
        result = director_runtime.retrieve("继续上一版")

    assert calls[:2] == ["revalidate", "compile"]
    receipt = result["canonical_runtime_receipt"]
    assert receipt["source_revision_pre_compiler_revalidation"]["status"] == "PASS"
    assert "source_revision_pre_compiler_revalidation" in receipt["flow"]
