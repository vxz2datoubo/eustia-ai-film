"""Canonical natural-language directing entrypoint for Learning Smart Recall.

Continuation-style requests first pass the Active Work Item Resolution Gate.
The gate trusts only the repository-controlled canonical continuity snapshot;
callers cannot inject freshness or historical-target verification callbacks.
After work-item identity binding, the runtime reconstructs compact retrieval
context, performs fixed-source revision revalidation immediately before the
Director Feature Compiler, then continues through Director Feature Compiler ->
Hard Route -> existing LearningRetriever semantic recall.

The same runtime also owns the first executable/deliverable output handoff.  A
fully constructed downstream output packet is not marked executable until the
existing Active Work Item output-scope guard proves that resolved, loaded and
emitted work-item identities are identical.  This finalizer does not build,
rewrite or grade prompts; it only gates delivery/execution identity.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .active_work_item import (
    ActiveWorkItemResolutionError,
    WorkItemResolution,
    build_work_item_context_packet,
    revalidate_source_revision,
    resolve_work_item,
    validate_output_work_item,
    validate_work_item_context_packet,
)
from .feature_compiler import compile_retrieval_task
from .retriever import LearningRetriever


_CALLER_SCOPE_BYPASS_KEYS = {
    "validated",
    "already_validated",
    "validation_token",
    "validation_digest",
    "validation_receipt",
    "scope_guard_status",
    "work_item_scope_validated",
    "serialized_resolution",
    "active_work_item_resolution",
}


def _reconstruct_feature_input(
    user_description: str,
    packet: dict[str, Any] | None,
) -> tuple[str, bool]:
    """Create a pragmatically complete retrieval input for continuation ellipsis."""
    if not packet:
        return user_description, False

    summary = str(packet.get("effective_state_summary") or "").strip()
    constraints = packet.get("constraints") or {}
    unresolved = [
        str(v).strip()
        for v in constraints.get("unresolved") or []
        if str(v).strip()
    ]
    locked = [
        str(v).strip()
        for v in constraints.get("locked") or []
        if str(v).strip()
    ]

    parts = [
        user_description.strip(),
        f"resolved_work_item={packet['work_item_id']}",
    ]
    if summary:
        parts.append(f"current_effective_state={summary}")
    if unresolved:
        parts.append("unresolved_failures=" + ", ".join(unresolved))
    if locked:
        parts.append("locked_mechanisms=" + ", ".join(locked[:12]))
    return "\n".join(parts), True


class DirectorLearningRuntime:
    """Bind directing requests and executable output to canonical work-item identity."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.retriever = LearningRetriever(self.project_root)

    def _retrieve_bound(
        self,
        description: str,
        *,
        task_id: str = "UNSPECIFIED_TASK",
        base_task: dict[str, Any] | None = None,
        top_k: int | None = None,
        expand: bool = False,
    ) -> tuple[dict[str, Any], WorkItemResolution, str | None]:
        """Run the canonical retrieval path and retain trusted identity in-process."""
        resolution = resolve_work_item(
            description,
            project_root=self.project_root,
        )

        merged_base = dict(base_task or {})
        work_item_packet: dict[str, Any] | None = None
        loaded_work_item_id: str | None = None
        if resolution.resolved_work_item_id:
            existing = str(merged_base.get("work_item_id") or "").strip()
            if existing and existing != resolution.resolved_work_item_id:
                raise ActiveWorkItemResolutionError(
                    "WORK_ITEM_INPUT_SCOPE_MISMATCH",
                    details={
                        "resolved_work_item_id": resolution.resolved_work_item_id,
                        "base_task_work_item_id": existing,
                    },
                )
            merged_base["work_item_id"] = resolution.resolved_work_item_id
            work_item_packet = build_work_item_context_packet(
                self.project_root, resolution
            )
            validate_work_item_context_packet(
                work_item_packet,
                expected_work_item_id=resolution.resolved_work_item_id,
            )
            loaded_work_item_id = str(work_item_packet["work_item_id"]).strip()

        feature_input, reconstructed = _reconstruct_feature_input(
            description, work_item_packet
        )

        # Close the remote source-revision TOCTOU window at the first downstream
        # compiler boundary. If the source Issue changed after initial resolution,
        # fail closed before Director Feature Compiler can observe stale context.
        source_revision_revalidation = revalidate_source_revision(resolution)

        task = compile_retrieval_task(
            feature_input,
            task_id=task_id,
            base_task=merged_base,
            route_data=self.retriever.routes,
            strict=True,
        )
        result = self.retriever.retrieve(
            task, top_k=top_k, expand=expand, fail_closed=True
        )

        runtime_flow = ["active_work_item_resolution"]
        if reconstructed:
            runtime_flow.append("continuation_task_reconstruction")
        if source_revision_revalidation.get("status") != "NOT_REQUIRED":
            runtime_flow.append("source_revision_pre_compiler_revalidation")
        runtime_flow.extend(
            ["director_feature_compiler", "hard_route", "semantic_recall"]
        )

        result["canonical_runtime_receipt"] = {
            "entrypoint": "DirectorLearningRuntime.retrieve",
            "flow": runtime_flow,
            "active_work_item_gate_invoked": True,
            "active_work_item_resolution": resolution.as_dict(),
            "source_revision_pre_compiler_revalidation": source_revision_revalidation,
            "work_item_context_packet": work_item_packet,
            "continuation_task_reconstructed": reconstructed,
            "serialized_work_item_authority_accepted": False,
            "caller_verification_callback_supported": False,
            "compiler_invoked": True,
            "work_item_resolution_authority": (
                "07_连续性与生产状态/连续性与当前生产状态.md#ACTIVE_WORK_ITEM_STATE"
            ),
            "work_item_resolution_contract": (
                "10_运行时/active_work_item_resolution_gate.yaml"
            ),
            "route_authority": "10_运行时/director_route_index.yaml",
            "retriever_authority": (
                "tools/learning_retriever/learning_retriever/retriever.py"
            ),
            "hard_routes": list(task.get("hard_routes") or []),
            "feature_compiler_receipt": dict(
                task.get("feature_compiler_receipt") or {}
            ),
        }
        return result, resolution, loaded_work_item_id

    def retrieve(
        self,
        description: str,
        *,
        task_id: str = "UNSPECIFIED_TASK",
        base_task: dict[str, Any] | None = None,
        top_k: int | None = None,
        expand: bool = False,
    ) -> dict[str, Any]:
        result, _, _ = self._retrieve_bound(
            description,
            task_id=task_id,
            base_task=base_task,
            top_k=top_k,
            expand=expand,
        )
        return result

    def finalize_execution_output(
        self,
        description: str,
        *,
        output_packet: Mapping[str, Any],
        task_id: str = "UNSPECIFIED_TASK",
        base_task: dict[str, Any] | None = None,
        top_k: int | None = None,
        expand: bool = False,
    ) -> dict[str, Any]:
        """Gate a constructed downstream packet before it becomes executable.

        ``output_packet`` is treated as already constructed content.  This method
        does not alter prompt text, model syntax, camera, story, assets or learning
        state.  It only reuses the canonical directing/retrieval path, preserves the
        trusted in-process resolution object, revalidates source revision freshness
        once more at pre-output, and then invokes ``validate_output_work_item``.

        Caller-supplied booleans, digests, receipts or serialized resolutions are
        neither authority nor a bypass.  They are reported as ignored claims while
        the real guard still executes from the trusted upstream resolution/context.
        """
        if not isinstance(output_packet, Mapping):
            raise ActiveWorkItemResolutionError(
                "WORK_ITEM_OUTPUT_PACKET_INVALID",
                details={"reason": "output_packet_must_be_mapping"},
            )

        packet = dict(output_packet)
        caller_claims = sorted(set(packet).intersection(_CALLER_SCOPE_BYPASS_KEYS))

        retrieval_result, resolution, loaded_work_item_id = self._retrieve_bound(
            description,
            task_id=task_id,
            base_task=base_task,
            top_k=top_k,
            expand=expand,
        )

        # A revision can arrive after Feature Compiler/recall but before delivery.
        # Revalidate the same fixed source Issue here instead of trusting a prior
        # serialized receipt or local state.
        source_revision_pre_output = revalidate_source_revision(resolution)

        output_work_item_id = str(packet.get("work_item_id") or "").strip() or None
        guard = validate_output_work_item(
            resolution,
            loaded_work_item_id=loaded_work_item_id,
            output_work_item_id=output_work_item_id,
        )

        guard_status = str(guard.get("status") or "").strip()
        if guard_status not in {"PASS", "NOT_REQUIRED"}:
            raise ActiveWorkItemResolutionError(
                "WORK_ITEM_OUTPUT_SCOPE_MISMATCH",
                details={"guard_status": guard_status or None},
            )

        receipt = {
            "guard": "work_item_output_scope",
            "status": guard_status,
            "resolved_work_item_id": resolution.resolved_work_item_id,
            "loaded_work_item_id": loaded_work_item_id,
            "output_work_item_id": output_work_item_id,
            "upstream_resolution_basis": resolution.verification_basis,
            "source_revision_pre_output_revalidation": source_revision_pre_output,
            "caller_scope_claims_present": caller_claims,
            "caller_scope_claims_accepted_as_authority": False,
            "prompt_or_payload_mutated_by_guard": False,
            "authority_boundary": "pre_output_identity_gate_only",
        }

        retrieval_receipt = dict(
            retrieval_result.get("canonical_runtime_receipt") or {}
        )
        retrieval_receipt["flow"] = list(retrieval_receipt.get("flow") or []) + [
            "source_revision_pre_output_revalidation",
            "work_item_output_scope_guard",
            "executable_output_handoff",
        ]
        retrieval_receipt["pre_output_work_item_scope"] = receipt
        retrieval_result["canonical_runtime_receipt"] = retrieval_receipt

        return {
            "status": "PASS",
            "executable": True,
            "deliverable": True,
            "output_packet": packet,
            "pre_output_receipt": receipt,
            "retrieval_result": retrieval_result,
        }
