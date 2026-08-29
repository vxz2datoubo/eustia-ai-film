"""Canonical natural-language directing entrypoint for Learning Smart Recall.

Continuation-style requests first pass the Active Work Item Resolution Gate.
After identity/freshness binding, flow continues as Director Feature Compiler ->
director_route_index hard route -> existing LearningRetriever semantic recall.
LearningRetriever remains retrieval authority and work-item resolution does not
become story, continuity, or learning authority.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .active_work_item import (
    ActiveWorkItemResolutionError,
    FreshnessProvider,
    build_work_item_context_packet,
    resolve_work_item,
)
from .feature_compiler import compile_retrieval_task
from .retriever import LearningRetriever


class DirectorLearningRuntime:
    """Bind directing requests to work-item identity and existing recall runtime.

    A freshness provider is an in-process orchestration capability. It is expected
    to perform the real source-Issue read and return its structured checkpoint
    receipt. CLI/JSON inputs cannot synthesize this capability.
    """

    def __init__(
        self,
        project_root: str | Path,
        *,
        freshness_provider: FreshnessProvider | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.retriever = LearningRetriever(self.project_root)
        self.freshness_provider = freshness_provider

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

        task = compile_retrieval_task(
            description,
            task_id=task_id,
            base_task=merged_base,
            route_data=self.retriever.routes,
            strict=True,
        )
        result = self.retriever.retrieve(task, top_k=top_k, expand=expand, fail_closed=True)
        result["canonical_runtime_receipt"] = {
            "entrypoint": "DirectorLearningRuntime.retrieve",
            "flow": [
                "active_work_item_resolution",
                "director_feature_compiler",
                "hard_route",
                "semantic_recall",
            ],
            "active_work_item_gate_invoked": True,
            "active_work_item_resolution": resolution.as_dict(),
            "work_item_context_packet": work_item_packet,
            "serialized_freshness_authority_accepted": False,
            "compiler_invoked": True,
            "work_item_resolution_authority": "10_运行时/active_work_item_resolution_gate.yaml",
            "route_authority": "10_运行时/director_route_index.yaml",
            "retriever_authority": "tools/learning_retriever/learning_retriever/retriever.py",
            "hard_routes": list(task.get("hard_routes") or []),
            "feature_compiler_receipt": dict(task.get("feature_compiler_receipt") or {}),
        }
        return result
