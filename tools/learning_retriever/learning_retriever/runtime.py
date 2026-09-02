"""Canonical natural-language directing entrypoint for Learning Smart Recall.

Continuation-style requests first pass the Active Work Item Resolution Gate. The
runtime preserves the trusted in-process resolution/context identity through recall.
Retrieval results are explicitly non-executable artifacts.

The first executable output surface is ``build_executable_output``. It resolves and
loads context once, accepts only caller output *content* rather than a pre-built packet,
constructs the executable packet inside the canonical runtime from that trusted loaded
context, revalidates the SAME trusted resolution, and runs the existing output-scope
guard before executable/deliverable flags can exist. It never re-resolves after packet
construction and never accepts caller-minted work-item identity or validation receipts.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
from pathlib import Path
from typing import Any, Mapping
import json

from .active_work_item import (
    ActiveWorkItemResolutionError,
    WorkItemResolution,
    build_work_item_context_packet,
    revalidate_source_revision,
    resolve_work_item,
    validate_output_work_item,
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
_CALLER_IDENTITY_KEYS = {
    "work_item_id",
    "resolved_work_item_id",
    "loaded_work_item_id",
    "output_work_item_id",
    "work_item_resolution",
    "canonical_runtime_receipt",
    "pre_output_receipt",
    "build_provenance",
}
_FORBIDDEN_CALLER_PACKET_KEYS = _CALLER_SCOPE_BYPASS_KEYS | _CALLER_IDENTITY_KEYS


@dataclass(frozen=True)
class ExecutionBuildContext:
    """Internal non-authoritative projection used by canonical packet construction.

    The object is retained as a structured runtime diagnostic type, but it is no
    longer passed to caller code. Caller code cannot construct the executable packet.
    """

    work_item_id: str | None
    resolution_required: bool
    task_id: str
    authority_boundary: str = "canonical_runtime_internal_build_context"


def _stable_digest(value: Mapping[str, Any]) -> str:
    try:
        encoded = json.dumps(
            dict(value),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_OUTPUT_CONTENT_NOT_SERIALIZABLE",
            details={"reason": str(exc)},
        ) from exc
    return sha256(encoded).hexdigest()


def _detached_output_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
    """Create a JSON-safe deep snapshot with no caller-owned nested aliases.

    ``dict(output_content)`` is insufficient because nested dict/list instances remain
    shared with caller code. A caller retaining one of those aliases could mutate the
    executable packet *after* validation. This recursive projection accepts only the
    ordinary JSON value domain and constructs every mapping/list container anew.
    """

    def clone(node: Any, *, path: str) -> Any:
        if isinstance(node, Mapping):
            detached: dict[str, Any] = {}
            for raw_key, child in node.items():
                if not isinstance(raw_key, str):
                    raise ActiveWorkItemResolutionError(
                        "WORK_ITEM_OUTPUT_CONTENT_NOT_SERIALIZABLE",
                        details={"reason": "mapping_key_must_be_string", "path": path},
                    )
                detached[raw_key] = clone(child, path=f"{path}.{raw_key}")
            return detached
        if isinstance(node, (list, tuple)):
            return [clone(child, path=f"{path}[{index}]") for index, child in enumerate(node)]
        if node is None or isinstance(node, (str, bool, int)):
            return node
        if isinstance(node, float):
            if not math.isfinite(node):
                raise ActiveWorkItemResolutionError(
                    "WORK_ITEM_OUTPUT_CONTENT_NOT_SERIALIZABLE",
                    details={"reason": "non_finite_number", "path": path},
                )
            return node
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_OUTPUT_CONTENT_NOT_SERIALIZABLE",
            details={"reason": "unsupported_value_type", "path": path, "type": type(node).__name__},
        )

    snapshot = clone(value, path="payload")
    if not isinstance(snapshot, dict):
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_OUTPUT_CONTENT_INVALID",
            details={"reason": "output_content_must_be_mapping"},
        )
    return snapshot


def _collect_forbidden_keys(value: Any, *, path: str = "payload") -> list[str]:
    """Reject caller attempts to smuggle identity/validation authority into content."""
    found: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            child_path = f"{path}.{key}"
            if key in _FORBIDDEN_CALLER_PACKET_KEYS:
                found.append(child_path)
            found.extend(_collect_forbidden_keys(child, path=child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found.extend(_collect_forbidden_keys(child, path=f"{path}[{index}]"))
    return found


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
    """Bind directing requests and executable output to one trusted work-item context."""

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
        """Run canonical retrieval once and retain its trusted identity in-process."""
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
            loaded_work_item_id = str(work_item_packet["work_item_id"]).strip()

        feature_input, reconstructed = _reconstruct_feature_input(
            description, work_item_packet
        )

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

        result["artifact_class"] = "DIRECTOR_RETRIEVAL_ONLY"
        result["execution_authorized"] = False
        result["executable"] = False
        result["deliverable"] = False
        result["requires_executable_output_builder"] = True
        result["canonical_runtime_receipt"] = {
            "entrypoint": "DirectorLearningRuntime.retrieve",
            "flow": runtime_flow,
            "active_work_item_gate_invoked": True,
            "active_work_item_resolution": resolution.as_dict(),
            "source_revision_pre_compiler_revalidation": source_revision_revalidation,
            "work_item_context_packet": work_item_packet,
            "loaded_work_item_id": loaded_work_item_id,
            "continuation_task_reconstructed": reconstructed,
            "serialized_work_item_authority_accepted": False,
            "caller_verification_callback_supported": False,
            "compiler_invoked": True,
            "retrieval_result_is_executable": False,
            "executable_output_requires": "DirectorLearningRuntime.build_executable_output",
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
        """Return recall/directing context only. Never an executable output packet."""
        result, _, _ = self._retrieve_bound(
            description,
            task_id=task_id,
            base_task=base_task,
            top_k=top_k,
            expand=expand,
        )
        return result

    def build_executable_output(
        self,
        description: str,
        *,
        output_content: Mapping[str, Any],
        task_id: str = "UNSPECIFIED_TASK",
        base_task: dict[str, Any] | None = None,
        top_k: int | None = None,
        expand: bool = False,
    ) -> dict[str, Any]:
        """Construct and gate the first executable/deliverable output handoff.

        Caller code supplies only content. It cannot supply a pre-built packet,
        callback builder, work-item identity, validation receipt, or scope token.
        Canonical runtime resolves and loads context, then constructs the packet itself
        with the trusted loaded identity. Caller-owned nested containers are detached
        before validation so they cannot mutate the packet after the guard succeeds.
        """
        if not isinstance(output_content, Mapping):
            raise ActiveWorkItemResolutionError(
                "WORK_ITEM_OUTPUT_CONTENT_INVALID",
                details={"reason": "output_content_must_be_mapping"},
            )
        forbidden_paths = sorted(set(_collect_forbidden_keys(output_content)))
        if forbidden_paths:
            raise ActiveWorkItemResolutionError(
                "WORK_ITEM_OUTPUT_CALLER_AUTHORITY_FORBIDDEN",
                details={"forbidden_paths": forbidden_paths},
            )

        # Snapshot before any trusted work-item work is performed. The runtime never
        # stores caller-owned containers in an executable packet.
        payload = _detached_output_snapshot(output_content)

        retrieval_result, resolution, loaded_work_item_id = self._retrieve_bound(
            description,
            task_id=task_id,
            base_task=base_task,
            top_k=top_k,
            expand=expand,
        )

        build_context = ExecutionBuildContext(
            work_item_id=loaded_work_item_id,
            resolution_required=bool(resolution.resolution_required),
            task_id=task_id,
        )
        payload_digest = _stable_digest(payload)

        # Canonical runtime is the only packet constructor. Caller content is nested
        # below `payload` and cannot set packet identity or validation authority.
        packet = {
            "work_item_id": build_context.work_item_id,
            "task_id": build_context.task_id,
            "payload": payload,
            "payload_digest": payload_digest,
            "packet_constructor": "DirectorLearningRuntime.build_executable_output",
        }

        # Pre-output TOCTOU closure uses the SAME resolution object that existed before
        # canonical packet construction. There is intentionally no second resolve call.
        source_revision_pre_output = revalidate_source_revision(resolution)
        output_work_item_id = build_context.work_item_id
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

        pre_output_receipt = {
            "guard": "work_item_output_scope",
            "status": guard_status,
            "resolved_work_item_id": resolution.resolved_work_item_id,
            "loaded_work_item_id": loaded_work_item_id,
            "output_work_item_id": output_work_item_id,
            "upstream_resolution_basis": resolution.verification_basis,
            "same_in_process_resolution_used_for_retrieval_build_and_guard": True,
            "post_build_reresolution_performed": False,
            "source_revision_pre_output_revalidation": source_revision_pre_output,
            "caller_prebuilt_packet_accepted": False,
            "caller_builder_callback_accepted": False,
            "caller_scope_claims_accepted_as_authority": False,
            "caller_payload_aliases_detached": True,
            "packet_constructed_by_canonical_runtime": True,
            "canonical_payload_digest": payload_digest,
            "prompt_or_payload_semantics_inspected_by_guard": False,
            "authority_boundary": "canonical_packet_build_plus_pre_output_identity_gate",
        }

        retrieval_receipt = dict(
            retrieval_result.get("canonical_runtime_receipt") or {}
        )
        retrieval_receipt["flow"] = list(retrieval_receipt.get("flow") or []) + [
            "canonical_output_packet_construction",
            "source_revision_pre_output_revalidation",
            "work_item_output_scope_guard",
            "executable_output_handoff",
        ]
        retrieval_receipt["pre_output_work_item_scope"] = pre_output_receipt
        retrieval_result["canonical_runtime_receipt"] = retrieval_receipt

        return {
            "status": "PASS",
            "artifact_class": "EXECUTABLE_OUTPUT_HANDOFF",
            "execution_authorized": True,
            "executable": True,
            "deliverable": True,
            "output_packet": packet,
            "pre_output_receipt": pre_output_receipt,
            "retrieval_result": retrieval_result,
        }
