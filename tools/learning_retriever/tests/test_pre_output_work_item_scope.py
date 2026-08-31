from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

import learning_retriever.runtime as runtime_module
from learning_retriever.active_work_item import (
    ActiveWorkItemResolutionError,
    WorkItemResolution,
)
from learning_retriever.runtime import DirectorLearningRuntime


ROOT = Path(__file__).resolve().parents[3]
ACTIVE = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
STALE = "KAIM-HIGH-SEARCH-30S"


def _resolution(*, required: bool = True) -> WorkItemResolution:
    if not required:
        return WorkItemResolution(
            False,
            None,
            "not_required",
            None,
            False,
            gate_status="NOT_REQUIRED",
            verification_basis="not_required",
        )
    return WorkItemResolution(
        True,
        ACTIVE,
        "active_work_item_pointer",
        "5454103847",
        True,
        gate_status="RESOLVED_VERIFIED",
        source_issue=19,
        latest_source_checkpoint_ref="5454103847",
        verification_basis="canonical_github_readback_verified_snapshot",
        snapshot_fingerprint="trusted-runtime-only",
        target_metadata={"work_item_id": ACTIVE},
    )


def _packet() -> dict:
    return {
        "packet_type": "WorkItemContext",
        "work_item_id": ACTIVE,
        "freshness_verified": True,
        "verification_basis": "canonical_github_readback_verified_snapshot",
        "authority_boundary": "coordination_projection_only",
        "effective_state_summary": "Kaim scarf/clothesline traverse",
        "constraints": {"unresolved": [], "locked": []},
    }


def _task(*args, **kwargs) -> dict:
    base = dict(kwargs.get("base_task") or {})
    return {
        **base,
        "hard_routes": [],
        "feature_compiler_receipt": {"receipt_complete": True},
    }


