"""Active work-item resolution gate for continuation-style directing requests.

The gate binds conversational continuation to a concrete production work item
before Director Feature Compiler runs. It does not choose screenplay facts,
mutate continuity, or become a second project authority.

Two facts cannot be minted by serialized JSON/CLI input:
1. source-Issue freshness;
2. an explicit switch to a non-active historical work item.
A host orchestrator that can perform the real canonical/source reads supplies
in-process provider callables for those operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import yaml


CONTINUITY_PATH = Path("07_连续性与生产状态/连续性与当前生产状态.md")
STATE_BEGIN = "<!-- ACTIVE_WORK_ITEM_STATE_BEGIN -->"
STATE_END = "<!-- ACTIVE_WORK_ITEM_STATE_END -->"

STRONG_CONTINUATION_SIGNALS = (
    "上次",
    "刚才",
    "那30秒",
    "那段",
    "那个镜头",
    "之前那个",
    "下一镜",
    "继续下面剧情",
    "重新导演那",
    "重新做那个",
)

CONTINUATION_VERBS = ("继续", "接着")
DISCOURSE_OBJECTS = (
    "上一版",
    "上个版本",
    "上次",
    "刚才",
    "那30秒",
    "这30秒",
    "那个30秒",
    "那段",
    "这段",
    "那个镜头",
    "这个镜头",
    "当前镜头",
    "之前那个",
    "下一镜",
    "下一个镜头",
    "下面剧情",
    "后面剧情",
    "这个版本",
    "那一版",
)

# These words explicitly contrast the current pointer with an older/non-active
# referent. When they occur in a continuation request, using the active pointer
# without resolving the historical target would be unsafe.
NONACTIVE_REFERENT_HINTS = (
    "之前",
    "以前",
    "更早",
    "旧的",
    "旧版",
    "前一个",
    "前面那个",
)

REQUIRED_STATE_FIELDS = (
    "work_item_id",
    "status",
    "source_issue",
    "baseline_checkpoint_ref",
    "latest_applied_checkpoint_ref",
    "story_scope_ref",
    "current_effective_state_summary",
    "locked_constraints",
    "preserved_constraints",
    "revoked_constraints",
    "experimental_constraints",
    "unresolved_failures",
    "checkpoint_writeback_status",
)

ALLOWED_TRANSITIONS = {
    "UNRESOLVED": {"RESOLVED_UNVERIFIED"},
    "RESOLVED_UNVERIFIED": {"RECONCILE_REQUIRED", "RESOLVED_VERIFIED"},
    "RECONCILE_REQUIRED": {"RESOLVED_VERIFIED"},
    "RESOLVED_VERIFIED": {"ACTIVE_REVISION", "CHECKPOINTED"},
    "ACTIVE_REVISION": {"CHECKPOINTED", "CLOSED"},
    "CHECKPOINTED": {"ACTIVE_REVISION", "CLOSED"},
    "CLOSED": set(),
}

FreshnessProvider = Callable[[dict[str, Any]], dict[str, Any]]
ExplicitTargetProvider = Callable[[str, dict[str, Any]], dict[str, Any] | None]


class ActiveWorkItemResolutionError(ValueError):
    """Fail-closed error raised before director feature compilation."""

    def __init__(self, code: str, *, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.details = details or {}
        super().__init__(code)


@dataclass(frozen=True)
class WorkItemResolution:
    resolution_required: bool
    resolved_work_item_id: str | None
    continuation_resolution_source: str
    checkpoint_ref: str | None
    freshness_verified: bool
    conflicts: tuple[str, ...] = field(default_factory=tuple)
    gate_status: str = "NOT_REQUIRED"
    source_issue: str | int | None = None
    latest_source_checkpoint_ref: str | None = None
    question_required: bool = False
    question: str | None = None
    target_metadata: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "resolution_required": self.resolution_required,
            "resolved_work_item_id": self.resolved_work_item_id,
            "continuation_resolution_source": self.continuation_resolution_source,
            "checkpoint_ref": self.checkpoint_ref,
            "freshness_verified": self.freshness_verified,
            "conflicts": list(self.conflicts),
            "gate_status": self.gate_status,
            "source_issue": self.source_issue,
            "latest_source_checkpoint_ref": self.latest_source_checkpoint_ref,
            "question_required": self.question_required,
            "question": self.question,
            "target_metadata": dict(self.target_metadata or {}),
        }


def _normalize_discourse_text(description: str) -> str:
    return " ".join(description.casefold().split()).strip()


def _continuation_verb_targets_discourse_object(text: str, verb: str) -> bool:
    search_from = 0
    while True:
        hit = text.find(verb, search_from)
        if hit < 0:
            return False
        tail = text[hit + len(verb): hit + len(verb) + 18].lstrip(" ，,：:。；;！!？?")
        if any(tail.startswith(obj) for obj in DISCOURSE_OBJECTS):
            return True
        search_from = hit + len(verb)


def is_continuation_request(description: str) -> bool:
    """Detect discourse continuation without confusing it with scene action."""
    if not isinstance(description, str):
        return False
    normalized = _normalize_discourse_text(description)
    if not normalized:
        return False

    if any(signal.casefold() in normalized for signal in STRONG_CONTINUATION_SIGNALS):
        return True

    compact = normalized.strip(" ，,：:。；;！!？?")
    if compact in CONTINUATION_VERBS:
        return True

    return any(
        _continuation_verb_targets_discourse_object(normalized, verb)
        for verb in CONTINUATION_VERBS
    )


def _explicit_nonactive_hint(description: str) -> bool:
    normalized = _normalize_discourse_text(description)
    return any(hint in normalized for hint in NONACTIVE_REFERENT_HINTS)


def _normalize_checkpoint(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _extract_state_payload(markdown: str) -> dict[str, Any]:
    start = markdown.find(STATE_BEGIN)
    end = markdown.find(STATE_END)
    if start < 0 or end < 0 or end <= start:
        raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_MISSING")

    payload = markdown[start + len(STATE_BEGIN):end].strip()
    if payload.startswith("```yaml"):
        payload = payload[len("```yaml"):]
    elif payload.startswith("```yml"):
        payload = payload[len("```yml"):]
    elif payload.startswith("```"):
        payload = payload[len("```"):]
    payload = payload.strip()
    if payload.endswith("```"):
        payload = payload[:-3].strip()

    try:
        parsed = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        raise ActiveWorkItemResolutionError(
            "ACTIVE_WORK_ITEM_STATE_INVALID", details={"yaml_error": str(exc)}
        ) from exc

    if not isinstance(parsed, dict) or not isinstance(parsed.get("active_work_item"), dict):
        raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_INVALID")
    state = dict(parsed["active_work_item"])

    missing = [field for field in REQUIRED_STATE_FIELDS if field not in state]
    if missing:
        raise ActiveWorkItemResolutionError(
            "ACTIVE_WORK_ITEM_STATE_INVALID", details={"missing_fields": missing}
        )

    if not str(state.get("work_item_id") or "").strip():
        raise ActiveWorkItemResolutionError(
            "ACTIVE_WORK_ITEM_STATE_INVALID", details={"field": "work_item_id"}
        )

    for key in (
        "locked_constraints",
        "preserved_constraints",
        "revoked_constraints",
        "experimental_constraints",
        "unresolved_failures",
    ):
        if not isinstance(state.get(key), list):
            raise ActiveWorkItemResolutionError(
                "ACTIVE_WORK_ITEM_STATE_INVALID", details={"field": key}
            )
    return state


def load_active_work_item_state(project_root: str | Path) -> dict[str, Any]:
    path = Path(project_root) / CONTINUITY_PATH
    try:
        markdown = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_MISSING") from exc
    return _extract_state_payload(markdown)


def _verify_active_freshness(
    state: dict[str, Any],
    freshness_provider: FreshnessProvider | None,
) -> tuple[bool, str | None]:
    source_issue = state.get("source_issue")
    checkpoint = _normalize_checkpoint(state.get("latest_applied_checkpoint_ref"))
    checkpoint_status = str(state.get("checkpoint_writeback_status") or "").strip().casefold()

    if source_issue in (None, "", 0, "0"):
        if checkpoint_status != "verified":
            raise ActiveWorkItemResolutionError(
                "WORK_ITEM_FRESHNESS_UNVERIFIED",
                details={"reason": "snapshot_writeback_not_verified"},
            )
        return True, checkpoint

    if freshness_provider is None:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_FRESHNESS_PROVIDER_REQUIRED",
            details={"source_issue": source_issue},
        )

    receipt = freshness_provider(dict(state))
    if not isinstance(receipt, dict):
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_FRESHNESS_UNVERIFIED",
            details={"source_issue": source_issue, "reason": "invalid_freshness_receipt"},
        )

    receipt_issue = receipt.get("source_issue")
    if str(receipt_issue) != str(source_issue) or receipt.get("source_issue_accessible") is not True:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_FRESHNESS_UNVERIFIED",
            details={"source_issue": source_issue, "reason": "source_issue_not_verified_accessible"},
        )

    latest = _normalize_checkpoint(receipt.get("latest_source_checkpoint_ref"))
    if latest is None:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_FRESHNESS_UNVERIFIED",
            details={"source_issue": source_issue, "reason": "latest_source_checkpoint_ref_missing"},
        )
    if latest != checkpoint:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_CHECKPOINT_RECONCILE_REQUIRED",
            details={
                "source_issue": source_issue,
                "latest_applied_checkpoint_ref": checkpoint,
                "latest_source_checkpoint_ref": latest,
            },
        )
    return True, latest


def _resolve_nonactive_target(
    description: str,
    state: dict[str, Any],
    explicit_target_provider: ExplicitTargetProvider | None,
) -> WorkItemResolution | None:
    if not _explicit_nonactive_hint(description):
        return None
    if explicit_target_provider is None:
        raise ActiveWorkItemResolutionError(
            "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
            details={"active_work_item_id": state.get("work_item_id")},
        )

    candidate = explicit_target_provider(description, dict(state))
    if not isinstance(candidate, dict) or candidate.get("verified") is not True:
        raise ActiveWorkItemResolutionError(
            "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
            details={"reason": "target_provider_did_not_return_verified_candidate"},
        )

    target_id = str(candidate.get("work_item_id") or "").strip()
    if not target_id or target_id == str(state.get("work_item_id") or "").strip():
        raise ActiveWorkItemResolutionError(
            "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
            details={"reason": "nonactive_candidate_missing_or_equals_active"},
        )

    return WorkItemResolution(
        resolution_required=True,
        resolved_work_item_id=target_id,
        continuation_resolution_source="user_explicit_trusted_target_resolution",
        checkpoint_ref=_normalize_checkpoint(candidate.get("checkpoint_ref")),
        freshness_verified=True,
        gate_status="RESOLVED_VERIFIED",
        source_issue=candidate.get("source_issue"),
        latest_source_checkpoint_ref=_normalize_checkpoint(candidate.get("checkpoint_ref")),
        target_metadata={
            key: value
            for key, value in candidate.items()
            if key != "verified"
        },
    )


def resolve_work_item(
    description: str,
    *,
    project_root: str | Path,
    freshness_provider: FreshnessProvider | None = None,
    explicit_target_provider: ExplicitTargetProvider | None = None,
) -> WorkItemResolution:
    """Resolve work-item identity and freshness before downstream compilation."""
    if not is_continuation_request(description):
        return WorkItemResolution(
            resolution_required=False,
            resolved_work_item_id=None,
            continuation_resolution_source="not_required",
            checkpoint_ref=None,
            freshness_verified=False,
            gate_status="NOT_REQUIRED",
        )

    state = load_active_work_item_state(project_root)
    explicit = _resolve_nonactive_target(description, state, explicit_target_provider)
    if explicit is not None:
        return explicit

    active_id = str(state["work_item_id"]).strip()
    freshness_verified, latest = _verify_active_freshness(state, freshness_provider)
    return WorkItemResolution(
        resolution_required=True,
        resolved_work_item_id=active_id,
        continuation_resolution_source="active_work_item_pointer",
        checkpoint_ref=_normalize_checkpoint(state.get("latest_applied_checkpoint_ref")),
        freshness_verified=freshness_verified,
        gate_status="RESOLVED_VERIFIED",
        source_issue=state.get("source_issue"),
        latest_source_checkpoint_ref=latest,
        target_metadata=None,
    )


def build_work_item_context_packet(
    project_root: str | Path,
    resolution: WorkItemResolution,
) -> dict[str, Any]:
    """Build a compact structured packet for specialist handoffs.

    This is a coordination projection only. Each department must still read the
    canonical source for facts it owns.
    """
    if not resolution.resolution_required or not resolution.resolved_work_item_id:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_REQUIRES_RESOLUTION")

    state = load_active_work_item_state(project_root)
    active_id = str(state["work_item_id"]).strip()
    if resolution.resolved_work_item_id == active_id:
        target = state
    else:
        target = dict(resolution.target_metadata or {})
        if str(target.get("work_item_id") or "").strip() != resolution.resolved_work_item_id:
            raise ActiveWorkItemResolutionError(
                "WORK_ITEM_CONTEXT_PACKET_TARGET_NOT_FOUND",
                details={"work_item_id": resolution.resolved_work_item_id},
            )

    return {
        "schema_version": "1.0",
        "packet_type": "WorkItemContext",
        "work_item_id": resolution.resolved_work_item_id,
        "resolution_source": resolution.continuation_resolution_source,
        "checkpoint_ref": resolution.checkpoint_ref,
        "freshness_verified": resolution.freshness_verified,
        "source_issue": resolution.source_issue,
        "story_scope_ref": target.get("story_scope_ref"),
        "effective_state_summary": target.get(
            "current_effective_state_summary", target.get("summary")
        ),
        "constraints": {
            "locked": list(target.get("locked_constraints") or []),
            "preserved": list(target.get("preserved_constraints") or []),
            "revoked": list(target.get("revoked_constraints") or []),
            "experimental": list(target.get("experimental_constraints") or []),
            "unresolved": list(target.get("unresolved_failures") or []),
        },
        "bound_media_or_reference_refs": list(target.get("bound_media_or_reference_refs") or []),
        "authority_refs": {
            "project_registry": "PROJECT_INDEX.yaml",
            "continuity": str(CONTINUITY_PATH),
            "director_method": "01_AI电影系统/AI电影系统.md",
            "screenplay": "03_剧本与改编/当前改编剧本.md",
        },
        "authority_boundary": "coordination_projection_only",
    }


def validate_work_item_context_packet(
    packet: dict[str, Any], *, expected_work_item_id: str
) -> bool:
    if not isinstance(packet, dict) or packet.get("packet_type") != "WorkItemContext":
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_INVALID")
    observed = str(packet.get("work_item_id") or "").strip()
    expected = str(expected_work_item_id or "").strip()
    if not observed or observed != expected:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_CONTEXT_PACKET_MISMATCH",
            details={"expected_work_item_id": expected or None, "observed_work_item_id": observed or None},
        )
    if packet.get("freshness_verified") is not True:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_STALE")
    if packet.get("authority_boundary") != "coordination_projection_only":
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_INVALID")
    return True


def validate_output_work_item(
    resolution: WorkItemResolution | dict[str, Any],
    *,
    loaded_work_item_id: str | None,
    output_work_item_id: str | None,
) -> dict[str, Any]:
    """Pre-output guard: resolved, loaded and emitted work-item identity must match."""
    if isinstance(resolution, WorkItemResolution):
        receipt = resolution.as_dict()
    else:
        receipt = dict(resolution)

    if not receipt.get("resolution_required"):
        return {"status": "NOT_REQUIRED", "matched": True}

    resolved = str(receipt.get("resolved_work_item_id") or "").strip()
    loaded = str(loaded_work_item_id or "").strip()
    output = str(output_work_item_id or "").strip()
    if not resolved or not loaded or not output or len({resolved, loaded, output}) != 1:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_OUTPUT_SCOPE_MISMATCH",
            details={
                "resolved_work_item_id": resolved or None,
                "loaded_work_item_id": loaded or None,
                "output_work_item_id": output or None,
            },
        )
    return {"status": "PASS", "matched": True, "work_item_id": resolved}


def apply_constraint_ledger(
    baseline: Iterable[str],
    *,
    changed: Iterable[str] = (),
    preserved: Iterable[str] = (),
    locked: Iterable[str] = (),
    revoked: Iterable[str] = (),
) -> list[str]:
    """Apply omission-is-not-revocation semantics to a compact string ledger."""
    state: list[str] = []
    for item in list(baseline) + list(preserved) + list(changed) + list(locked):
        value = str(item).strip()
        if value and value not in state:
            state.append(value)
    revoked_set = {str(item).strip() for item in revoked if str(item).strip()}
    return [item for item in state if item not in revoked_set]


def validate_state_transition(current: str, target: str) -> bool:
    current = str(current).strip().upper()
    target = str(target).strip().upper()
    if current not in ALLOWED_TRANSITIONS or target not in ALLOWED_TRANSITIONS[current]:
        raise ActiveWorkItemResolutionError(
            "INVALID_WORK_ITEM_STATE_TRANSITION",
            details={"current": current, "target": target},
        )
    return True
