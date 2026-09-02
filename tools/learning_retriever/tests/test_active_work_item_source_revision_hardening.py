from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import learning_retriever.active_work_item as active
import learning_retriever.runtime as runtime_module
from learning_retriever.active_work_item import (
    ActiveWorkItemResolutionError,
    WorkItemResolution,
    revalidate_source_revision,
)


def _resolution(*, applied: str = "10", latest: str = "10") -> WorkItemResolution:
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
    return {"id": comment_id, "body": f"## {heading} — regression checkpoint\n\nOBSERVED: bounded evidence"}


def _evidence(comment_id: int) -> dict:
    return {"id": comment_id, "body": "## Evidence clarification\n\nThis is evidence only, not a revision checkpoint."}


class ActiveWorkItemSourceRevisionHardeningTests(unittest.TestCase):
    def test_public_resolve_rejects_missing_applied_checkpoint_identity(self):
        resolution = _resolution(applied="10", latest="10")
        with patch.object(active._remote, "resolve_work_item", return_value=resolution), patch.object(
            active._remote, "_github_issue_comments", return_value=[_structured(9)]
        ):
            with self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                active.resolve_work_item("继续上一版", project_root=".")
        self.assertEqual(ctx.exception.code, "WORK_ITEM_SOURCE_APPLIED_CHECKPOINT_INVALID")
        self.assertEqual(ctx.exception.details["reason"], "applied_checkpoint_comment_missing")

    def test_public_resolve_rejects_applied_checkpoint_edited_to_evidence_only(self):
        resolution = _resolution(applied="10", latest="10")
        with patch.object(active._remote, "resolve_work_item", return_value=resolution), patch.object(
            active._remote, "_github_issue_comments", return_value=[_evidence(10)]
        ):
            with self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                active.resolve_work_item("继续上一版", project_root=".")
        self.assertEqual(ctx.exception.code, "WORK_ITEM_SOURCE_APPLIED_CHECKPOINT_INVALID")
        self.assertEqual(ctx.exception.details["reason"], "applied_checkpoint_not_structured_revision")

    def test_public_resolve_rejects_fabricated_applied_id_ahead_of_real_structured_set(self):
        resolution = _resolution(applied="99", latest="99")
        with patch.object(active._remote, "resolve_work_item", return_value=resolution), patch.object(
            active._remote, "_github_issue_comments", return_value=[_structured(10), _structured(20, "Revision checkpoint")]
        ):
            with self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                active.resolve_work_item("继续上一版", project_root=".")
        self.assertEqual(ctx.exception.code, "WORK_ITEM_SOURCE_APPLIED_CHECKPOINT_INVALID")

    def test_pre_compiler_revalidation_rejects_new_structured_checkpoint(self):
        resolution = _resolution(applied="10", latest="10")
        with patch.object(active._remote, "_github_issue_comments", return_value=[_structured(10), _structured(11, "Revision checkpoint")]):
            with self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                revalidate_source_revision(resolution)
        self.assertEqual(ctx.exception.code, "WORK_ITEM_SOURCE_REVISION_AHEAD_OF_CANONICAL")
        self.assertEqual(ctx.exception.details["phase"], "pre_compiler")
        self.assertEqual(ctx.exception.details["latest_source_checkpoint_ref"], "11")

    def test_pre_compiler_revalidation_accepts_live_applied_checkpoint_and_evidence_only_tail(self):
        resolution = _resolution(applied="10", latest="10")
        with patch.object(active._remote, "_github_issue_comments", return_value=[_structured(10), _evidence(11)]):
            receipt = revalidate_source_revision(resolution)
        self.assertEqual(
            receipt,
            {
                "status": "PASS", "phase": "pre_compiler", "source_issue": 19,
                "applied_checkpoint_ref": "10", "latest_structured_checkpoint_ref": "10",
                "applied_checkpoint_live": True, "applied_checkpoint_structured": True,
            },
        )

    def test_runtime_aborts_before_feature_compiler_when_remote_revision_changes(self):
        """Explicit test seam preserves ordering without patching production globals."""
        resolution = _resolution(applied="10", latest="10")
        director_runtime = runtime_module.DirectorLearningRuntime.__new__(runtime_module.DirectorLearningRuntime)
        director_runtime.project_root = Path(".")
        director_runtime.retriever = SimpleNamespace(routes={})
        packet = {
            "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
            "effective_state_summary": "scarf traverse",
            "constraints": {"unresolved": [], "locked": []},
        }
        failure = ActiveWorkItemResolutionError(
            "WORK_ITEM_SOURCE_REVISION_AHEAD_OF_CANONICAL", details={"phase": "pre_compiler"}
        )
        compiler_called = {"value": False}

        def compiler(*_args, **_kwargs):
            compiler_called["value"] = True
            return {}

        with patch.object(runtime_module, "_verify_runtime_transitive_provenance", return_value=None), patch.object(
            runtime_module, "_CAPTURED_RESOLVE_WORK_ITEM", return_value=resolution
        ), patch.object(
            runtime_module, "_CAPTURED_BUILD_CONTEXT", return_value=packet
        ), patch.object(
            runtime_module, "_CAPTURED_REVALIDATE_SOURCE", side_effect=failure
        ), patch.object(
            runtime_module, "_CAPTURED_COMPILE_RETRIEVAL_TASK", side_effect=compiler
        ):
            with self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                director_runtime.retrieve("继续上一版")

        self.assertEqual(ctx.exception.code, "WORK_ITEM_SOURCE_REVISION_AHEAD_OF_CANONICAL")
        self.assertFalse(compiler_called["value"])

    def test_runtime_revalidates_immediately_before_compiler_use(self):
        """Explicit test seam verifies revalidate→compile ordering after provenance gate."""
        resolution = _resolution(applied="10", latest="10")
        director_runtime = runtime_module.DirectorLearningRuntime.__new__(runtime_module.DirectorLearningRuntime)
        director_runtime.project_root = Path(".")
        director_runtime.retriever = SimpleNamespace(routes={})
        packet = {
            "work_item_id": "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
            "effective_state_summary": "scarf traverse",
            "constraints": {"unresolved": [], "locked": []},
        }
        calls: list[str] = []

        def _revalidate(_resolution):
            calls.append("revalidate")
            return {
                "status": "PASS", "phase": "pre_compiler", "source_issue": 19,
                "applied_checkpoint_ref": "10", "latest_structured_checkpoint_ref": "10",
            }

        def _compile(*args, **kwargs):
            calls.append("compile")
            return {"hard_routes": [], "feature_compiler_receipt": {"status": "PASS"}}

        def _retrieve(_self, task, **_kwargs):
            return {"selected": [], "task": task}

        with patch.object(runtime_module, "_verify_runtime_transitive_provenance", return_value=None), patch.object(
            runtime_module, "_CAPTURED_RESOLVE_WORK_ITEM", return_value=resolution
        ), patch.object(
            runtime_module, "_CAPTURED_BUILD_CONTEXT", return_value=packet
        ), patch.object(
            runtime_module, "_CAPTURED_REVALIDATE_SOURCE", side_effect=_revalidate
        ), patch.object(
            runtime_module, "_CAPTURED_COMPILE_RETRIEVAL_TASK", side_effect=_compile
        ), patch.object(
            runtime_module, "_CAPTURED_RETRIEVER_RETRIEVE", side_effect=_retrieve
        ):
            result = director_runtime.retrieve("继续上一版")

        self.assertEqual(calls[:2], ["revalidate", "compile"])
        receipt = result["canonical_runtime_receipt"]
        self.assertEqual(receipt["source_revision_pre_compiler_revalidation"]["status"], "PASS")
        self.assertIn("source_revision_pre_compiler_revalidation", receipt["flow"])


if __name__ == "__main__":
    unittest.main()
