"""Canonical public facade for Director Feature Compiler.

The large natural-language parser is frozen in ``_feature_compiler_core_v4``.
This public module owns the trust boundary around that parser:

1. callers cannot inject actor identity;
2. canonical character terms are read through PROJECT_INDEX from this governed
   repository checkout on every public compile;
3. actor-only target relations are revalidated against the subject of the
   specific target-bearing event, never a global same-verb Boolean;
4. camera/actor agency may carry only across bounded continuation syntax and is
   invalidated by an intervening explicit non-agent subject;
5. the facade filters relations emitted by the private parser but never creates
   route IDs, story facts, character identity, or learning authority.

The component remains retrieval-query normalization only. It does not own story,
character, route, learning, camera, map, asset, or continuity truth.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

from . import _feature_compiler_core_v4 as _core
from .entity_semantics import (
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
    "全都", "都", "持续", "始终", "一直", "十分", "非常", "极其", "郑重", "恭敬",
    "虔诚", "先",
)
_SIMPLE_MODIFIERS = tuple(dict.fromkeys(_MANNER_TOKENS + _TEMPORAL_GLUE + _COORDINATION_GLUE))
_FACING_ACTIONS = (
    "转过身朝向", "转过身面向", "转身朝向", "转身面向", "回身朝向", "回身面向",
    "身体朝", "躯干朝", "上身朝", "朝向", "面向", "面朝", "转向", "正对",
)
_GAZE_ACTIONS = (
    "看向", "望向", "盯着", "注视", "视线朝", "目光朝", "观察", "看到", "看见", "见到",
)
_KNEEL_ACTIONS = ("伏地跪拜", "跪着朝", "跪向", "下跪", "跪拜", "拜下", "拜倒", "跪下")
_DIRECTION_PATTERN = re.compile("面朝|朝着|对着|向着|朝|向")
_TARGET_OBJECT_TERMS = (
    "目标", "圣女", "教会", "敌人", "对手", "逃犯", "追兵", "同伴", "陌生人", "凯姆", "蒂娅",
    "她", "他", "孩子", "伤员", "平民", "队友", "门口", "大门", "门", "窗口", "窗户", "舞台", "出口",
)
_TARGET_RELATIONS = {
    "gaze_to_target",
    "facing_to_target",
    "kneeling_to_target",
    "pursuit_to_target",
    "escape_from_target",
    "occlusion_to_target",
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
    """Resolve actor identity only from the governed checkout's PROJECT_INDEX."""

    return load_canonical_character_terms(_MODULE_PROJECT_ROOT)


def _consume_known_tokens(value: str, tokens: tuple[str, ...]) -> bool:
    residual = value.strip().replace(" ", "")
    ordered = tuple(sorted(set(tokens), key=len, reverse=True))
    changed = True
    while changed and residual:
        changed = False
        for token in ordered:
            if residual.startswith(token):
                residual = residual[len(token):]
                changed = True
                break
    return not residual


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
    """Accept only positively known bounded modifier syntax.

    In particular, arbitrary CJK ``...地`` is never sufficient. A ``地`` tail
    is admitted only when the stem can be fully segmented into the finite manner
    vocabulary above, so ordinary nouns such as ``出生地`` cannot be stripped to
    expose a preceding actor token.
    """

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
        if normalized == term:
            return True
        if normalized.startswith(term) and _modifier_tail(normalized[len(term):]):
            return True
    return False


def _body_leader(value: str) -> bool:
    normalized = _strip_leading_glue(value)
    for term in _BODY_TERMS:
        if normalized == term:
            return True
        if normalized.startswith(term) and _modifier_tail(normalized[len(term):]):
            return True
    return False


def _classify_explicit_leader(
    value: str,
    *,
    canonical_terms: tuple[str, ...],
    action: str,
) -> str:
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


def _last_direction_marker(prefix: str) -> tuple[int, str] | None:
    """Return the last non-overlapping longest-first directional marker."""

    matches = list(_DIRECTION_PATTERN.finditer(prefix))
    if not matches:
        return None
    match = matches[-1]
    return match.start(), match.group(0)


def _event_hits(clause: str) -> list[tuple[int, int, str, str]]:
    """Return non-overlapping observable events as (start, end, kind, action)."""

    raw: list[tuple[int, int, str, str]] = []
    for kind, actions in (
        ("gaze", _GAZE_ACTIONS),
        ("kneel", _KNEEL_ACTIONS),
        ("facing", _FACING_ACTIONS),
    ):
        pattern = re.compile("|".join(re.escape(action) for action in sorted(actions, key=len, reverse=True)))
        for match in pattern.finditer(clause):
            raw.append((match.start(), match.end(), kind, match.group(0)))
    raw.sort(key=lambda item: (item[0], -(item[1] - item[0]), {"gaze": 0, "kneel": 1, "facing": 2}[item[2]]))

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
    marker_pos, marker_text = marker
    target_phrase = prefix[marker_pos + len(marker_text):]
    return _contains_target(target_phrase), prefix[:marker_pos]


