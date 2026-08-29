"""Canonical natural-language directing entrypoint for Learning Smart Recall.

Flow is fixed as Director Feature Compiler -> director_route_index hard route ->
existing LearningRetriever semantic recall. LearningRetriever remains the
retrieval authority and learning_recall_index remains unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .feature_compiler import FEATURE_KEYS, compile_retrieval_task
from .retriever import LearningRetriever


class DirectorLearningRuntime:
    """Bound natural-language director tasks to the existing retrieval runtime."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.retriever = LearningRetriever(self.project_root)

    def retrieve(
        self,
        description: str,
        *,
        task_id: str = "UNSPECIFIED_TASK",
        base_task: dict[str, Any] | None = None,
        top_k: int | None = None,
        expand: bool = False,
    ) -> dict[str, Any]:
        task = compile_retrieval_task(
            description,
            task_id=task_id,
            base_task=base_task,
            route_data=self.retriever.routes,
            strict=True,
        )
        result = self.retriever.retrieve(task, top_k=top_k, expand=expand, fail_closed=True)
        result["canonical_runtime_receipt"] = {
            "entrypoint": "DirectorLearningRuntime.retrieve",
            "flow": ["director_feature_compiler", "hard_route", "semantic_recall"],
            "compiler_invoked": True,
            "route_authority": "10_运行时/director_route_index.yaml",
            "retriever_authority": "tools/learning_retriever/learning_retriever/retriever.py",
            "compiled_features": {key: list(task.get(key) or []) for key in FEATURE_KEYS},
            "hard_routes": list(task.get("hard_routes") or []),
            "feature_compiler_receipt": dict(task.get("feature_compiler_receipt") or {}),
        }
        return result
