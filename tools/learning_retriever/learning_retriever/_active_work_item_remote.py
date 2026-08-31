"""Fixed-GitHub trust root for Active Work Item resolution."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import ssl
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

import yaml

CANONICAL_REPOSITORY = "vxz2datoubo/eustia-ai-film"
CANONICAL_BRANCH = "main"
GITHUB_API_ROOT = "https://api.github.com"
CONTINUITY_PATH = Path("07_连续性与生产状态/连续性与当前生产状态.md")
PROJECT_INDEX_PATH = Path("PROJECT_INDEX.yaml")
STATE_BEGIN = "<!-- ACTIVE_WORK_ITEM_STATE_BEGIN -->"
STATE_END = "<!-- ACTIVE_WORK_ITEM_STATE_END -->"

STRONG_CONTINUATION_SIGNALS = ("上次", "刚才", "那30秒", "那段", "那个镜头", "之前那个", "下一镜", "继续下面剧情", "重新导演那", "重新做那个")
CONTINUATION_VERBS = ("继续", "接着")
DISCOURSE_OBJECTS = ("上一版", "上个版本", "上次", "刚才", "那30秒", "这30秒", "那个30秒", "那段", "这段", "那个镜头", "这个镜头", "当前镜头", "之前那个", "下一镜", "下一个镜头", "下面剧情", "后面剧情", "这个版本", "那一版")
NONACTIVE_REFERENT_HINTS = ("之前", "以前", "更早", "旧的", "旧版", "前一个", "前面那个")
EXACT_PREVIOUS_REFERENT_HINTS = ("之前那个", "前一个", "前面那个", "上一工作项", "上一个工作项", "上一段")
REQUIRED_STATE_FIELDS = (
    "work_item_id", "status", "source_issue", "baseline_checkpoint_ref", "latest_applied_checkpoint_ref",
    "story_scope_ref", "current_effective_state_summary", "locked_constraints", "preserved_constraints",
    "revoked_constraints", "experimental_constraints", "unresolved_failures", "checkpoint_writeback_status",
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
_STRUCTURED_REVISION_PATTERNS = (
    re.compile(r"(?im)^#{1,4}\s*Director checkpoint\b"),
    re.compile(r"(?im)^#{1,4}\s*Revision checkpoint\b"),
    re.compile(r"(?im)^#{1,4}\s*Micro Capture\b"),
    re.compile(r"(?im)^#{1,4}\s*Trajectory Final-Delta\b"),
    re.compile(r"(?im)^\s*schema:\s*(?:MICRO_CAPTURE|REVISION_CHECKPOINT|TRAJECTORY_FINAL_DELTA)/v\d+\b"),
)


class ActiveWorkItemResolutionError(ValueError):
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


def _norm(text: str) -> str:
    return " ".join(text.casefold().split()).strip()


def _verb_targets(text: str, verb: str) -> bool:
    start = 0
    while True:
        hit = text.find(verb, start)
        if hit < 0:
            return False
        tail = text[hit + len(verb):hit + len(verb) + 18].lstrip(" ，,：:。；;！!？?")
        if any(tail.startswith(obj) for obj in DISCOURSE_OBJECTS):
            return True
        start = hit + len(verb)


def is_continuation_request(description: str) -> bool:
    if not isinstance(description, str) or not _norm(description):
        return False
    text = _norm(description)
    if any(signal.casefold() in text for signal in STRONG_CONTINUATION_SIGNALS):
        return True
    if text.strip(" ，,：:。；;！!？?") in CONTINUATION_VERBS:
        return True
    return any(_verb_targets(text, verb) for verb in CONTINUATION_VERBS)


def _normalize_checkpoint(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    return text or None


def _normalize_repo_text(value: str) -> str:
    return value.replace("\r\n", "\n").rstrip("\n")


def _extract_state_payload(markdown: str) -> dict[str, Any]:
    start, end = markdown.find(STATE_BEGIN), markdown.find(STATE_END)
    if start < 0 or end <= start:
        raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_MISSING")
    payload = markdown[start + len(STATE_BEGIN):end].strip()
    for fence in ("```yaml", "```yml", "```"):
        if payload.startswith(fence):
            payload = payload[len(fence):]
            break
    payload = payload.strip()
    if payload.endswith("```"):
        payload = payload[:-3].strip()
    try:
        parsed = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_INVALID", details={"yaml_error": str(exc)}) from exc
    if not isinstance(parsed, Mapping) or not isinstance(parsed.get("active_work_item"), Mapping):
        raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_INVALID")
    state = dict(parsed["active_work_item"])
    missing = [key for key in REQUIRED_STATE_FIELDS if key not in state]
    if missing:
        raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_INVALID", details={"missing_fields": missing})
    if not str(state.get("work_item_id") or "").strip():
        raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_INVALID", details={"field": "work_item_id"})
    for key in ("locked_constraints", "preserved_constraints", "revoked_constraints", "experimental_constraints", "unresolved_failures"):
        if not isinstance(state.get(key), list):
            raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_INVALID", details={"field": key})
    return state


def load_active_work_item_state(project_root: str | Path) -> dict[str, Any]:
    try:
        text = (Path(project_root) / CONTINUITY_PATH).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ActiveWorkItemResolutionError("ACTIVE_WORK_ITEM_STATE_MISSING") from exc
    return _extract_state_payload(text)


def _snapshot_projection(state: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "work_item_id", "status", "source_issue", "baseline_checkpoint_ref", "latest_applied_checkpoint_ref",
        "story_scope_ref", "current_effective_state_summary", "locked_constraints", "preserved_constraints",
        "revoked_constraints", "experimental_constraints", "unresolved_failures", "bound_media_or_reference_refs",
        "current_best_ref", "previous_work_item_id", "next_expected_action", "checkpoint_writeback_status",
        "writeback_verified_commit",
    )
    out = {key: state.get(key) for key in keys}
    out["baseline_checkpoint_ref"] = _normalize_checkpoint(out.get("baseline_checkpoint_ref"))
    out["latest_applied_checkpoint_ref"] = _normalize_checkpoint(out.get("latest_applied_checkpoint_ref"))
    out["checkpoint_writeback_status"] = str(out.get("checkpoint_writeback_status") or "").strip().casefold()
    out["writeback_verified_commit"] = str(out.get("writeback_verified_commit") or "").strip()
    for key in ("locked_constraints", "preserved_constraints", "revoked_constraints", "experimental_constraints", "unresolved_failures", "bound_media_or_reference_refs"):
        out[key] = list(out.get(key) or [])
    return out


def _snapshot_identity_projection(state: Mapping[str, Any]) -> dict[str, Any]:
    out = _snapshot_projection(state)
    out.pop("checkpoint_writeback_status", None)
    out.pop("writeback_verified_commit", None)
    return out


def _validate_project_index(index: Mapping[str, Any]) -> None:
    if index.get("project_id") != "EUSTIA_AI_FILM":
        raise ActiveWorkItemResolutionError("WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE", details={"reason": "project_id_mismatch"})
    canonical = index.get("canonical") or {}
    if not isinstance(canonical, Mapping) or canonical.get("continuity") != CONTINUITY_PATH.as_posix():
        raise ActiveWorkItemResolutionError("WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE", details={"reason": "continuity_not_registered_in_project_index"})


def _tls_context() -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.load_default_certs()
    return context


def _github_api_json(endpoint: str) -> Any:
    prefix = f"/repos/{CANONICAL_REPOSITORY}/"
    if not isinstance(endpoint, str) or not endpoint.startswith(prefix) or "://" in endpoint:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE", details={"reason": "noncanonical_api_endpoint"})
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "eustia-active-work-item-gate/3"}
    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=_tls_context()))
    try:
        with opener.open(Request(GITHUB_API_ROOT + endpoint, headers=headers, method="GET"), timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, UnicodeError, json.JSONDecodeError) as exc:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE", details={"reason": "fixed_github_readback_failed", "endpoint": endpoint, "error": type(exc).__name__}) from exc


def _github_file_text(path: Path, ref: str) -> str:
    payload = _github_api_json(f"/repos/{CANONICAL_REPOSITORY}/contents/{quote(path.as_posix(), safe='/')}?ref={quote(ref, safe='')}")
    if not isinstance(payload, Mapping) or payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
        raise ActiveWorkItemResolutionError("WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE", details={"reason": "github_file_readback_invalid", "path": path.as_posix()})
    try:
        return base64.b64decode(payload["content"]).decode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE", details={"reason": "github_file_decode_failed", "path": path.as_posix()}) from exc


def _github_issue_comments(issue: int) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for page in range(1, 11):
        payload = _github_api_json(f"/repos/{CANONICAL_REPOSITORY}/issues/{issue}/comments?per_page=100&page={page}")
        if not isinstance(payload, list):
            raise ActiveWorkItemResolutionError("WORK_ITEM_SOURCE_ISSUE_UNAVAILABLE", details={"source_issue": issue, "reason": "invalid_comment_payload"})
        comments.extend(dict(item) for item in payload if isinstance(item, Mapping))
        if len(payload) < 100:
            return comments
    raise ActiveWorkItemResolutionError("WORK_ITEM_SOURCE_ISSUE_UNAVAILABLE", details={"source_issue": issue, "reason": "comment_scan_bound_exceeded"})


def _is_structured_revision_comment(body: Any) -> bool:
    text = body if isinstance(body, str) else ""
    return any(pattern.search(text) for pattern in _STRUCTURED_REVISION_PATTERNS)


def _live_source_checkpoint(source_issue: Any, applied_ref: str) -> str:
    try:
        issue, applied = int(str(source_issue).strip()), int(applied_ref)
    except (TypeError, ValueError) as exc:
        raise ActiveWorkItemResolutionError("WORK_ITEM_SOURCE_ISSUE_UNAVAILABLE", details={"reason": "non_numeric_issue_or_checkpoint"}) from exc
    try:
        comments = _github_issue_comments(issue)
    except ActiveWorkItemResolutionError as exc:
        if exc.code == "WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE":
            raise ActiveWorkItemResolutionError("WORK_ITEM_SOURCE_ISSUE_UNAVAILABLE", details={"source_issue": issue, **exc.details}) from exc
        raise
    ids = sorted(int(c["id"]) for c in comments if isinstance(c.get("id"), int) and _is_structured_revision_comment(c.get("body")))
    latest = ids[-1] if ids else applied
    if latest > applied:
        raise ActiveWorkItemResolutionError(
            "WORK_ITEM_SOURCE_REVISION_AHEAD_OF_CANONICAL",
            details={"source_issue": issue, "latest_applied_checkpoint_ref": str(applied), "latest_source_checkpoint_ref": str(latest), "gate_status": "RECONCILE_REQUIRED"},
        )
    return str(latest)


def _remote_materialization(canonical_sha: str, state: Mapping[str, Any]) -> str:
    projection = _snapshot_projection(state)
    if projection["checkpoint_writeback_status"] != "verified":
        raise ActiveWorkItemResolutionError("WORK_ITEM_SNAPSHOT_UNVERIFIED", details={"reason": "checkpoint_writeback_not_finalized"})
    declared = projection["writeback_verified_commit"]
    if not (len(declared) == 40 and all(c in "0123456789abcdef" for c in declared.casefold())):
        raise ActiveWorkItemResolutionError("WORK_ITEM_SNAPSHOT_UNVERIFIED", details={"reason": "materialization_commit_not_full_sha"})
    commit = _github_api_json(f"/repos/{CANONICAL_REPOSITORY}/commits/{declared}")
    if not isinstance(commit, Mapping) or commit.get("sha") != declared:
        raise ActiveWorkItemResolutionError("WORK_ITEM_SNAPSHOT_UNVERIFIED", details={"reason": "materialization_commit_missing"})
    compare = _github_api_json(f"/repos/{CANONICAL_REPOSITORY}/compare/{declared}...{canonical_sha}")
    merge_base = compare.get("merge_base_commit") if isinstance(compare, Mapping) else None
    status = str(compare.get("status") or "") if isinstance(compare, Mapping) else ""
    if not isinstance(merge_base, Mapping) or merge_base.get("sha") != declared or status not in {"ahead", "identical"}:
        raise ActiveWorkItemResolutionError("WORK_ITEM_SNAPSHOT_UNVERIFIED", details={"reason": "materialization_commit_not_canonical_ancestor"})
    materialized = _extract_state_payload(_github_file_text(CONTINUITY_PATH, declared))
    if _snapshot_identity_projection(materialized) != _snapshot_identity_projection(state):
        raise ActiveWorkItemResolutionError("WORK_ITEM_SNAPSHOT_UNVERIFIED", details={"reason": "materialization_snapshot_identity_mismatch"})
    return declared


def _trusted_snapshot(project_root: str | Path) -> tuple[dict[str, Any], str, str, str]:
    branch = _github_api_json(f"/repos/{CANONICAL_REPOSITORY}/branches/{CANONICAL_BRANCH}")
    sha = str(((branch.get("commit") or {}) if isinstance(branch, Mapping) else {}).get("sha") or "")
    if not (len(sha) == 40 and all(c in "0123456789abcdef" for c in sha.casefold())):
        raise ActiveWorkItemResolutionError("WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE", details={"reason": "canonical_main_sha_missing"})
    index_text = _github_file_text(PROJECT_INDEX_PATH, sha)
    continuity_text = _github_file_text(CONTINUITY_PATH, sha)
    try:
        index = yaml.safe_load(index_text) or {}
    except yaml.YAMLError as exc:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE", details={"reason": "canonical_project_index_invalid"}) from exc
    if not isinstance(index, Mapping):
        raise ActiveWorkItemResolutionError("WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE", details={"reason": "canonical_project_index_not_mapping"})
    _validate_project_index(index)
    state = _extract_state_payload(continuity_text)

    root = Path(project_root)
    try:
        local_index = (root / PROJECT_INDEX_PATH).read_text(encoding="utf-8")
        local_continuity = (root / CONTINUITY_PATH).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ActiveWorkItemResolutionError("WORK_ITEM_SNAPSHOT_UNVERIFIED", details={"reason": "local_projection_missing"}) from exc
    if _normalize_repo_text(local_index) != _normalize_repo_text(index_text):
        raise ActiveWorkItemResolutionError("WORK_ITEM_SNAPSHOT_UNVERIFIED", details={"reason": "project_index_local_differs_from_fixed_github_main"})
    if _normalize_repo_text(local_continuity) != _normalize_repo_text(continuity_text):
        raise ActiveWorkItemResolutionError("WORK_ITEM_SNAPSHOT_UNVERIFIED", details={"reason": "continuity_local_differs_from_fixed_github_main"})

    materialization = _remote_materialization(sha, state)
    applied = _normalize_checkpoint(state.get("latest_applied_checkpoint_ref"))
    if applied is None:
        raise ActiveWorkItemResolutionError("WORK_ITEM_SNAPSHOT_UNVERIFIED", details={"reason": "latest_applied_checkpoint_ref_missing"})
    latest = _live_source_checkpoint(state.get("source_issue"), applied)
    receipt = {
        "repository": CANONICAL_REPOSITORY, "branch": CANONICAL_BRANCH, "sha": sha,
        "continuity_sha256": hashlib.sha256(continuity_text.encode()).hexdigest(),
        "materialization": materialization, "latest_structured_source_checkpoint": latest,
        "projection": _snapshot_projection(state),
    }
    fingerprint = hashlib.sha256(json.dumps(receipt, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:24]
    return state, continuity_text, fingerprint, latest


def _historical_section(markdown: str, previous_id: str) -> str | None:
    marker = f"｜{previous_id}"
    lines = markdown.splitlines()
    for start, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and marker in stripped:
            level = len(stripped) - len(stripped.lstrip("#"))
            prefix = "#" * level + " "
            end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(prefix)), len(lines))
            return "\n".join(lines[start:end]).strip() or None
    return None


def _previous_resolution(description: str, state: dict[str, Any], markdown: str, fingerprint: str, latest: str) -> WorkItemResolution | None:
    text = _norm(description)
    if not any(h in text for h in NONACTIVE_REFERENT_HINTS):
        return None
    previous = str(state.get("previous_work_item_id") or "").strip()
    if not previous:
        raise ActiveWorkItemResolutionError("EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION", details={"reason": "canonical_previous_work_item_id_missing"})
    if previous.casefold() not in text and not any(h in text for h in EXACT_PREVIOUS_REFERENT_HINTS):
        raise ActiveWorkItemResolutionError("EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION", details={"reason": "nonactive_phrase_not_exactly_bound_to_registered_previous_item"})
    section = _historical_section(markdown, previous)
    if section is None:
        raise ActiveWorkItemResolutionError("EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION", details={"reason": "canonical_historical_section_missing"})
    summary = " ".join(line.strip("# -*`\t") for line in section.splitlines() if line.strip() and not line.strip().startswith("```"))
    target = {"work_item_id": previous, "summary": " ".join(summary.split())[:1200], "story_scope_ref": None, "locked_constraints": [], "preserved_constraints": [], "revoked_constraints": [], "experimental_constraints": [], "unresolved_failures": [], "bound_media_or_reference_refs": [], "canonical_historical_section": True}
    return WorkItemResolution(True, previous, "user_explicit_canonical_previous_work_item", None, True, gate_status="RESOLVED_VERIFIED", source_issue=state.get("source_issue"), latest_source_checkpoint_ref=latest, target_metadata=target, verification_basis="canonical_github_readback_historical_binding", snapshot_fingerprint=fingerprint)


def resolve_work_item(description: str, *, project_root: str | Path) -> WorkItemResolution:
    if not is_continuation_request(description):
        return WorkItemResolution(False, None, "not_required", None, False, gate_status="NOT_REQUIRED", verification_basis="not_required")
    state, markdown, fingerprint, latest = _trusted_snapshot(project_root)
    previous = _previous_resolution(description, state, markdown, fingerprint, latest)
    if previous is not None:
        return previous
    return WorkItemResolution(
        True, str(state["work_item_id"]).strip(), "active_work_item_pointer",
        _normalize_checkpoint(state.get("latest_applied_checkpoint_ref")), True,
        gate_status="RESOLVED_VERIFIED", source_issue=state.get("source_issue"),
        latest_source_checkpoint_ref=latest, target_metadata=dict(state),
        verification_basis="canonical_github_readback_verified_snapshot", snapshot_fingerprint=fingerprint,
    )


def build_work_item_context_packet(project_root: str | Path, resolution: WorkItemResolution) -> dict[str, Any]:
    del project_root
    if not resolution.resolution_required or not resolution.resolved_work_item_id:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_REQUIRES_RESOLUTION")
    target = dict(resolution.target_metadata or {})
    if str(target.get("work_item_id") or "").strip() != resolution.resolved_work_item_id:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_TARGET_NOT_FOUND")
    return {
        "schema_version": "2.0", "packet_type": "WorkItemContext", "work_item_id": resolution.resolved_work_item_id,
        "resolution_source": resolution.continuation_resolution_source, "checkpoint_ref": resolution.checkpoint_ref,
        "freshness_verified": resolution.freshness_verified, "verification_basis": resolution.verification_basis,
        "snapshot_fingerprint": resolution.snapshot_fingerprint, "source_issue": resolution.source_issue,
        "latest_source_checkpoint_ref": resolution.latest_source_checkpoint_ref,
        "story_scope_ref": target.get("story_scope_ref"),
        "effective_state_summary": target.get("current_effective_state_summary", target.get("summary")),
        "constraints": {
            "locked": list(target.get("locked_constraints") or []), "preserved": list(target.get("preserved_constraints") or []),
            "revoked": list(target.get("revoked_constraints") or []), "experimental": list(target.get("experimental_constraints") or []),
            "unresolved": list(target.get("unresolved_failures") or []),
        },
        "bound_media_or_reference_refs": list(target.get("bound_media_or_reference_refs") or []),
        "authority_refs": {"canonical_repository": CANONICAL_REPOSITORY, "project_registry": PROJECT_INDEX_PATH.as_posix(), "continuity": CONTINUITY_PATH.as_posix(), "director_method": "01_AI电影系统/AI电影系统.md", "screenplay": "03_剧本与改编/当前改编剧本.md"},
        "authority_boundary": "coordination_projection_only",
    }


def validate_work_item_context_packet(packet: dict[str, Any], *, expected_work_item_id: str) -> bool:
    if not isinstance(packet, dict) or packet.get("packet_type") != "WorkItemContext":
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_INVALID")
    observed, expected = str(packet.get("work_item_id") or "").strip(), str(expected_work_item_id or "").strip()
    if not observed or observed != expected:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_MISMATCH", details={"expected_work_item_id": expected or None, "observed_work_item_id": observed or None})
    if packet.get("freshness_verified") is not True:
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_STALE")
    if not str(packet.get("verification_basis") or "").startswith("canonical_github_readback_") or packet.get("authority_boundary") != "coordination_projection_only":
        raise ActiveWorkItemResolutionError("WORK_ITEM_CONTEXT_PACKET_INVALID")
    return True


def validate_output_work_item(resolution: WorkItemResolution | dict[str, Any], *, loaded_work_item_id: str | None, output_work_item_id: str | None) -> dict[str, Any]:
    receipt = resolution.as_dict() if isinstance(resolution, WorkItemResolution) else dict(resolution)
    if not receipt.get("resolution_required"):
        return {"status": "NOT_REQUIRED", "matched": True}
    ids = [str(receipt.get("resolved_work_item_id") or "").strip(), str(loaded_work_item_id or "").strip(), str(output_work_item_id or "").strip()]
    if any(not value for value in ids) or len(set(ids)) != 1:
        raise ActiveWorkItemResolutionError("WORK_ITEM_OUTPUT_SCOPE_MISMATCH", details={"resolved_work_item_id": ids[0] or None, "loaded_work_item_id": ids[1] or None, "output_work_item_id": ids[2] or None})
    return {"status": "PASS", "matched": True, "work_item_id": ids[0]}


def apply_constraint_ledger(baseline: Iterable[str], *, changed: Iterable[str] = (), preserved: Iterable[str] = (), locked: Iterable[str] = (), revoked: Iterable[str] = ()) -> list[str]:
    state: list[str] = []
    for item in list(baseline) + list(preserved) + list(changed) + list(locked):
        value = str(item).strip()
        if value and value not in state:
            state.append(value)
    revoked_set = {str(item).strip() for item in revoked if str(item).strip()}
    return [item for item in state if item not in revoked_set]


def validate_state_transition(current: str, target: str) -> bool:
    current, target = str(current).strip().upper(), str(target).strip().upper()
    if current not in ALLOWED_TRANSITIONS or target not in ALLOWED_TRANSITIONS[current]:
        raise ActiveWorkItemResolutionError("INVALID_WORK_ITEM_STATE_TRANSITION", details={"current": current, "target": target})
    return True
