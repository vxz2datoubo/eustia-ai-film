from __future__ import annotations

from contextlib import ExitStack, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import learning_retriever.cli as cli_module
import learning_retriever.runtime as runtime_module
from learning_retriever.active_work_item import (
    ActiveWorkItemResolutionError,
    WorkItemResolution,
)
from learning_retriever.runtime import DirectorLearningRuntime

ROOT = Path(__file__).resolve().parents[3]
ACTIVE = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
STALE = "KAIM-HIGH-SEARCH-30S"


def resolution(*, required=True, work_item=ACTIVE):
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
        work_item,
        "active_work_item_pointer",
        "5454103847",
        True,
        gate_status="RESOLVED_VERIFIED",
        source_issue=19,
        latest_source_checkpoint_ref="5454103847",
        verification_basis="canonical_github_readback_verified_snapshot",
        snapshot_fingerprint="trusted-runtime-only",
        target_metadata={"work_item_id": work_item},
    )


def context_packet(work_item=ACTIVE):
    return {
        "packet_type": "WorkItemContext",
        "work_item_id": work_item,
        "freshness_verified": True,
        "verification_basis": "canonical_github_readback_verified_snapshot",
        "authority_boundary": "coordination_projection_only",
        "effective_state_summary": "Kaim scarf/clothesline traverse",
        "constraints": {"unresolved": [], "locked": []},
    }


def compiled_task(*args, **kwargs):
    base = dict(kwargs.get("base_task") or {})
    return {
        **base,
        "hard_routes": [],
        "feature_compiler_receipt": {"receipt_complete": True},
    }


class PreOutputScopeV2Tests(unittest.TestCase):
    def harness(self, *, resolved=None, revalidation=None):
        runtime = DirectorLearningRuntime(ROOT)
        resolved = resolved or resolution()
        stack = ExitStack()
        resolve_mock = stack.enter_context(
            patch.object(runtime_module, "resolve_work_item", return_value=resolved)
        )
        stack.enter_context(
            patch.object(
                runtime_module,
                "build_work_item_context_packet",
                return_value=context_packet(resolved.resolved_work_item_id or ACTIVE),
            )
        )
        revalidate_mock = stack.enter_context(
            patch.object(
                runtime_module,
                "revalidate_source_revision",
                side_effect=revalidation
                or [
                    {"status": "PASS", "phase": "pre_compiler"},
                    {"status": "PASS", "phase": "pre_output"},
                ],
            )
        )
        stack.enter_context(
            patch.object(runtime_module, "compile_retrieval_task", side_effect=compiled_task)
        )
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
        return runtime, stack, resolve_mock, revalidate_mock

    def test_retrieve_is_explicitly_non_executable(self):
        runtime, stack, _, _ = self.harness(
            revalidation=[{"status": "PASS", "phase": "pre_compiler"}]
        )
        with stack:
            result = runtime.retrieve("继续上一版")
        self.assertEqual(result["artifact_class"], "DIRECTOR_RETRIEVAL_ONLY")
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["executable"])
        self.assertFalse(result["deliverable"])
        self.assertTrue(result["requires_executable_output_builder"])

    def test_canonical_runtime_constructs_packet_with_loaded_identity(self):
        runtime, stack, resolve_mock, revalidate_mock = self.harness()
        with stack:
            result = runtime.build_executable_output(
                "继续上一版",
                output_content={"prompt": "execute scarf traverse"},
            )
        self.assertTrue(result["execution_authorized"])
        self.assertTrue(result["executable"])
        self.assertTrue(result["deliverable"])
        packet = result["output_packet"]
        self.assertEqual(packet["work_item_id"], ACTIVE)
        self.assertEqual(packet["payload"]["prompt"], "execute scarf traverse")
        self.assertEqual(packet["packet_constructor"], "DirectorLearningRuntime.build_executable_output")
        receipt = result["pre_output_receipt"]
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["resolved_work_item_id"], ACTIVE)
        self.assertEqual(receipt["loaded_work_item_id"], ACTIVE)
        self.assertEqual(receipt["output_work_item_id"], ACTIVE)
        self.assertTrue(receipt["packet_constructed_by_canonical_runtime"])
        self.assertFalse(receipt["caller_prebuilt_packet_accepted"])
        self.assertFalse(receipt["caller_builder_callback_accepted"])
        self.assertFalse(receipt["post_build_reresolution_performed"])
        self.assertEqual(resolve_mock.call_count, 1)
        self.assertEqual(revalidate_mock.call_count, 2)
        self.assertIs(
            revalidate_mock.call_args_list[0].args[0],
            revalidate_mock.call_args_list[1].args[0],
        )

    def test_caller_cannot_supply_work_item_identity_even_if_it_matches_current(self):
        runtime, stack, _, _ = self.harness()
        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.build_executable_output(
                "继续上一版",
                output_content={"work_item_id": ACTIVE, "prompt": "caller built packet"},
            )
        self.assertEqual(ctx.exception.code, "WORK_ITEM_OUTPUT_CALLER_AUTHORITY_FORBIDDEN")

    def test_preconstructed_stale_A_packet_relabelled_B_is_rejected_before_build(self):
        runtime, stack, resolve_mock, _ = self.harness()
        cached_under_a = {
            "work_item_id": STALE,
            "prompt": "payload captured earlier under stale work item A",
        }
        # Simulate the exact prior-review attack: cached packet is relabelled to the
        # current B before submission. Identity is still caller-controlled and forbidden.
        cached_under_a["work_item_id"] = ACTIVE
        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.build_executable_output(
                "继续上一版",
                output_content=cached_under_a,
            )
        self.assertEqual(ctx.exception.code, "WORK_ITEM_OUTPUT_CALLER_AUTHORITY_FORBIDDEN")
        # Rejection happens before canonical resolution because caller packet identity
        # is not a supported input surface at all.
        self.assertEqual(resolve_mock.call_count, 0)

    def test_nested_caller_validation_or_identity_claim_is_also_rejected(self):
        runtime, stack, _, _ = self.harness()
        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.build_executable_output(
                "继续上一版",
                output_content={
                    "prompt": "凯姆用围巾中段搭在固定晾衣绳上，从右向左横向移动",
                    "metadata": {
                        "validated": True,
                        "work_item_id": ACTIVE,
                        "validation_token": "caller-minted",
                    },
                },
            )
        self.assertEqual(ctx.exception.code, "WORK_ITEM_OUTPUT_CALLER_AUTHORITY_FORBIDDEN")

    def test_caller_builder_callback_surface_is_removed(self):
        runtime, stack, _, _ = self.harness()
        with stack, self.assertRaises(TypeError):
            runtime.build_executable_output(  # type: ignore[call-arg]
                "继续上一版",
                output_builder=lambda context: {"work_item_id": context.work_item_id},
            )

    def test_runtime_does_not_reresolve_if_current_resolver_would_change_after_build(self):
        runtime = DirectorLearningRuntime(ROOT)
        a = resolution(work_item=ACTIVE)
        b = resolution(work_item=STALE)
        with ExitStack() as stack:
            resolve_mock = stack.enter_context(
                patch.object(runtime_module, "resolve_work_item", side_effect=[a, b])
            )
            stack.enter_context(
                patch.object(runtime_module, "build_work_item_context_packet", return_value=context_packet(ACTIVE))
            )
            revalidate_mock = stack.enter_context(
                patch.object(
                    runtime_module,
                    "revalidate_source_revision",
                    side_effect=[
                        {"status": "PASS", "phase": "pre_compiler"},
                        {"status": "PASS", "phase": "pre_output"},
                    ],
                )
            )
            stack.enter_context(
                patch.object(runtime_module, "compile_retrieval_task", side_effect=compiled_task)
            )
            stack.enter_context(
                patch.object(
                    runtime.retriever,
                    "retrieve",
                    return_value={"selected_cases": [], "mandatory_recall_satisfied": True, "receipt_complete": True},
                )
            )
            result = runtime.build_executable_output(
                "继续上一版",
                output_content={"prompt": "A"},
            )
        self.assertTrue(result["executable"])
        self.assertEqual(result["output_packet"]["work_item_id"], ACTIVE)
        self.assertEqual(resolve_mock.call_count, 1)
        self.assertEqual(revalidate_mock.call_count, 2)

    def test_non_continuation_fast_path_needs_no_fake_work_item_identity(self):
        runtime, stack, resolve_mock, _ = self.harness(resolved=resolution(required=False))
        with stack:
            result = runtime.build_executable_output(
                "研究一个全新的独立镜头",
                output_content={"prompt": "new independent shot"},
            )
        self.assertTrue(result["executable"])
        self.assertEqual(result["pre_output_receipt"]["status"], "NOT_REQUIRED")
        self.assertIsNone(result["pre_output_receipt"]["output_work_item_id"])
        self.assertIsNone(result["output_packet"]["work_item_id"])
        self.assertEqual(resolve_mock.call_count, 1)

    def test_output_content_must_be_mapping(self):
        runtime, stack, _, _ = self.harness()
        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.build_executable_output(  # type: ignore[arg-type]
                "继续上一版",
                output_content="prompt",
            )
        self.assertEqual(ctx.exception.code, "WORK_ITEM_OUTPUT_CONTENT_INVALID")