class PreOutputWorkItemScopeTests(unittest.TestCase):
    def _runtime_harness(
        self,
        *,
        resolution: WorkItemResolution | None = None,
        revalidation_side_effect=None,
    ):
        runtime = DirectorLearningRuntime(ROOT)
        resolution = resolution or _resolution()
        stack = ExitStack()
        stack.enter_context(
            patch.object(runtime_module, "resolve_work_item", return_value=resolution)
        )
        stack.enter_context(
            patch.object(runtime_module, "build_work_item_context_packet", return_value=_packet())
        )
        if revalidation_side_effect is None:
            stack.enter_context(
                patch.object(
                    runtime_module,
                    "revalidate_source_revision",
                    return_value={"status": "PASS", "phase": "test"},
                )
            )
        else:
            stack.enter_context(
                patch.object(
                    runtime_module,
                    "revalidate_source_revision",
                    side_effect=revalidation_side_effect,
                )
            )
        stack.enter_context(patch.object(runtime_module, "compile_retrieval_task", side_effect=_task))
        stack.enter_context(
            patch.object(
                runtime.retriever,
                "retrieve",
                return_value={
                    "selected_cases": [],
                    "mandatory_recall_satisfied": True,
                    "receipt_complete": True,
                },
            )
        )
        return runtime, stack

    def test_matching_resolved_loaded_and_output_identity_is_executable(self):
        runtime, stack = self._runtime_harness()
        with stack:
            result = runtime.finalize_execution_output(
                "继续上一版",
                output_packet={"work_item_id": ACTIVE, "prompt": "execute scarf traverse"},
            )
        self.assertTrue(result["executable"])
        self.assertTrue(result["deliverable"])
        self.assertEqual(result["pre_output_receipt"]["status"], "PASS")
        self.assertEqual(result["pre_output_receipt"]["resolved_work_item_id"], ACTIVE)
        self.assertEqual(result["pre_output_receipt"]["loaded_work_item_id"], ACTIVE)
        self.assertEqual(result["pre_output_receipt"]["output_work_item_id"], ACTIVE)

    def test_stale_output_identity_fails_even_when_loaded_context_is_correct(self):
        runtime, stack = self._runtime_harness()
        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.finalize_execution_output(
                "继续上一版",
                output_packet={"work_item_id": STALE, "prompt": "right scene wording"},
            )
        self.assertEqual(ctx.exception.code, "WORK_ITEM_OUTPUT_SCOPE_MISMATCH")

    def test_stale_loaded_context_fails_before_output_can_be_deliverable(self):
        runtime, stack = self._runtime_harness()
        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.finalize_execution_output(
                "继续上一版",
                base_task={"work_item_id": STALE},
                output_packet={"work_item_id": ACTIVE, "prompt": "execute scarf traverse"},
            )
        self.assertEqual(ctx.exception.code, "WORK_ITEM_INPUT_SCOPE_MISMATCH")

    def test_missing_output_identity_fails_closed_for_continuation(self):
        runtime, stack = self._runtime_harness()
        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.finalize_execution_output(
                "继续上一版",
                output_packet={"prompt": "execute scarf traverse"},
            )
        self.assertEqual(ctx.exception.code, "WORK_ITEM_OUTPUT_SCOPE_MISMATCH")

    def test_prompt_semantics_cannot_override_stale_metadata_identity(self):
        runtime, stack = self._runtime_harness()
        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.finalize_execution_output(
                "继续上一版",
                output_packet={
                    "work_item_id": STALE,
                    "prompt": (
                        "凯姆用围巾中段搭在固定晾衣绳上，双手握住两端，"
                        "从画面右侧横向移动到左侧。"
                    ),
                },
            )
        self.assertEqual(ctx.exception.code, "WORK_ITEM_OUTPUT_SCOPE_MISMATCH")

    def test_caller_validation_claims_do_not_bypass_real_scope_guard(self):
        runtime, stack = self._runtime_harness()
        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.finalize_execution_output(
                "继续上一版",
                output_packet={
                    "work_item_id": STALE,
                    "prompt": "execute scarf traverse",
                    "validated": True,
                    "validation_token": "caller-minted",
                    "serialized_resolution": {"resolved_work_item_id": ACTIVE},
                },
            )
        self.assertEqual(ctx.exception.code, "WORK_ITEM_OUTPUT_SCOPE_MISMATCH")

    def test_matching_packet_with_caller_claims_passes_only_real_guard_and_reports_ignored_claims(self):
        runtime, stack = self._runtime_harness()
        with stack:
            result = runtime.finalize_execution_output(
                "继续上一版",
                output_packet={
                    "work_item_id": ACTIVE,
                    "prompt": "execute scarf traverse",
                    "validated": True,
                    "validation_digest": "caller-minted",
                },
            )
        receipt = result["pre_output_receipt"]
        self.assertEqual(receipt["status"], "PASS")
        self.assertFalse(receipt["caller_scope_claims_accepted_as_authority"])
        self.assertEqual(
            receipt["caller_scope_claims_present"],
            ["validated", "validation_digest"],
        )

    def test_non_continuation_fast_path_does_not_require_work_item_identity(self):
        runtime, stack = self._runtime_harness(resolution=_resolution(required=False))
        with stack:
            result = runtime.finalize_execution_output(
                "分析一个独立的新镜头",
                output_packet={"prompt": "standalone shot"},
            )
        self.assertEqual(result["pre_output_receipt"]["status"], "NOT_REQUIRED")
        self.assertTrue(result["deliverable"])

    def test_source_revision_change_after_retrieval_blocks_pre_output_delivery(self):
        runtime, stack = self._runtime_harness(
            revalidation_side_effect=[
                {"status": "PASS", "phase": "pre_compiler"},
                ActiveWorkItemResolutionError(
                    "WORK_ITEM_SOURCE_REVISION_CHANGED_AFTER_RESOLUTION",
                    details={"gate_status": "RECONCILE_REQUIRED"},
                ),
            ]
        )
        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.finalize_execution_output(
                "继续上一版",
                output_packet={"work_item_id": ACTIVE, "prompt": "execute scarf traverse"},
            )
        self.assertEqual(
            ctx.exception.code,
            "WORK_ITEM_SOURCE_REVISION_CHANGED_AFTER_RESOLUTION",
        )

    def test_guard_does_not_mutate_prompt_or_payload(self):
        runtime, stack = self._runtime_harness()
        original = {
            "work_item_id": ACTIVE,
            "prompt": "exact model prompt",
            "payload": {"camera": "locked", "references": ["asset://kaim"]},
        }
        expected = deepcopy(original)
        with stack:
            result = runtime.finalize_execution_output(
                "继续上一版",
                output_packet=original,
            )
        self.assertEqual(original, expected)
        self.assertEqual(result["output_packet"], expected)
        self.assertFalse(result["pre_output_receipt"]["prompt_or_payload_mutated_by_guard"])


if __name__ == "__main__":
    unittest.main()
