"""Canonical natural-language directing entrypoint for Learning Smart Recall.

Continuation-style requests first pass the Active Work Item Resolution Gate.
After identity/freshness binding, the runtime reconstructs a compact complete
task description from the resolved WorkItemContext, then continues as Director
Feature Compiler -> director_route_index hard route -> existing LearningRetriever
semantic recall. Retrieval authority is unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .active_work_item import (
    ActiveWorkItemResolutionError,
    ExplicitTargetProvider,
    FreshnessProvider,
    build_work_item_context_packet,
    resolve_work_item,
)
from .feature_compiler import compile_retrieval_task
from .retriever import LearningRetriever


def _reconstruct_feature_input(
    user_description: str,
    packet: dict[str, Any] | None,
) -> tuple[str, bool]:
    """Create a pragmatically complete feature-compiler input for ellipsis.

    This is not a prompt sent to a video model. It is compact retrieval context
    so phrases like “重新导演上次那30秒” compile features from the resolved work
    item rather than from an empty anaphora shell.
    """
    if not packet:
        return user_description, False

    summary = str(packet.get("effective_state_summary") or "").strip()
    constraints = packet.get("constraints") or {}
    unresolved = [str(v).strip() for v in constraints.get("unresolved") or [] if str(v).strip()]
    locked = [str(v).strip() for v in constraints.get("locked") or [] if str(v).strip()]

    parts = [
        user_description.strip(),
        f"resolved_work_item={packet['work_item_id']}",
    ]
    if summary:
        parts.append(f"current_effective_state={summary}")
    if unresolved:
        parts.append("unresolved_failures=" + ", ".join(unresolved))
    if locked:
        # Locks are bounded to retrieval identity/mechanism cues. The full
        # Constraint Ledger remains in the packet and canonical continuity.
        parts.append("locked_mechanisms=" + ", ".join(locked[:12]))
    return "\n".join(parts), True


class DirectorLearningRuntime:
    """Bind directing requests to work-item identity and existing recall runtime.

    Providers are in-process orchestration capabilities. A freshness provider
    performs the real source-Issue checkpoint read. An explicit-target provider
    resolves a user-requested historical/non-active item from targeted canonical
    metadata. Serialized CLI/JSON inputs cannot synthesize either capability.
    """

    def __init__(
        self,
        project_root: str | Path,
        *,
        freshness_provider: FreshnessProvider | None = None,
        explicit_target_provider: ExplicitTargetProvider | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.retriever = LearningRetriever(self.project_root)
        self.freshness_provider = freshness_provider
        self.explicit_target_provider = explicit_target_provider

    def retrieve(
        self,
        description: str,
        *,
        task_id: str = "UNSPECIFIED_TASK",
        base_task: dict[str, Any] | None = None,
        top_k: int | None = None,
        expand: bool = False,
    ) -> dict[str, Any]:
        resolution = resolve_work_item(
            description,
            project_root=self.project_root,
            freshness_provider=self.freshness_provider,
            explicit_target_provider=self.explicit_target_provider,
        )

        merged_base = dict(base_task or {})
        work_item_packet: dict[str, Any] | None = None
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

        feature_input, reconstructed = _reconstruct_feature_input(
            description, work_item_packet
        )
        task = compile_retrieval_task(
            feature_input,
            task_id=task_id,
            base_task=merged_base,
            route_data=self.retriever.routes,
            strict=True,
        )
        result = self.retriever.retrieve(task, top_k=top_k, expand=expand, fail_closed=True)

        runtime_flow = ["active_work_item_resolution"]
        if reconstructed:
            runtime_flow.append("continuation_task_reconstruction")
        runtime_flow.extend(["director_feature_compiler", "hard_route", "semantic_recall"])

        result["canonical_runtime_receipt"] = {
            "entrypoint": "DirectorLearningRuntime.retrieve",
            "flow": runtime_flow,
            "active_work_item_gate_invoked": True,
            "active_work_item_resolution": resolution.as_dict(),
            "work_item_context_packet": work_item_packet,
            "continuation_task_reconstructed": reconstructed,
            "serialized_work_item_authority_accepted": False,
            "compiler_invoked": True,
            "work_item_resolution_authority": "10_运行时/active_work_item_resolution_gate.yaml",
            "route_authority": "10_运行时/director_route_index.yaml",
            "retriever_authority": "tools/learning_retriever/learning_retriever/retriever.py",
            "hard_routes": list(task.get("hard_routes") or []),
            "feature_compiler_receipt": dict(task.get("feature_compiler_receipt") or {}),
        }
        return result
