"""Canonical public facade for Director Feature Compiler.

The large natural-language parser is frozen in ``_feature_compiler_core_v4``.
This facade owns only the actor/camera trust boundary around relations already
emitted by that parser. It never creates route IDs, story facts, character truth,
or learning authority.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

from . import _feature_compiler_core_v4 as _core
from .entity_semantics import (
    HUMAN_ROLE_HEADS,
    PRONOUN_AGENT_TERMS,
    bounded_animate_agent_leader,
    load_canonical_character_terms,
    obvious_non_agent_subject_prefix,
)
from .route_resolver import RouteResolutionError, resolve_hard_routes

FEATURE_KEYS = _core.FEATURE_KEYS
SOAC_SCHEMA_PATH = _core.SOAC_SCHEMA_PATH
DirectorFeatures = _core.DirectorFeatures
FeatureCompilationError = _core.FeatureCompilationError
validate_semantic_dependencies = _core.validate_semantic_dependencies

_MODULE_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CAMERA_TERMS = ("摄影机", "摄像机", "镜头", "机位", "camera")
_BODY_TERMS = ("身体", "躯干", "上身")
_TEMPORAL_GLUE = (
    "随后", "随即", "然后", "接着", "继而", "于是", "立刻", "马上", "之后", "后", "再", "又", "便",
)
_COORDINATION_GLUE = ("并且", "并", "且", "而后", "接下来")
_MANNER_TOKENS = (
    "突然", "缓缓", "慢慢", "迅速", "立刻", "马上", "纷纷", "共同", "一起", "一同",
    "全都", "都", "持续", "始终", "一直", "十分", "非常", "极其", "郑重", "恭敬", "虔诚", "先",
)
_SIMPLE_MODIFIERS = tuple(dict.fromkeys(_MANNER_TOKENS + _TEMPORAL_GLUE + _COORDINATION_GLUE))
_TARGET_PREFIX_MODIFIERS = (
    "高台上的", "台上的", "门口的", "远处的", "前方的", "附近的",
    "那位", "这位", "一位", "那名", "这名", "一名", "那个", "这个", "一个",
)
_FACING_ACTIONS = (
    "转过身朝向", "转过身面向", "转身朝向", "转身面向", "回身朝向", "回身面向",
    "身体朝", "躯干朝", "上身朝", "朝向", "面向", "面朝", "转向", "正对",
)
_GAZE_ACTIONS = ("看向", "望向", "盯着", "注视", "视线朝", "目光朝", "观察", "看到", "看见", "见到")
_KNEEL_ACTIONS = ("伏地跪拜", "跪着朝", "跪向", "下跪", "跪拜", "拜下", "拜倒", "跪下")
_DIRECTION_PATTERN = re.compile("面朝|朝着|对着|向着|朝|向")
_TARGET_OBJECT_TERMS = (
    "目标", "圣女", "教会", "敌人", "对手", "逃犯", "追兵", "同伴", "陌生人", "凯姆", "蒂娅",
    "她", "他", "孩子", "伤员", "平民", "队友", "门口", "大门", "门", "窗口", "窗户", "舞台", "出口",
)
_TARGET_RELATIONS = {
    "gaze_to_target", "facing_to_target", "kneeling_to_target",
    "pursuit_to_target", "escape_from_target", "occlusion_to_target",
}
_BODY_RELATIONS = {"facing_to_target", "kneeling_to_target", "pursuit_to_target"}
_CLAUSE_SPLIT = re.compile(r"[，。；！？,;!?]+")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _merge(existing: Any, compiled: list[str]) -> list[str]:
    if existing is None:
        current: list[str] = []
    elif isinstance(existing, (list, tuple, set)):
        current = [str(value) for value in existing]
    else:
        current = [str(existing)]
    return _dedupe(current + compiled)


def _canonical_actor_terms() -> tuple[str, ...]:
    return load_canonical_character_terms(_MODULE_PROJECT_ROOT)


def _consume_known_tokens(value: str, tokens: tuple[str, ...]) -> bool:
    residual = value.strip().replace(" ", "")
    ordered = tuple(sorted(set(tokens), key=len, reverse=True))
    while residual:
        for token in ordered:
            if residual.startswith(token):
                residual = residual[len(token):]
                break
        else:
            return False
    return True


def _strip_leading_glue(value: str) -> str:
    residual = value.strip().replace(" ", "")
    ordered = tuple(sorted(set(_TEMPORAL_GLUE + _COORDINATION_GLUE), key=len, reverse=True))
    changed = True
    while changed and residual:
        changed = False
        for token in ordered:
            if residual.startswith(token):
                residual = residual[len(token):]
                changed = True
                break
    return residual


def _modifier_tail(value: str) -> bool:
    """Positive-only modifier grammar; arbitrary ``...地`` is never enough."""
    residual = value.strip().replace(" ", "")
    if not residual:
        return True
    if residual.endswith("地"):
        stem = residual[:-1]
        return bool(stem and _consume_known_tokens(stem, _MANNER_TOKENS))
    return _consume_known_tokens(residual, _SIMPLE_MODIFIERS)


def _camera_leader(value: str) -> bool:
    normalized = _strip_leading_glue(value)
    for term in _CAMERA_TERMS:
        if normalized == term or (
            normalized.startswith(term) and _modifier_tail(normalized[len(term):])
        ):
            return True
    return False


def _body_leader(value: str) -> bool:
    normalized = _strip_leading_glue(value)
    for term in _BODY_TERMS:
        if normalized == term or (
            normalized.startswith(term) and _modifier_tail(normalized[len(term):])
        ):
            return True
    return False


def _classify_explicit_leader(value: str, *, canonical_terms: tuple[str, ...], action: str) -> str:
    normalized = _strip_leading_glue(value)
    if not normalized:
        return "EMPTY"
    if _camera_leader(normalized):
        return "CAMERA"
    if _body_leader(normalized):
        return "ACTOR"
    if bounded_animate_agent_leader(
        normalized,
        action=action,
        known_actor_terms=canonical_terms,
        modifier_tail_validator=_modifier_tail,
        max_chars=28,
    ):
        return "ACTOR"
    return "OTHER"


def _actor_identity_key(value: str, *, canonical_terms: tuple[str, ...], action: str) -> str | None:
    """Return the actor token nearest the event after actorhood is positively proven.

    This is continuity identity for parser carry only, not canonical character
    identity. Different aliases are intentionally not merged here: when wording
    changes identity token, cross-event carry fails closed rather than guessing.
    """
    normalized = _strip_leading_glue(value)
    if not normalized or _camera_leader(normalized) or _body_leader(normalized):
        return None
    if not bounded_animate_agent_leader(
        normalized,
        action=action,
        known_actor_terms=canonical_terms,
        modifier_tail_validator=_modifier_tail,
        max_chars=28,
    ):
        return None

    terms = tuple(
        sorted(
            set(canonical_terms) | set(HUMAN_ROLE_HEADS) | set(PRONOUN_AGENT_TERMS),
            key=len,
            reverse=True,
        )
    )
    hits: list[tuple[int, int, str]] = []
    for term in terms:
        forms = (term, f"{term}们") if not term.endswith("们") else (term,)
        for form in forms:
            for match in re.finditer(re.escape(form), normalized):
                hits.append((match.end(), len(form), form))
    if not hits:
        return None
    _, _, form = max(hits, key=lambda item: (item[0], item[1]))
    return f"ACTOR::{form}"


def _leading_actor_identity_from_clause(clause: str, *, canonical_terms: tuple[str, ...]) -> str | None:
    """Recognize a bounded actor subject in a clause with no tracked event.

    This is used only to invalidate stale agency. It does not create any feature.
    """
    normalized = _strip_leading_glue(clause)
    bounded = normalized[:28]
    found: str | None = None
    for end in range(1, len(bounded) + 1):
        candidate = bounded[:end]
        identity = _actor_identity_key(candidate, canonical_terms=canonical_terms, action="")
        if identity is not None:
            found = identity
    return found


def _last_direction_marker(prefix: str) -> tuple[int, str] | None:
    matches = list(_DIRECTION_PATTERN.finditer(prefix))
    if not matches:
        return None
    match = matches[-1]
    return match.start(), match.group(0)


def _event_hits(clause: str) -> list[tuple[int, int, str, str]]:
    raw: list[tuple[int, int, str, str]] = []
    for kind, actions in (("gaze", _GAZE_ACTIONS), ("kneel", _KNEEL_ACTIONS), ("facing", _FACING_ACTIONS)):
        pattern = re.compile("|".join(re.escape(x) for x in sorted(actions, key=len, reverse=True)))
        for match in pattern.finditer(clause):
            raw.append((match.start(), match.end(), kind, match.group(0)))
    raw.sort(key=lambda x: (x[0], -(x[1] - x[0]), {"gaze": 0, "kneel": 1, "facing": 2}[x[2]]))
    events: list[tuple[int, int, str, str]] = []
    consumed_until = -1
    for event in raw:
        if event[0] < consumed_until:
            continue
        events.append(event)
        consumed_until = event[1]
    return events


def _contains_target(value: str) -> bool:
    normalized = value.strip().replace(" ", "")
    return any(term in normalized for term in _TARGET_OBJECT_TERMS)


def _preposed_target_and_leader(prefix: str) -> tuple[bool, str]:
    marker = _last_direction_marker(prefix)
    if marker is None:
        return False, prefix
    pos, text = marker
    return _contains_target(prefix[pos + len(text):]), prefix[:pos]


def _continuation_segment_allows_inherit(value: str) -> bool:
    """Allow only bounded target phrase + temporal/coordination syntax."""
    residual = value.strip().replace(" ", "")
    if not residual:
        return True
    if _consume_known_tokens(
        residual,
        tuple(dict.fromkeys(_TARGET_OBJECT_TERMS + _TEMPORAL_GLUE + _COORDINATION_GLUE + _MANNER_TOKENS)),
    ):
        return True

    for target in sorted(set(_TARGET_OBJECT_TERMS), key=len, reverse=True):
        pos = residual.find(target)
        if pos < 0:
            continue
        prefix = residual[:pos]
        suffix = residual[pos + len(target):]
        prefix_ok = not prefix or _consume_known_tokens(prefix, _TARGET_PREFIX_MODIFIERS)
        suffix_ok = not suffix or _consume_known_tokens(
            suffix,
            tuple(dict.fromkeys(_TEMPORAL_GLUE + _COORDINATION_GLUE + _MANNER_TOKENS)),
        )
        if prefix_ok and suffix_ok:
            return True
    return False


def _clause_starts_camera(clause: str) -> bool:
    normalized = _strip_leading_glue(clause)
    return any(normalized.startswith(term) for term in _CAMERA_TERMS)


def _scan_actor_event_support(text: str, *, canonical_terms: tuple[str, ...]) -> dict[str, bool]:
    """Bind target evidence to both the specific event and the specific actor token."""
    support = {
        "facing_observable": False, "facing_target": False,
        "gaze_observable": False, "gaze_target": False,
        "kneel_observable": False, "kneel_target": False,
    }
    last_agent: str | None = None
    last_actor_identity: str | None = None
    last_target_actor_identity: str | None = None
    first_clause = True

    clauses = [part.strip() for part in _CLAUSE_SPLIT.split(text) if part.strip()]
    for clause in clauses:
        events = _event_hits(clause)
        if not events:
            if _clause_starts_camera(clause):
                last_agent = "CAMERA"
                last_actor_identity = None
                last_target_actor_identity = None
            else:
                intervening_actor = _leading_actor_identity_from_clause(
                    clause, canonical_terms=canonical_terms
                )
                if intervening_actor is not None:
                    last_agent = "ACTOR"
                    last_actor_identity = intervening_actor
                    last_target_actor_identity = None
                elif obvious_non_agent_subject_prefix(
                    clause, known_actor_terms=canonical_terms, max_chars=24
                ):
                    last_agent = None
                    last_actor_identity = None
                    last_target_actor_identity = None
            first_clause = False
            continue

        previous_end = 0
        clause_agent: str | None = None
        clause_actor_identity: str | None = None
        clause_target_actor_identity: str | None = None
        unbound_actor_kneel_identity: str | None = None

        for index, (start, end, kind, action) in enumerate(events):
            before_event = clause[previous_end:start]
            after_event = clause[end: events[index + 1][0] if index + 1 < len(events) else len(clause)]
            leader = before_event
            preposed_target = False
            if kind == "kneel":
                preposed_target, leader = _preposed_target_and_leader(before_event)

            classified = _classify_explicit_leader(
                leader, canonical_terms=canonical_terms, action=action
            )
            explicit = classified != "EMPTY"
            explicit_actor_identity = (
                _actor_identity_key(leader, canonical_terms=canonical_terms, action=action)
                if classified == "ACTOR"
                else None
            )
            agent_class = classified
            actor_identity = explicit_actor_identity

            if classified == "EMPTY":
                if clause_agent in {"ACTOR", "CAMERA"}:
                    agent_class = clause_agent
                    actor_identity = clause_actor_identity if clause_agent == "ACTOR" else None
                elif last_agent in {"ACTOR", "CAMERA"}:
                    agent_class = last_agent
                    actor_identity = last_actor_identity if last_agent == "ACTOR" else None
                elif first_clause:
                    agent_class = "ACTOR"  # bounded bare director imperative
                    actor_identity = None
                else:
                    agent_class = "UNKNOWN"
            elif classified == "OTHER" and clause_agent in {"ACTOR", "CAMERA"}:
                if _continuation_segment_allows_inherit(before_event):
                    agent_class = clause_agent
                    actor_identity = clause_actor_identity if clause_agent == "ACTOR" else None
                    explicit = False
            elif classified == "ACTOR" and actor_identity is None:
                # Body-part wording can be explicit ACTOR syntax without naming a
                # new actor; bind it only to an already-proven local/previous actor.
                if clause_agent == "ACTOR":
                    actor_identity = clause_actor_identity
                elif last_agent == "ACTOR":
                    actor_identity = last_actor_identity

            if (
                explicit
                and agent_class == "ACTOR"
                and actor_identity is not None
                and clause_actor_identity is not None
                and actor_identity != clause_actor_identity
            ):
                # A new explicit person cancels deferred evidence owned by the
                # previous actor within this coordinated clause.
                unbound_actor_kneel_identity = None
                clause_target_actor_identity = None

            direct_target = _contains_target(after_event)
            carry_syntax = _continuation_segment_allows_inherit(before_event)
            if (
                index == 0
                and agent_class == "ACTOR"
                and explicit
                and actor_identity is not None
                and actor_identity == last_target_actor_identity
            ):
                # Only a genuinely repeated actor may cross the separator when
                # the private core already emitted the relation.
                carry_syntax = True

            carry_from_clause = bool(
                actor_identity is not None
                and actor_identity == clause_target_actor_identity
            )
            carry_from_previous_clause = bool(
                actor_identity is not None
                and actor_identity == last_target_actor_identity
            )
            carried_target = bool(
                agent_class == "ACTOR"
                and carry_syntax
                and (carry_from_clause or carry_from_previous_clause)
            )
            event_target = bool(
                preposed_target or direct_target or (kind == "kneel" and carried_target)
            )

            if agent_class == "ACTOR":
                support[f"{kind}_observable"] = True
                if event_target:
                    support[f"{kind}_target"] = True
                elif kind == "kneel" and actor_identity is not None:
                    unbound_actor_kneel_identity = actor_identity

            # A later facing target may bind only a pending kneel owned by the
            # exact same actor, never merely another ACTOR-class subject.
            if (
                kind == "facing"
                and agent_class == "ACTOR"
                and event_target
                and actor_identity is not None
                and actor_identity == unbound_actor_kneel_identity
                and not explicit
            ):
                support["kneel_target"] = True

            if agent_class in {"ACTOR", "CAMERA"}:
                clause_agent = agent_class
                clause_actor_identity = actor_identity if agent_class == "ACTOR" else None
            elif explicit:
                clause_agent = None
                clause_actor_identity = None
                unbound_actor_kneel_identity = None
                clause_target_actor_identity = None

            if explicit:
                if agent_class in {"ACTOR", "CAMERA"}:
                    last_agent = agent_class
                    last_actor_identity = actor_identity if agent_class == "ACTOR" else None
                else:
                    last_agent = None
                    last_actor_identity = None
                    last_target_actor_identity = None

            if agent_class == "ACTOR" and event_target and actor_identity is not None:
                clause_target_actor_identity = actor_identity
                last_target_actor_identity = actor_identity
            elif explicit and agent_class == "ACTOR" and not event_target:
                # An explicit non-target actor event interrupts older target
                # carry, even if the actor happens to share the same class.
                last_target_actor_identity = None
            elif agent_class != "ACTOR" and event_target:
                last_target_actor_identity = None

            previous_end = end
        first_clause = False
    return support


def _sanitize_actor_target_relations(
    task: str, features: DirectorFeatures, *, canonical_terms: tuple[str, ...]
) -> tuple[DirectorFeatures, bool]:
    support = _scan_actor_event_support(task, canonical_terms=canonical_terms)
    relation = list(features.relation_type)
    dramatic = list(features.dramatic_function)
    spatial = list(features.spatial_action_features)
    failure = list(features.failure_mechanism)
    matched_rules = list(features.matched_rules)
    semantic_trace = list(features.semantic_trace)
    filtered = False
    removed_facing = removed_gaze = removed_kneel = False

    if "facing_to_target" in relation and not support["facing_target"]:
        relation = [x for x in relation if x != "facing_to_target"]
        removed_facing = filtered = True
    if "gaze_to_target" in relation and not support["gaze_target"]:
        relation = [x for x in relation if x != "gaze_to_target"]
        failure = [x for x in failure if x != "gaze_target_spatial_binding_fail"]
        removed_gaze = filtered = True
    if "kneeling_to_target" in relation and not support["kneel_target"]:
        relation = [x for x in relation if x != "kneeling_to_target"]
        spatial = [x for x in spatial if x != "kneeling_to_target"]
        removed_kneel = filtered = True

    if not any(x in _BODY_RELATIONS for x in relation):
        failure = [x for x in failure if x != "body_orientation_target_fail"]
        if (removed_facing or removed_kneel) and not (
            support["facing_observable"] or support["kneel_observable"]
        ):
            spatial = [x for x in spatial if x != "body_orientation"]
    if removed_gaze and not support["gaze_observable"]:
        spatial = [x for x in spatial if x != "gaze_direction"]
    if not any(x in _TARGET_RELATIONS for x in relation):
        dramatic = [x for x in dramatic if x != "target_oriented_action"]
        spatial = [x for x in spatial if x != "locatable_target"]

    if filtered:
        matched_rules.append("actor_subject_safety_filter")
        semantic_trace.append("EntitySemantics.per_target_event_actor_identity_boundary")

    return DirectorFeatures(
        dramatic_function=_dedupe(dramatic),
        relation_type=_dedupe(relation),
        spatial_action_features=_dedupe(spatial),
        failure_mechanism=_dedupe(failure),
        semantic_trace=_dedupe(semantic_trace),
        matched_rules=_dedupe(matched_rules),
    ), filtered


def compile_director_features(task: str, *, strict: bool = True) -> DirectorFeatures:
    if not isinstance(task, str) or not task.strip():
        raise FeatureCompilationError("EMPTY_DIRECTOR_TASK")
    canonical_terms = _canonical_actor_terms()
    parsed = _core.compile_director_features(task, strict=False, known_actor_terms=canonical_terms)
    result, _ = _sanitize_actor_target_relations(task, parsed, canonical_terms=canonical_terms)
    if strict and not result.recognized:
        raise FeatureCompilationError("NO_RECOGNIZED_DIRECTOR_FEATURES")
    return result


def compile_retrieval_task(
    description: str,
    *,
    task_id: str = "UNSPECIFIED_TASK",
    base_task: dict[str, Any] | None = None,
    route_data: dict[str, Any] | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    canonical_terms = _canonical_actor_terms()
    parsed = _core.compile_director_features(description, strict=False, known_actor_terms=canonical_terms)
    features, filtered = _sanitize_actor_target_relations(description, parsed, canonical_terms=canonical_terms)
    if strict and not features.recognized:
        raise FeatureCompilationError("NO_RECOGNIZED_DIRECTOR_FEATURES")

    task = dict(base_task or {})
    task["task_id"] = str(task.get("task_id") or task_id)
    for key, compiled in features.as_dict().items():
        task[key] = _merge(task.get(key), compiled)
    try:
        task["hard_routes"] = resolve_hard_routes(task, route_data, description=description)
    except RouteResolutionError as exc:
        raise FeatureCompilationError(str(exc)) from exc

    task["feature_compiler_receipt"] = {
        "component": "DIRECTOR_FEATURE_COMPILER_V1_1",
        "status": "PASS" if features.recognized else "FAIL",
        "input_fingerprint": hashlib.sha256(description.encode("utf-8")).hexdigest()[:16],
        "compiled_feature_keys": [key for key in FEATURE_KEYS if getattr(features, key)],
        "known_actor_terms_count": len(canonical_terms),
        "actor_terms_source": "PROJECT_INDEX.canonical.character_db",
        "caller_actor_terms_supported": False,
        "actor_subject_binding": "per_target_event_actor_identity_v3",
        "actor_subject_safety_filtered": filtered,
        "matched_rules": list(features.matched_rules),
        "semantic_trace": list(features.semantic_trace),
        "route_resolution": "director_route_index",
        "hard_routes": list(task["hard_routes"]),
        "authority_boundary": "retrieval_query_only",
    }
    return task