def _continuation_segment_allows_inherit(value: str) -> bool:
    """Allow only target NP + temporal/coordination glue between two events.

    This is intentionally narrower than natural-language parsing. It exists only
    to preserve already-emitted core relations such as ``看到圣女后跪拜`` while
    refusing residual subject material such as ``雕像``.
    """

    residual = value.strip().replace(" ", "")
    if not residual:
        return True

    ordered_targets = tuple(sorted(set(_TARGET_OBJECT_TERMS), key=len, reverse=True))
    ordered_glue = tuple(sorted(set(_TEMPORAL_GLUE + _COORDINATION_GLUE + _MANNER_TOKENS), key=len, reverse=True))
    changed = True
    while changed and residual:
        changed = False
        for token in ordered_targets + ordered_glue:
            if residual.startswith(token):
                residual = residual[len(token):]
                changed = True
                break
    return not residual


def _clause_starts_camera(clause: str) -> bool:
    normalized = _strip_leading_glue(clause)
    return any(normalized.startswith(term) for term in _CAMERA_TERMS)


def _scan_actor_event_support(
    text: str,
    *,
    canonical_terms: tuple[str, ...],
) -> dict[str, bool]:
    """Bind actor evidence to the exact target-bearing event.

    ``*_observable`` records legitimate actor motion/gaze independent of target.
    ``*_target`` is stronger: the same event must have ACTOR agency and bounded
    target evidence (direct, preposed, or a tightly bounded carry from a prior
    actor target event). A valid actor event elsewhere cannot authorize a
    nonhuman target event of the same verb kind.
    """

    support = {
        "facing_observable": False,
        "facing_target": False,
        "gaze_observable": False,
        "gaze_target": False,
        "kneel_observable": False,
        "kneel_target": False,
    }
    last_agent: str | None = None
    last_event_was_actor_target = False
    first_clause = True

    clauses = [part.strip() for part in _CLAUSE_SPLIT.split(text) if part.strip()]
    for clause in clauses:
        events = _event_hits(clause)
        if not events:
            if _clause_starts_camera(clause):
                last_agent = "CAMERA"
            elif obvious_non_agent_subject_prefix(
                clause,
                known_actor_terms=canonical_terms,
                max_chars=24,
            ):
                last_agent = None
                last_event_was_actor_target = False
            first_clause = False
            continue

        previous_end = 0
        clause_agent: str | None = None
        clause_target_seen = False
        for index, (start, end, kind, action) in enumerate(events):
            before_event = clause[previous_end:start]
            after_event = clause[end: events[index + 1][0] if index + 1 < len(events) else len(clause)]
            leader = before_event
            preposed_target = False
            if kind == "kneel":
                preposed_target, leader = _preposed_target_and_leader(before_event)

            classified = _classify_explicit_leader(
                leader,
                canonical_terms=canonical_terms,
                action=action,
            )
            explicit = classified != "EMPTY"
            agent_class = classified

            if classified == "EMPTY":
                if clause_agent in {"ACTOR", "CAMERA"}:
                    agent_class = clause_agent
                elif last_agent in {"ACTOR", "CAMERA"}:
                    agent_class = last_agent
                elif first_clause:
                    # A bare first-clause directive such as “朝向圣女” is a
                    # legitimate blocking imperative. It still cannot override a
                    # previously proven camera clause because that is inherited above.
                    agent_class = "ACTOR"
                else:
                    agent_class = "UNKNOWN"
            elif classified == "OTHER" and clause_agent in {"ACTOR", "CAMERA"}:
                # Same-clause agency may continue only when the material between
                # events is itself bounded target/glue syntax. Residual subject
                # nouns never borrow the previous event's actor class.
                if _continuation_segment_allows_inherit(before_event):
                    agent_class = clause_agent
                    explicit = False

            direct_target = _contains_target(after_event)
            carried_target = bool(
                agent_class == "ACTOR"
                and (clause_target_seen or last_event_was_actor_target)
                and _continuation_segment_allows_inherit(before_event)
            )
            event_target = bool(preposed_target or direct_target or (kind == "kneel" and carried_target))

            if agent_class == "ACTOR":
                support[f"{kind}_observable"] = True
                if event_target:
                    support[f"{kind}_target"] = True

            if agent_class in {"ACTOR", "CAMERA"}:
                clause_agent = agent_class
            elif explicit:
                # A new explicit OTHER subject terminates local agency. This is
                # the key boundary preventing “群众下跪，雕像...跪下” style loans.
                clause_agent = None

            if explicit:
                if agent_class in {"ACTOR", "CAMERA"}:
                    last_agent = agent_class
                elif agent_class == "OTHER":
                    last_agent = None
                    last_event_was_actor_target = False

            if agent_class == "ACTOR" and event_target:
                clause_target_seen = True
                last_event_was_actor_target = True
            elif agent_class != "ACTOR" and event_target:
                last_event_was_actor_target = False

            previous_end = end

        first_clause = False
    return support


