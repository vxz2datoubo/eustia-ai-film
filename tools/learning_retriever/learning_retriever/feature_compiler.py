"""Canonical public facade for Director Feature Compiler.

The large natural-language parser is frozen in ``_feature_compiler_core_v4``.
This public module owns the trust boundary around that parser:

1. callers cannot inject actor identity;
2. canonical character terms are read through PROJECT_INDEX from this governed
   repository checkout on every public compile;
3. actor-only target relations are revalidated against bounded subject evidence
   before Hard Route resolution;
4. camera agency is preserved across elliptical follow-up clauses;
5. already-proven same-clause agency may carry across coordinated actions, but
   the facade never creates a target relation that the private parser did not emit.

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
    NON_ADVERBIAL_DI_ENDINGS,
    bounded_animate_agent_leader,
    load_canonical_character_terms,
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
    "随后", "随即", "然后", "接着", "继而", "于是", "立刻", "马上", "再", "又", "便",
)
_SIMPLE_MODIFIERS = (
    "突然", "缓缓", "慢慢", "迅速", "立刻", "马上", "纷纷", "共同", "一起", "一同",
    "全都", "都", "持续", "始终", "一直", "十分", "非常", "极其", "郑重", "恭敬",
    "虔诚", "随后", "随即", "然后", "接着", "继而", "于是", "再", "又", "便", "先",
)
_FACING_ACTIONS = (
    "转过身朝向", "转过身面向", "转身朝向", "转身面向", "回身朝向", "回身面向",
    "身体朝", "躯干朝", "上身朝", "朝向", "面向", "转向", "正对",
)
_GAZE_ACTIONS = (
    "看向", "望向", "盯着", "注视", "视线朝", "目光朝", "观察", "看到", "看见", "见到",
)
_KNEEL_ACTIONS = ("伏地跪拜", "跪着朝", "跪向", "下跪", "跪拜", "拜下", "拜倒", "跪下")
_DIRECTION_MARKERS = ("面朝", "朝着", "对着", "向着", "朝", "向")
_DIRECTION_PATTERN = re.compile("面朝|朝着|对着|向着|朝|向")
_TARGET_RELATIONS = {
    "gaze_to_target",
    "facing_to_target",
    "kneeling_to_target",
    "pursuit_to_target",
    "escape_from_target",
    "occlusion_to_target",
}
_BODY_RELATIONS = {"facing_to_target", "kneeling_to_target", "pursuit_to_target"}


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


def _strip_temporal_glue(value: str) -> str:
    residual = value.strip()
    changed = True
    while changed and residual:
        changed = False
        for token in _TEMPORAL_GLUE:
            if residual.startswith(token):
                residual = residual[len(token):].strip()
                changed = True
                break
    return residual


def _modifier_tail(value: str) -> bool:
    residual = value.strip().replace(" ", "")
    if not residual:
        return True
    if any(residual.endswith(token) for token in NON_ADVERBIAL_DI_ENDINGS):
        return False
    if residual.endswith("地"):
        stem = residual[:-1]
        return bool(
            2 <= len(stem) <= 8
            and all("\u4e00" <= char <= "\u9fff" for char in stem)
        )
    changed = True
    while changed and residual:
        changed = False
        for token in sorted(_SIMPLE_MODIFIERS, key=len, reverse=True):
            if residual.startswith(token):
                residual = residual[len(token):]
                changed = True
                break
    return not residual


def _camera_leader(value: str) -> bool:
    normalized = value.strip().replace(" ", "")
    for term in _CAMERA_TERMS:
        if normalized == term:
            return True
        if normalized.startswith(term) and _modifier_tail(normalized[len(term):]):
            return True
    return False


def _body_leader(value: str) -> bool:
    normalized = value.strip().replace(" ", "")
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
    normalized = _strip_temporal_glue(value)
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
        max_chars=24,
    ):
        return "ACTOR"
    return "OTHER"


def _first_action(clause: str, actions: tuple[str, ...]) -> tuple[int, str] | None:
    hits: list[tuple[int, int, str]] = []
    for action in actions:
        pos = clause.find(action)
        if pos >= 0:
            hits.append((pos, -len(action), action))
    if not hits:
        return None
    pos, _, action = min(hits)
    return pos, action


def _last_direction_marker(prefix: str) -> tuple[int, str] | None:
    """Return the last non-overlapping directional marker.

    Regex alternation is longest-first, so ``面朝`` is one marker rather than an
    outer ``面朝`` plus a later overlapping bare ``朝``. The same boundary keeps
    ``朝着``/``向着`` intact before subject validation.
    """

    matches = list(_DIRECTION_PATTERN.finditer(prefix))
    if not matches:
        return None
    match = matches[-1]
    return match.start(), match.group(0)


def _resolve_agent_class(
    leader: str,
    *,
    action: str,
    canonical_terms: tuple[str, ...],
    last_agent: str | None,
    first_clause: bool,
) -> tuple[str, bool]:
    """Return (agent_class, explicit_leader_present)."""

    classified = _classify_explicit_leader(
        leader,
        canonical_terms=canonical_terms,
        action=action,
    )
    if classified != "EMPTY":
        return classified, True
    if last_agent in {"ACTOR", "CAMERA"}:
        return last_agent, False
    if first_clause:
        return "ACTOR", False
    return "UNKNOWN", False


def _scan_actor_subject_support(
    text: str,
    *,
    canonical_terms: tuple[str, ...],
) -> dict[str, bool]:
    """Validate actor observables without reparsing target semantics.

    The private core still decides whether a gaze/facing/kneel relation exists.
    This scan answers only whether the relevant observable has a proven ACTOR
    subject. A proven ACTOR/CAMERA may carry through later coordinated actions in
    the same clause; across clauses only the last explicitly proven agency may be
    inherited by an empty/temporal-glue leader.
    """

    support = {"facing": False, "gaze": False, "kneel": False}
    last_agent: str | None = None
    first_clause = True

    clauses = [
        part.strip()
        for part in re.split(r"[，。；！？,;!?]+", text)
        if part.strip()
    ]
    for clause in clauses:
        event_hits: list[tuple[int, str, str]] = []
        for kind, actions in (
            ("facing", _FACING_ACTIONS),
            ("gaze", _GAZE_ACTIONS),
            ("kneel", _KNEEL_ACTIONS),
        ):
            hit = _first_action(clause, actions)
            if hit:
                event_hits.append((hit[0], kind, hit[1]))
        if not event_hits:
            first_clause = False
            continue

        clause_agent: str | None = None
        seen_event = False
        for pos, kind, action in sorted(event_hits, key=lambda item: item[0]):
            prefix = clause[:pos]
            leader = prefix
            if kind == "kneel":
                marker = _last_direction_marker(prefix)
                if marker is not None:
                    leader = prefix[: marker[0]]

            agent_class, explicit = _resolve_agent_class(
                leader,
                action=action,
                canonical_terms=canonical_terms,
                last_agent=last_agent,
                first_clause=first_clause,
            )
            if seen_event and agent_class == "OTHER" and clause_agent in {"ACTOR", "CAMERA"}:
                agent_class = clause_agent
                explicit = False

            if agent_class == "ACTOR":
                support[kind] = True

            if agent_class in {"ACTOR", "CAMERA"}:
                clause_agent = agent_class
            if explicit and agent_class in {"ACTOR", "CAMERA"}:
                last_agent = agent_class
            elif not explicit and last_agent is None and agent_class in {"ACTOR", "CAMERA"}:
                last_agent = agent_class
            seen_event = True

        first_clause = False
    return support


def _sanitize_actor_target_relations(
    task: str,
    features: DirectorFeatures,
    *,
    canonical_terms: tuple[str, ...],
) -> tuple[DirectorFeatures, bool]:
    support = _scan_actor_subject_support(task, canonical_terms=canonical_terms)

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

    if "facing_to_target" in relation and not support["facing"]:
        relation = [value for value in relation if value != "facing_to_target"]
        removed_facing = True
        filtered = True
    if "gaze_to_target" in relation and not support["gaze"]:
        relation = [value for value in relation if value != "gaze_to_target"]
        failure = [value for value in failure if value != "gaze_target_spatial_binding_fail"]
        removed_gaze = True
        filtered = True
    if "kneeling_to_target" in relation and not support["kneel"]:
        relation = [value for value in relation if value != "kneeling_to_target"]
        spatial = [value for value in spatial if value != "kneeling_to_target"]
        removed_kneel = True
        filtered = True

    if not any(value in _BODY_RELATIONS for value in relation):
        failure = [value for value in failure if value != "body_orientation_target_fail"]
        if (removed_facing or removed_kneel) and not support["facing"]:
            spatial = [value for value in spatial if value != "body_orientation"]

    if removed_gaze and not support["gaze"]:
        spatial = [value for value in spatial if value != "gaze_direction"]

    if not any(value in _TARGET_RELATIONS for value in relation):
        dramatic = [value for value in dramatic if value != "target_oriented_action"]
        spatial = [value for value in spatial if value != "locatable_target"]

    if filtered:
        matched_rules.append("actor_subject_safety_filter")
        semantic_trace.append("EntitySemantics.actor_subject_boundary")

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
        "actor_subject_safety_filtered": filtered,
        "matched_rules": list(features.matched_rules),
        "semantic_trace": list(features.semantic_trace),
        "route_resolution": "director_route_index",
        "hard_routes": list(task["hard_routes"]),
        "authority_boundary": "retrieval_query_only",
    }
    return task
