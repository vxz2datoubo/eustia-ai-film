"""Active work-item resolution gate for continuation-style directing requests.

The gate binds conversational continuation to a concrete production work item
before Director Feature Compiler runs. Runtime trust comes from the canonical
continuity snapshot in the repository checkout. Source Issues remain revision
and evidence trace; serialized request data and caller-supplied Python callbacks
cannot mint work-item identity or checkpoint verification.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml


CONTINUITY_PATH = Path("07_连续性与生产状态/连续性与当前生产状态.md")
PROJECT_INDEX_PATH = Path("PROJECT_INDEX.yaml")
STATE_BEGIN = "<!-- ACTIVE_WORK_ITEM_STATE_BEGIN -->"
STATE_END = "<!-- ACTIVE_WORK_ITEM_STATE_END -->"

STRONG_CONTINUATION_SIGNALS = (
    "上次", "刚才", "那30秒", "那段", "那个镜头", "之前那个",
    "下一镜", "继续下面剧情", "重新导演那", "重新做那个",
)
CONTINUATION_VERBS = ("继续", "接着")
DISCOURSE_OBJECTS = (
    "上一版", "上个版本", "上次", "刚才", "那30秒", "这30秒", "那个30秒",
    "那段", "这段", "那个镜头", "这个镜头", "当前镜头", "之前那个",
    "下一镜", "下一个镜头", "下面剧情", "后面剧情", "这个版本", "那一版",
)
NONACTIVE_REFERENT_HINTS = (
    "之前", "以前", "更早", "旧的", "旧版", "前一个", "前面那个",
)
EXACT_PREVIOUS_REFERENT_HINTS = (
    "之前那个", "前一个", "前面那个", "上一工作项", "上一个工作项", "上一段",
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
    "writeback_verified_commit",
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
    target_metadata: dict[str, Any] | None = None
    verification_basis: str | None = None
    snapshot_fingerprint: str | None = None

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
            "verification_basis": self.verification_basis,
            "snapshot_fingerprint": self.snapshot_fingerprint,
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


def _normalize_repo_text(value: str) -> str:
    return value.replace("\r\n", "\n").rstrip("\n")


def _load_continuity_markdown(project_root: str | Path) -> str:
    path = Path(project_root) / CONTINUITY_PATH
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_MISSING") from exc


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
    return _extract_state_payload(_load_continuity_markdown(project_root))


def _validate_project_authority_payload(index: dict[str, Any]) -> None:
    if index.get("project_id") != "EUSTIA_AI_FILM":
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE",
            details={"reason": "project_id_mismatch"},
        )
    canonical = index.get("canonical") or {}
    if canonical.get("continuity") != CONTINUITY_PATH.as_posix():
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE",
            details={"reason": "continuity_not_registered_in_project_index"},
        )


def _validate_project_authority_binding(project_root: str | Path) -> None:
    root = Path(project_root)
    index_path = root / PROJECT_INDEX_PATH
    try:
        index = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE",
            details={"missing": PROJECT_INDEX_PATH.as_posix()},
        ) from exc
    if not isinstance(index, dict):
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE",
            details={"reason": "project_index_not_mapping"},
        )
    _validate_project_authority_payload(index)


def _snapshot_projection(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "work_item_id": str(state.get("work_item_id") or "").strip(),
        "status": str(state.get("status") or "").strip(),
        "source_issue": state.get("source_issue"),
        "baseline_checkpoint_ref": _normalize_checkpoint(state.get("baseline_checkpoint_ref")),
        "latest_applied_checkpoint_ref": _normalize_checkpoint(
            state.get("latest_applied_checkpoint_ref")
        ),
        "story_scope_ref": str(state.get("story_scope_ref") or "").strip(),
        "current_effective_state_summary": str(
            state.get("current_effective_state_summary") or ""
        ).strip(),
        "locked_constraints": list(state.get("locked_constraints") or []),
        "preserved_constraints": list(state.get("preserved_constraints") or []),
        "revoked_constraints": list(state.get("revoked_constraints") or []),
        "experimental_constraints": list(state.get("experimental_constraints") or []),
        "unresolved_failures": list(state.get("unresolved_failures") or []),
        "checkpoint_writeback_status": str(
            state.get("checkpoint_writeback_status") or ""
        ).strip().casefold(),
        "writeback_verified_commit": str(
            state.get("writeback_verified_commit") or ""
        ).strip(),
    }


def _git_capture(
    project_root: str | Path,
    *args: str,
    allow_failure: bool = False,
) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(Path(project_root)), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        if allow_failure:
            return 127, "", str(exc)
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            details={"reason": "git_runtime_unavailable"},
        ) from exc
    if completed.returncode != 0 and not allow_failure:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            details={
                "reason": "git_provenance_query_failed",
                "args": list(args),
                "stderr": completed.stderr.strip()[:400],
            },
        )
    return completed.returncode, completed.stdout, completed.stderr


def _resolve_canonical_main_commit(project_root: str | Path) -> str:
    resolved: dict[str, str] = {}
    for ref in ("refs/heads/main", "refs/remotes/origin/main"):
        code, stdout, _ = _git_capture(
            project_root,
            "rev-parse",
            "--verify",
            ref,
            allow_failure=True,
        )
        if code == 0 and stdout.strip():
            resolved[ref] = stdout.strip()

    if not resolved:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            details={"reason": "canonical_main_ref_missing"},
        )
    unique = set(resolved.values())
    if len(unique) != 1:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            details={"reason": "canonical_main_ref_ambiguous", "refs": resolved},
        )
    return next(iter(unique))


def _committed_text(
    project_root: str | Path,
    commit: str,
    path: Path,
) -> str:
    _, stdout, _ = _git_capture(
        project_root,
        "show",
        f"{commit}:{path.as_posix()}",
    )
    return stdout


def _verify_canonical_snapshot(
    project_root: str | Path, state: dict[str, Any]
) -> tuple[str, str | None]:
    """Bind freshness to the canonical main checkout and committed readback.

    Snapshot fields such as `checkpoint_writeback_status` and
    `writeback_verified_commit` are retained for backward-compatible audit data,
    but they are not trust inputs. Runtime freshness is granted only when the
    checkout HEAD is exactly the repository's canonical main ref and both
    PROJECT_INDEX plus continuity are byte-equivalent to the committed main
    objects being consumed.
    """
    root = Path(project_root)
    _validate_project_authority_binding(root)
    projection = _snapshot_projection(state)
    checkpoint = projection["latest_applied_checkpoint_ref"]
    if checkpoint is None:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            details={"reason": "latest_applied_checkpoint_ref_missing"},
        )

    canonical_commit = _resolve_canonical_main_commit(root)
    _, head_stdout, _ = _git_capture(root, "rev-parse", "HEAD")
    head = head_stdout.strip()
    if head != canonical_commit:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            details={
                "reason": "current_head_is_not_canonical_main",
                "head": head or None,
                "canonical_main": canonical_commit,
            },
        )

    committed_index_text = _committed_text(root, canonical_commit, PROJECT_INDEX_PATH)
    try:
        working_index_text = (root / PROJECT_INDEX_PATH).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE",
            details={"missing": PROJECT_INDEX_PATH.as_posix()},
        ) from exc
    if _normalize_repo_text(committed_index_text) != _normalize_repo_text(working_index_text):
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            details={"reason": "project_index_worktree_differs_from_canonical_main"},
        )
    committed_index = yaml.safe_load(committed_index_text) or {}
    if not isinstance(committed_index, dict):
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE",
            details={"reason": "canonical_project_index_not_mapping"},
        )
    _validate_project_authority_payload(committed_index)

    committed_continuity = _committed_text(root, canonical_commit, CONTINUITY_PATH)
    working_continuity = _load_continuity_markdown(root)
    if _normalize_repo_text(committed_continuity) != _normalize_repo_text(working_continuity):
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            details={"reason": "continuity_worktree_differs_from_canonical_main"},
        )
    committed_state = _extract_state_payload(committed_continuity)
    if _snapshot_projection(committed_state) != projection:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            details={"reason": "active_snapshot_projection_differs_from_canonical_main"},
        )

    _, tree_stdout, _ = _git_capture(root, "rev-parse", f"{canonical_commit}^{{tree}}")
    _, blob_stdout, _ = _git_capture(
        root,
        "rev-parse",
        f"{canonical_commit}:{CONTINUITY_PATH.as_posix()}",
    )
    evidence = {
        "projection": projection,
        "canonical_commit": canonical_commit,
        "canonical_tree": tree_stdout.strip(),
        "continuity_blob": blob_stdout.strip(),
    }
    encoded = json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    fingerprint = hashlib.sha256(encoded).hexdigest()[:24]
    return fingerprint, checkpoint


def _historical_section_for_previous(
    markdown: str, previous_work_item_id: str
) -> str | None:
    marker = f"｜{previous_work_item_id}"
    lines = markdown.splitlines()
    start: int | None = None
    level: int | None = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and marker in stripped:
            start = idx
            level = len(stripped) - len(stripped.lstrip("#"))
            break
    if start is None or level is None:
        return None

    end = len(lines)
    prefix = "#" * level + " "
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith(prefix):
            end = idx
            break
    section = "\n".join(lines[start:end]).strip()
    return section or None


def _resolve_canonical_previous_target(
    description: str,
    *,
    state: dict[str, Any],
    markdown: str,
    snapshot_fingerprint: str,
) -> WorkItemResolution | None:
    if not _explicit_nonactive_hint(description):
        return None

    previous_id = str(state.get("previous_work_item_id") or "").strip()
    if not previous_id:
        raise ActiveWorkItemResolutionError(
            "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
            details={"reason": "canonical_previous_work_item_id_missing"},
        )

    normalized = _normalize_discourse_text(description)
    exact_identity = previous_id.casefold() in normalized
    exact_previous_relation = any(
        hint in normalized for hint in EXACT_PREVIOUS_REFERENT_HINTS
    )
    if not exact_identity and not exact_previous_relation:
        raise ActiveWorkItemResolutionError(
            "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
            details={
                "reason": "nonactive_phrase_not_exactly_bound_to_registered_previous_item",
                "registered_previous_work_item_id": previous_id,
            },
        )

    section = _historical_section_for_previous(markdown, previous_id)
    if section is None:
        raise ActiveWorkItemResolutionError(
            "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
            details={"reason": "canonical_historical_section_missing"},
        )

    compact_summary = " ".join(
        line.strip("# -*`\t")
        for line in section.splitlines()
        if line.strip() and not line.strip().startswith("```")
    )
    compact_summary = " ".join(compact_summary.split())[:1200]

    target = {
        "work_item_id": previous_id,
        "checkpoint_ref": None,
        "source_issue": None,
        "story_scope_ref": None,
        "summary": compact_summary,
        "locked_constraints": [],
        "preserved_constraints": [],
        "revoked_constraints": [],
        "experimental_constraints": [],
        "unresolved_failures": [],
        "canonical_historical_section": True,
    }
    return WorkItemResolution(
        resolution_required=True,
        resolved_work_item_id=previous_id,
        continuation_resolution_source="user_explicit_canonical_previous_work_item",
        checkpoint_ref=None,
        freshness_verified=True,
        gate_status="RESOLVED_VERIFIED",
        source_issue=None,
        latest_source_checkpoint_ref=None,
        target_metadata=target,
        verification_basis="canonical_continuity_historical_binding",
        snapshot_fingerprint=snapshot_fingerprint,
    )


def resolve_work_item(
    description: str,
    *,
    project_root: str | Path,
) -> WorkItemResolution:
    """Resolve work-item identity from canonical continuity before compilation."""
    if not is_continuation_request(description):
        return WorkItemResolution(
            resolution_required=False,
            resolved_work_item_id=None,
            continuation_resolution_source="not_required",
            checkpoint_ref=None,
            freshness_verified=False,
            gate_status="NOT_REQUIRED",
            verification_basis="not_required",
        )

    markdown = _load_continuity_markdown(project_root)
    state = _extract_state_payload(markdown)
    fingerprint, checkpoint = _verify_canonical_snapshot(project_root, state)

    explicit = _resolve_canonical_previous_target(
        description,
        state=state,
        markdown=markdown,
        snapshot_fingerprint=fingerprint,
    )
    if explicit is not None:
        return explicit

    active_id = str(state["work_item_id"]).strip()
    return WorkItemResolution(
        resolution_required=True,
        resolved_work_item_id=active_id,
        continuation_resolution_source="active_work_item_pointer",
        checkpoint_ref=checkpoint,
        freshness_verified=True,
        gate_status="RESOLVED_VERIFIED",
        source_issue=state.get("source_issue"),
        latest_source_checkpoint_ref=None,
        target_metadata=None,
        verification_basis="canonical_continuity_verified_snapshot",
        snapshot_fingerprint=fingerprint,
    )


def build_work_item_context_packet(
    project_root: str | Path,
    resolution: WorkItemResolution,
) -> dict[str, Any]:
    """Build a compact coordination projection for downstream specialists."""
    if not resolution.resolution_required or not resolution.resolved_work_item_id:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_CONTEXT_PACKET_REQUIRES_RESOLUTION"
        )

    state = load_active_work_item_state(project_root)
    active_id = str(state["work_item_id"]).strip()
    if resolution.resolved_work_item_id == active_id:
        target = state
    else:
        target = dict(resolution.target_metadata or {})
        if (
            str(target.get("work_item_id") or "").strip()
            != resolution.resolved_work_item_id
        ):
            raise ActiveWorkItemResolutionError(
                "WORK_ITEM_CONTEXT_PACKET_TARGET_NOT_FOUND",
                details={"work_item_id": resolution.resolved_work_item_id},
            )

    return {
        "schema_version": "1.1",
        "packet_type": "WorkItemContext",
        "work_item_id": resolution.resolved_work_item_id,
        "resolution_source": resolution.continuation_resolution_source,
        "checkpoint_ref": resolution.checkpoint_ref,
        "freshness_verified": resolution.freshness_verified,
        "verification_basis": resolution.verification_basis,
        "snapshot_fingerprint": resolution.snapshot_fingerprint,
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
        "bound_media_or_reference_refs": list(
            target.get("bound_media_or_reference_refs") or []
        ),
        "authority_refs": {
            "project_registry": PROJECT_INDEX_PATH.as_posix(),
            "continuity": CONTINUITY_PATH.as_posix(),
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
            details={
                "expected_work_item_id": expected or None,
                "observed_work_item_id": observed or None,
            },
        )
    if packet.get("freshness_verified") is not True:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_STALE")
    if not str(packet.get("verification_basis") or "").startswith("canonical_"):
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_INVALID")
    if packet.get("authority_boundary") != "coordination_projection_only":
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_INVALID")
    return True


def validate_output_work_item(
    resolution: WorkItemResolution | dict[str, Any],
    *,
    loaded_work_item_id: str | None,
    output_work_item_id: str | None,
) -> dict[str, Any]:
    """Resolved, loaded and emitted work-item identity must match."""
    receipt = (
        resolution.as_dict()
        if isinstance(resolution, WorkItemResolution)
        else dict(resolution)
    )
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
    revoked_set = {
        str(item).strip() for item in revoked if str(item).strip()
    }
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
