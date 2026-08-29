"""Active work-item resolution gate for continuation-style directing requests.

This module binds a continuation request to the canonical current-production
snapshot before Director Feature Compiler runs. It is intentionally bounded:
it does not fetch GitHub, choose screenplay facts, mutate continuity, or become
a second project authority. Callers supply freshness evidence for source Issue
checkpoints when the active snapshot declares one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


CONTINUITY_PATH = Path("07_连续性与生产状态/连续性与当前生产状态.md")
STATE_BEGIN = "<!-- ACTIVE_WORK_ITEM_STATE_BEGIN -->"
STATE_END = "<!-- ACTIVE_WORK_ITEM_STATE_END -->"

# These expressions are intrinsically discourse/anaphora references rather than
# ordinary in-scene action language. Generic verbs such as “继续” and “接着” are
# deliberately handled separately because “继续追击/继续攀爬” describe character
# action and must not invoke project-state reconciliation.
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
        }


def _normalize_discourse_text(description: str) -> str:
    return " ".join(description.casefold().split()).strip()


def _continuation_verb_targets_discourse_object(text: str, verb: str) -> bool:
    """Return true only when a generic continuation verb points to prior work.

    A bounded window is used so a later unrelated mention of “镜头” does not turn
    an in-scene action such as “角色继续追击，镜头跟随” into a continuation request.
    """
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
    """Detect discourse continuation without confusing it with scene action.

    Strong anaphora such as “上次/刚才/那30秒/下一镜” always require resolution.
    Generic “继续/接着” only count when used alone as a short discourse command or
    when they directly target a bounded discourse object such as “上一版/下一镜”.
    """
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

    for verb in CONTINUATION_VERBS:
        if _continuation_verb_targets_discourse_object(normalized, verb):
            return True
    return False


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


def resolve_work_item(
    description: str,
    *,
    project_root: str | Path,
    context: dict[str, Any] | None = None,
) -> WorkItemResolution:
    """Resolve continuation work-item identity before downstream compilation.

    `context` is an orchestration receipt, not an authority store. The caller may
    pass exact source-Issue freshness evidence or an explicit user-selected
    non-active work-item identity. Semantic search results are deliberately not
    accepted as identity proof.
    """
    if not is_continuation_request(description):
        return WorkItemResolution(
            resolution_required=False,
            resolved_work_item_id=None,
            continuation_resolution_source="not_required",
            checkpoint_ref=None,
            freshness_verified=False,
            gate_status="NOT_REQUIRED",
        )

    context = dict(context or {})
    state = load_active_work_item_state(project_root)
    active_id = str(state["work_item_id"]).strip()

    explicit_id = str(context.get("explicit_work_item_id") or "").strip() or None
    if explicit_id:
        if explicit_id != active_id and context.get("explicit_target_verified") is not True:
            raise ActiveWorkItemResolutionError(
                "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
                details={"active_work_item_id": active_id, "explicit_work_item_id": explicit_id},
            )
        return WorkItemResolution(
            resolution_required=True,
            resolved_work_item_id=explicit_id,
            continuation_resolution_source="user_explicit",
            checkpoint_ref=_normalize_checkpoint(context.get("explicit_checkpoint_ref")),
            freshness_verified=True,
            gate_status="RESOLVED_VERIFIED",
            source_issue=context.get("explicit_source_issue"),
            latest_source_checkpoint_ref=_normalize_checkpoint(
                context.get("explicit_checkpoint_ref")
            ),
        )

    source_issue = state.get("source_issue")
    checkpoint = _normalize_checkpoint(state.get("latest_applied_checkpoint_ref"))
    checkpoint_status = str(state.get("checkpoint_writeback_status") or "").strip().casefold()

    if source_issue not in (None, "", 0, "0"):
        if context.get("source_issue_accessible") is not True:
            raise ActiveWorkItemResolutionError(
                "WORK_ITEM_FRESHNESS_UNVERIFIED",
                details={"source_issue": source_issue, "reason": "source_issue_not_verified_accessible"},
            )
        latest = _normalize_checkpoint(context.get("latest_source_checkpoint_ref"))
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
        freshness_verified = True
        latest_source = latest
    else:
        if checkpoint_status != "verified":
            raise ActiveWorkItemResolutionError(
                "WORK_ITEM_FRESHNESS_UNVERIFIED",
                details={"reason": "snapshot_writeback_not_verified"},
            )
        freshness_verified = True
        latest_source = checkpoint

    return WorkItemResolution(
        resolution_required=True,
        resolved_work_item_id=active_id,
        continuation_resolution_source="active_work_item_pointer",
        checkpoint_ref=checkpoint,
        freshness_verified=freshness_verified,
        gate_status="RESOLVED_VERIFIED",
        source_issue=source_issue,
        latest_source_checkpoint_ref=latest_source,
    )


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
