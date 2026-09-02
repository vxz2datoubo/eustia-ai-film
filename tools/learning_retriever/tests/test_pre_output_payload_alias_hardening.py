from __future__ import annotations

from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import learning_retriever.runtime as runtime_module
from learning_retriever.active_work_item import ActiveWorkItemResolutionError, WorkItemResolution
from learning_retriever.runtime import DirectorLearningRuntime

ROOT = Path(__file__).resolve().parents[3]
ACTIVE = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"


def _resolution() -> WorkItemResolution:
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


def _context_packet() -> dict:
    return {
        "packet_type": "WorkItemContext",
        "work_item_id": ACTIVE,
        "freshness_verified": True,
        "verification_basis": "canonical_github_readback_verified_snapshot",
        "authority_boundary": "coordination_projection_only",
        "effective_state_summary": "Kaim scarf/clothesline traverse",
        "constraints": {"unresolved": [], "locked": []},
    }


def _compiled_task(*args, **kwargs):
    base = dict(kwargs.get("base_task") or {})
    return {**base, "hard_routes": [], "feature_compiler_receipt": {"receipt_complete": True}}


def _runtime_harness():
    runtime = DirectorLearningRuntime(ROOT)
    stack = ExitStack()
    resolve_mock = stack.enter_context(patch.object(runtime_module, "resolve_work_item", return_value=_resolution()))
    stack.enter_context(patch.object(runtime_module, "build_work_item_context_packet", return_value=_context_packet()))
    stack.enter_context(
        patch.object(
            runtime_module,
            "revalidate_source_revision",
            side_effect=[
                {"status": "PASS", "phase": "pre_compiler"},
                {"status": "PASS", "phase": "pre_output"},
            ],
        )
    )
    stack.enter_context(patch.object(runtime_module, "compile_retrieval_task", side_effect=_compiled_task))
    stack.enter_context(
        patch.object(
            runtime.retriever,
            "retrieve",
            return_value={"selected_cases": [], "mandatory_recall_satisfied": True, "receipt_complete": True},
        )
    )
    return runtime, stack, resolve_mock


def _digest(payload):
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class PreOutputPayloadAliasHardeningTests(unittest.TestCase):
    def test_nested_caller_alias_mutation_cannot_change_validated_executable_packet(self):
        runtime, stack, _ = _runtime_harness()
        caller_steps = [{"action": "scarf traverse", "contacts": ["scarf", "clothesline"]}]
        caller_metadata = {"notes": ["preserve fixed clothesline"]}
        caller_content = {"steps": caller_steps, "metadata": caller_metadata}

        with stack:
            result = runtime.build_executable_output("继续上一版", output_content=caller_content)

        packet = result["output_packet"]
        digest_before = packet["payload_digest"]
        self.assertEqual(packet["payload"]["steps"][0]["action"], "scarf traverse")
        self.assertEqual(packet["payload"]["metadata"]["notes"], ["preserve fixed clothesline"])
        self.assertTrue(result["pre_output_receipt"]["caller_payload_aliases_detached"])
        self.assertEqual(digest_before, _digest(packet["payload"]))

        caller_steps[0]["action"] = "replace validated action after guard"
        caller_steps[0]["contacts"].clear()
        caller_metadata["notes"].append("late caller mutation")

        self.assertEqual(packet["payload"]["steps"][0]["action"], "scarf traverse")
        self.assertEqual(packet["payload"]["steps"][0]["contacts"], ["scarf", "clothesline"])
        self.assertEqual(packet["payload"]["metadata"]["notes"], ["preserve fixed clothesline"])
        self.assertEqual(packet["payload_digest"], digest_before)
        self.assertEqual(packet["payload_digest"], _digest(packet["payload"]))

    def test_non_json_object_is_rejected_before_canonical_resolution(self):
        runtime, stack, resolve_mock = _runtime_harness()

        class CallerObject:
            pass

        with stack, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
            runtime.build_executable_output(
                "继续上一版",
                output_content={"nested": {"unsafe": CallerObject()}},
            )
        self.assertEqual(ctx.exception.code, "WORK_ITEM_OUTPUT_CONTENT_NOT_SERIALIZABLE")
        self.assertEqual(resolve_mock.call_count, 0)


if __name__ == "__main__":
    unittest.main()
