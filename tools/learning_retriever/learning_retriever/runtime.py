"""Canonical natural-language directing entrypoint for Learning Smart Recall.

Continuation-style requests first pass the Active Work Item Resolution Gate.
The gate trusts only the repository-controlled canonical continuity snapshot;
callers cannot inject freshness or historical-target verification callbacks.
After work-item identity binding, the runtime reconstructs compact retrieval
context, performs one final fixed-source revision revalidation immediately
before Director Feature Compiler use, then continues through Director Feature
Compiler -> Hard Route -> existing LearningRetriever semantic recall.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .active_work_item import (
    ActiveWorkItemResolutionError,
    build_work_item_context_packet,
    revalidate_source_revision,
    resolve_work_item,
)
from .entity_semantics import load_canonical_character_terms
from .feature_compiler import FEATURE_KEYS, compile_retrieval_task
from .retriever import LearningRetriever


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
    """Bind directing requests to canonical work-item identity and existing recall."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.retriever = LearningRetriever(self.project_root)
        self.canonical_character_terms = load_canonical_character_terms(self.project_root)

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

        # The normal constructor caches the canonical character projection. Some
        # adversarial/runtime harnesses deliberately bypass __init__; those paths
        # must fail closed by rebuilding the same PROJECT_INDEX-bound projection,
        # not by assuming caller-supplied actor terms.
        canonical_character_terms = getattr(self, "canonical_character_terms", None)
        if canonical_character_terms is None:
            canonical_character_terms = load_canonical_character_terms(self.project_root)

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
            known_actor_terms=canonical_character_terms,
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
            "entity_semantics_authority": "PROJECT_INDEX.canonical.character_db",
            "canonical_character_term_count": len(canonical_character_terms),
            "compiled_features": {
                key: list(task.get(key) or []) for key in FEATURE_KEYS
            },
            "hard_routes": list(task.get("hard_routes") or []),
            "feature_compiler_receipt": dict(
                task.get("feature_compiler_receipt") or {}
            ),
        }
        return result
