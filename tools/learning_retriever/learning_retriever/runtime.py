"""Canonical natural-language directing entrypoint for Learning Smart Recall.

Continuation-style requests first pass the Active Work Item Resolution Gate. Before
any authority-bearing receipt/context can be consumed, this module revalidates the
exact transitive runtime dependencies captured at import time. Same-process mutation
of resolver/context/revalidation/compiler/retriever bindings therefore fails closed.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any
import sys

from .active_work_item import (
    ActiveWorkItemResolutionError,
    build_work_item_context_packet,
    revalidate_source_revision,
    resolve_work_item,
)
from .feature_compiler import compile_retrieval_task
from .retriever import LearningRetriever


def _module_source_fingerprint(obj: Any) -> tuple[Path, str]:
    module_name = getattr(obj, "__module__", "")
    module = sys.modules.get(module_name)
    source = getattr(module, "__file__", None)
    if not source:
        raise RuntimeError(f"runtime dependency source unavailable: {module_name}")
    path = Path(source).resolve()
    return path, sha256(path.read_bytes()).hexdigest()


_CAPTURED_RESOLVE_WORK_ITEM = resolve_work_item
_CAPTURED_BUILD_CONTEXT = build_work_item_context_packet
_CAPTURED_REVALIDATE_SOURCE = revalidate_source_revision
_CAPTURED_COMPILE_RETRIEVAL_TASK = compile_retrieval_task
_CAPTURED_LEARNING_RETRIEVER = LearningRetriever
_CAPTURED_RETRIEVER_INIT = LearningRetriever.__init__
_CAPTURED_RETRIEVER_RETRIEVE = LearningRetriever.retrieve
_CAPTURED_DEPENDENCY_SOURCES = {
    "resolve_work_item": _module_source_fingerprint(resolve_work_item),
    "build_work_item_context_packet": _module_source_fingerprint(build_work_item_context_packet),
    "revalidate_source_revision": _module_source_fingerprint(revalidate_source_revision),
    "compile_retrieval_task": _module_source_fingerprint(compile_retrieval_task),
    "LearningRetriever": _module_source_fingerprint(LearningRetriever),
}
_THIS_PACKAGE_DIR = Path(__file__).resolve().parent


def _runtime_provenance_error(reason: str) -> ActiveWorkItemResolutionError:
    return ActiveWorkItemResolutionError(
        "WORK_ITEM_RUNTIME_PROVENANCE_SUBSTITUTED",
        details={"reason": reason},
    )


def _verify_runtime_transitive_provenance() -> None:
    """Fail before trusted resolution if any consumed runtime dependency drifted."""
    if resolve_work_item is not _CAPTURED_RESOLVE_WORK_ITEM:
        raise _runtime_provenance_error("resolve_work_item_identity")
    if build_work_item_context_packet is not _CAPTURED_BUILD_CONTEXT:
        raise _runtime_provenance_error("build_work_item_context_packet_identity")
    if revalidate_source_revision is not _CAPTURED_REVALIDATE_SOURCE:
        raise _runtime_provenance_error("revalidate_source_revision_identity")
    if compile_retrieval_task is not _CAPTURED_COMPILE_RETRIEVAL_TASK:
        raise _runtime_provenance_error("compile_retrieval_task_identity")
    if LearningRetriever is not _CAPTURED_LEARNING_RETRIEVER:
        raise _runtime_provenance_error("LearningRetriever_class_identity")
    if LearningRetriever.__init__ is not _CAPTURED_RETRIEVER_INIT:
        raise _runtime_provenance_error("LearningRetriever_init_identity")
    if LearningRetriever.retrieve is not _CAPTURED_RETRIEVER_RETRIEVE:
        raise _runtime_provenance_error("LearningRetriever_retrieve_identity")

    for name, obj in {
        "resolve_work_item": resolve_work_item,
        "build_work_item_context_packet": build_work_item_context_packet,
        "revalidate_source_revision": revalidate_source_revision,
        "compile_retrieval_task": compile_retrieval_task,
        "LearningRetriever": LearningRetriever,
    }.items():
        try:
            current_path, current_digest = _module_source_fingerprint(obj)
        except Exception as exc:
            raise _runtime_provenance_error(f"{name}_source_unavailable") from exc
        expected_path, expected_digest = _CAPTURED_DEPENDENCY_SOURCES[name]
        if current_path != expected_path or current_path.parent != _THIS_PACKAGE_DIR:
            raise _runtime_provenance_error(f"{name}_source_path")
        if current_digest != expected_digest:
            raise _runtime_provenance_error(f"{name}_source_digest")


def _reconstruct_feature_input(user_description: str, packet: dict[str, Any] | None) -> tuple[str, bool]:
    if not packet:
        return user_description, False
    summary = str(packet.get("effective_state_summary") or "").strip()
    constraints = packet.get("constraints") or {}
    unresolved = [str(v).strip() for v in constraints.get("unresolved") or [] if str(v).strip()]
    locked = [str(v).strip() for v in constraints.get("locked") or [] if str(v).strip()]
    parts = [user_description.strip(), f"resolved_work_item={packet['work_item_id']}"]
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
        _verify_runtime_transitive_provenance()
        self.project_root = Path(project_root)
        self.retriever = _CAPTURED_LEARNING_RETRIEVER(self.project_root)

    def retrieve(
        self,
        description: str,
        *,
        task_id: str = "UNSPECIFIED_TASK",
        base_task: dict[str, Any] | None = None,
        top_k: int | None = None,
        expand: bool = False,
    ) -> dict[str, Any]:
        # This must remain the first semantic action. No canonical receipt/context is
        # consumed before the captured dependency universe is revalidated.
        _verify_runtime_transitive_provenance()
        resolution = _CAPTURED_RESOLVE_WORK_ITEM(description, project_root=self.project_root)

        merged_base = dict(base_task or {})
        work_item_packet: dict[str, Any] | None = None
        if resolution.resolved_work_item_id:
            existing = str(merged_base.get("work_item_id") or "").strip()
            if existing and existing != resolution.resolved_work_item_id:
                raise ActiveWorkItemResolutionError(
                    "WORK_ITEM_INPUT_SCOPE_MISMATCH",
                    details={"resolved_work_item_id": resolution.resolved_work_item_id, "base_task_work_item_id": existing},
                )
            merged_base["work_item_id"] = resolution.resolved_work_item_id
            work_item_packet = _CAPTURED_BUILD_CONTEXT(self.project_root, resolution)

        feature_input, reconstructed = _reconstruct_feature_input(description, work_item_packet)
        source_revision_revalidation = _CAPTURED_REVALIDATE_SOURCE(resolution)
        task = _CAPTURED_COMPILE_RETRIEVAL_TASK(
            feature_input, task_id=task_id, base_task=merged_base,
            route_data=self.retriever.routes, strict=True,
        )
        result = _CAPTURED_RETRIEVER_RETRIEVE(
            self.retriever, task, top_k=top_k, expand=expand, fail_closed=True
        )

        runtime_flow = ["active_work_item_resolution"]
        if reconstructed:
            runtime_flow.append("continuation_task_reconstruction")
        if source_revision_revalidation.get("status") != "NOT_REQUIRED":
            runtime_flow.append("source_revision_pre_compiler_revalidation")
        runtime_flow.extend(["director_feature_compiler", "hard_route", "semantic_recall"])
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
            "transitive_runtime_provenance_verified_before_authority_consumption": True,
            "work_item_resolution_authority": "07_连续性与生产状态/连续性与当前生产状态.md#ACTIVE_WORK_ITEM_STATE",
            "work_item_resolution_contract": "10_运行时/active_work_item_resolution_gate.yaml",
            "route_authority": "10_运行时/director_route_index.yaml",
            "retriever_authority": "tools/learning_retriever/learning_retriever/retriever.py",
            "hard_routes": list(task.get("hard_routes") or []),
            "feature_compiler_receipt": dict(task.get("feature_compiler_receipt") or {}),
        }
        return result