class CLIExecutionConsumerTests(unittest.TestCase):
    def test_execution_packet_cli_passes_body_not_prebuilt_packet_or_builder(self):
        fake_runtime = MagicMock()
        fake_runtime.build_executable_output.return_value = {
            "status": "PASS",
            "artifact_class": "EXECUTABLE_OUTPUT_HANDOFF",
            "execution_authorized": True,
            "executable": True,
            "deliverable": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            packet_path = Path(tmp) / "packet.json"
            packet_path.write_text(json.dumps({"prompt": "test"}), encoding="utf-8")
            argv = [
                "prog",
                "--description",
                "继续上一版",
                "--execution-packet",
                str(packet_path),
            ]
            with patch.object(cli_module, "DirectorLearningRuntime", return_value=fake_runtime), patch.object(
                sys, "argv", argv
            ), redirect_stdout(StringIO()):
                code = cli_module.main()
        self.assertEqual(code, 0)
        fake_runtime.build_executable_output.assert_called_once()
        fake_runtime.retrieve.assert_not_called()
        kwargs = fake_runtime.build_executable_output.call_args.kwargs
        self.assertEqual(kwargs["output_content"], {"prompt": "test"})
        self.assertNotIn("output_builder", kwargs)

    def test_description_only_cli_remains_non_executable_retrieval_path(self):
        fake_runtime = MagicMock()
        fake_runtime.retrieve.return_value = {
            "status": "PASS",
            "artifact_class": "DIRECTOR_RETRIEVAL_ONLY",
            "execution_authorized": False,
            "executable": False,
            "deliverable": False,
        }
        argv = ["prog", "--description", "新镜头分析"]
        with patch.object(cli_module, "DirectorLearningRuntime", return_value=fake_runtime), patch.object(
            sys, "argv", argv
        ), redirect_stdout(StringIO()):
            code = cli_module.main()
        self.assertEqual(code, 0)
        fake_runtime.retrieve.assert_called_once()
        fake_runtime.build_executable_output.assert_not_called()


if __name__ == "__main__":
    unittest.main()