def _sanitize_actor_target_relations(
    task: str,
    features: DirectorFeatures,
    *,
    canonical_terms: tuple[str, ...],
) -> tuple[DirectorFeatures, bool]:
    support = _scan_actor_event_support(task, canonical_terms=canonical_terms)

    relation = list(features.relation_type)
    dramatic = list(features.dramatic_function)
    spatial = list(features.spatial_action_features)
    failure = list(features.failure_mechanism)
    matched_rules = list(features.matched_rules)
    semantic_trace = list(features.semantic_trace)
    filtered = False
    removed_facing = False
    removed_gaze = False
    removed_kneel = False

    if "facing_to_target" in relation and not support["facing_target"]:
        relation = [value for value in relation if value != "facing_to_target"]
        removed_facing = True
        filtered = True
    if "gaze_to_target" in relation and not support["gaze_target"]:
        relation = [value for value in relation if value != "gaze_to_target"]
        failure = [value for value in failure if value != "gaze_target_spatial_binding_fail"]
        removed_gaze = True
        filtered = True
    if "kneeling_to_target" in relation and not support["kneel_target"]:
        relation = [value for value in relation if value != "kneeling_to_target"]
        spatial = [value for value in spatial if value != "kneeling_to_target"]
        removed_kneel = True
        filtered = True

    if not any(value in _BODY_RELATIONS for value in relation):
        failure = [value for value in failure if value != "body_orientation_target_fail"]
        if (removed_facing or removed_kneel) and not (
            support["facing_observable"] or support["kneel_observable"]
        ):
            spatial = [value for value in spatial if value != "body_orientation"]

    if removed_gaze and not support["gaze_observable"]:
        spatial = [value for value in spatial if value != "gaze_direction"]

    if not any(value in _TARGET_RELATIONS for value in relation):
        dramatic = [value for value in dramatic if value != "target_oriented_action"]
        spatial = [value for value in spatial if value != "locatable_target"]

    if filtered:
        matched_rules.append("actor_subject_safety_filter")
        semantic_trace.append("EntitySemantics.per_target_event_subject_boundary")

    sanitized = DirectorFeatures(
        dramatic_function=_dedupe(dramatic),
        relation_type=_dedupe(relation),
        spatial_action_features=_dedupe(spatial),
        failure_mechanism=_dedupe(failure),
        semantic_trace=_dedupe(semantic_trace),
        matched_rules=_dedupe(matched_rules),
    )
    return sanitized, filtered


def compile_director_features(
    task: str,
    *,
    strict: bool = True,
) -> DirectorFeatures:
    """Compile director language with canonical, non-injectable actor semantics."""

    if not isinstance(task, str) or not task.strip():
        raise FeatureCompilationError("EMPTY_DIRECTOR_TASK")

    canonical_terms = _canonical_actor_terms()
    parsed = _core.compile_director_features(
        task,
        strict=False,
        known_actor_terms=canonical_terms,
    )
    result, _ = _sanitize_actor_target_relations(
        task,
        parsed,
        canonical_terms=canonical_terms,
    )
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
    parsed = _core.compile_director_features(
        description,
        strict=False,
        known_actor_terms=canonical_terms,
    )
    features, filtered = _sanitize_actor_target_relations(
        description,
        parsed,
        canonical_terms=canonical_terms,
    )
    if strict and not features.recognized:
        raise FeatureCompilationError("NO_RECOGNIZED_DIRECTOR_FEATURES")

    task = dict(base_task or {})
    task["task_id"] = str(task.get("task_id") or task_id)
    for key, compiled in features.as_dict().items():
        task[key] = _merge(task.get(key), compiled)
    try:
        task["hard_routes"] = resolve_hard_routes(
            task,
            route_data,
            description=description,
        )
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
        "actor_subject_binding": "per_target_event_v2",
        "actor_subject_safety_filtered": filtered,
        "matched_rules": list(features.matched_rules),
        "semantic_trace": list(features.semantic_trace),
        "route_resolution": "director_route_index",
        "hard_routes": list(task["hard_routes"]),
        "authority_boundary": "retrieval_query_only",
    }
    return task
