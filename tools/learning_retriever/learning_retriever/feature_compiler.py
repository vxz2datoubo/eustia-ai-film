"""Canonical public facade for Director Feature Compiler v5 grammar hardening.

The previously reviewed v4 facade is frozen in ``_feature_compiler_facade_v4``.
This thin public wrapper closes production-language grammar drift without
re-opening caller actor authority, cross-actor carry, or project truth surfaces.

Public flow:
    original director text
      -> canonical character projection
      -> bounded actor/target normalization for frozen core only
      -> frozen core parser
      -> v5 actor/observable + shared target safety facade on original text
      -> canonical director_route_index

The wrapper remains retrieval-query-only. It creates no story, character, map,
asset, camera, learning, maturity, writeback, or generation authority.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from . import _feature_compiler_facade_v4 as _legacy
from .entity_semantics import (
    HUMAN_ROLE_HEADS,
    PRONOUN_AGENT_TERMS,
    bounded_animate_agent_leader,
)
from .predicate_semantics import (
    TARGET_PREFIX_TOKENS,
    normalize_post_action_target_prefixes,
    target_starts_after_bounded_prefix,
)
from .route_resolver import RouteResolutionError, resolve_hard_routes


FEATURE_KEYS = _legacy.FEATURE_KEYS
SOAC_SCHEMA_PATH = _legacy.SOAC_SCHEMA_PATH
DirectorFeatures = _legacy.DirectorFeatures
FeatureCompilationError = _legacy.FeatureCompilationError
validate_semantic_dependencies = _legacy.validate_semantic_dependencies

_MODULE_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CANONICAL_ACTOR_AUTHORITY = _legacy._canonical_actor_authority
_CAMERA_TERMS = _legacy._CAMERA_TERMS
_BODY_TERMS = _legacy._BODY_TERMS
_TEMPORAL_GLUE = _legacy._TEMPORAL_GLUE
_COORDINATION_GLUE = _legacy._COORDINATION_GLUE
_MANNER_TOKENS = _legacy._MANNER_TOKENS
_SIMPLE_MODIFIERS = _legacy._SIMPLE_MODIFIERS
_FACING_ACTIONS = _legacy._FACING_ACTIONS
_GAZE_ACTIONS = _legacy._GAZE_ACTIONS
_KNEEL_ACTIONS = _legacy._KNEEL_ACTIONS
_TARGET_OBJECT_TERMS = _legacy._TARGET_OBJECT_TERMS
_TARGET_PREFIX_MODIFIERS = TARGET_PREFIX_TOKENS
_GAZE_OBSERVABLE_TERMS = ("目光", "视线")
_ALL_ACTOR_PREDICATE_ACTIONS = tuple(
    dict.fromkeys(_FACING_ACTIONS + _GAZE_ACTIONS + _KNEEL_ACTIONS)
)
_CORE_COORDINATION_TERMS = ("并且", "并", "且")

# Freeze references before installing v5 callbacks into the private facade.
_V4_BASE_ACTOR_IDENTITY = _legacy._base_actor_identity_key
_V4_CAMERA_LEADER = _legacy._camera_leader
_V4_BODY_LEADER = _legacy._body_leader
_V4_MODIFIER_TAIL = _legacy._modifier_tail
_V4_STRIP_LEADING_GLUE = _legacy._strip_leading_glue
_V4_TARGET_TERMS = _legacy._target_terms
_V4_MERGE = _legacy._merge


def _canonical_actor_authority() -> tuple[dict[str, str], tuple[str, ...]]:
    return _CANONICAL_ACTOR_AUTHORITY()


def _canonical_prefix_identity(
    value: str,
    *,
    canonical_identity_map: dict[str, str],
) -> str | None:
    """Resolve exact canonical term + validated modifier before free-form CJK gate."""
    normalized = _V4_STRIP_LEADING_GLUE(value)
    for term, row_id in sorted(
        canonical_identity_map.items(), key=lambda item: (-len(item[0]), item[0])
    ):
        if not normalized.startswith(term):
            continue
        tail = normalized[len(term):]
        if _V4_MODIFIER_TAIL(tail):
            return f"CHARACTER::{row_id}"
    return None


def _base_actor_identity_key_v5(
    value: str,
    *,
    canonical_terms: tuple[str, ...],
    canonical_identity_map: dict[str, str],
    action: str,
) -> str | None:
    canonical = _canonical_prefix_identity(
        value,
        canonical_identity_map=canonical_identity_map,
    )
    if canonical is not None:
        return canonical
    return _V4_BASE_ACTOR_IDENTITY(
        value,
        canonical_terms=canonical_terms,
        canonical_identity_map=canonical_identity_map,
        action=action,
    )


def _possessive_observable_owner_identity(
    value: str,
    *,
    canonical_terms: tuple[str, ...],
    canonical_identity_map: dict[str, str],
    action: str,
) -> str | None:
    """Bind ``<actor>的身体/目光/视线`` only through a proven actor owner."""
    normalized = _V4_STRIP_LEADING_GLUE(value)
    owned_terms = tuple(sorted(set(_BODY_TERMS + _GAZE_OBSERVABLE_TERMS), key=len, reverse=True))
    for observable in owned_terms:
        marker = f"的{observable}"
        pos = normalized.rfind(marker)
        if pos <= 0:
            continue
        tail = normalized[pos + len(marker):]
        if not _V4_MODIFIER_TAIL(tail):
            continue
        owner = normalized[:pos]
        identity = _base_actor_identity_key_v5(
            owner,
            canonical_terms=canonical_terms,
            canonical_identity_map=canonical_identity_map,
            action=action,
        )
        if identity is not None:
            return identity
    return None


def _classify_explicit_leader_v5(
    value: str,
    *,
    canonical_terms: tuple[str, ...],
    canonical_identity_map: dict[str, str],
    action: str,
) -> str:
    normalized = _V4_STRIP_LEADING_GLUE(value)
    if not normalized:
        return "EMPTY"
    if _V4_CAMERA_LEADER(normalized):
        return "CAMERA"
    if _possessive_observable_owner_identity(
        normalized,
        canonical_terms=canonical_terms,
        canonical_identity_map=canonical_identity_map,
        action=action,
    ) is not None:
        return "ACTOR"
    if _V4_BODY_LEADER(normalized):
        return "ACTOR"
    if _canonical_prefix_identity(
        normalized,
        canonical_identity_map=canonical_identity_map,
    ) is not None:
        return "ACTOR"
    if bounded_animate_agent_leader(
        normalized,
        action=action,
        known_actor_terms=canonical_terms,
        modifier_tail_validator=_V4_MODIFIER_TAIL,
        max_chars=36,
    ):
        return "ACTOR"
    return "OTHER"


def _actor_identity_key_v5(
    value: str,
    *,
    canonical_terms: tuple[str, ...],
    canonical_identity_map: dict[str, str],
    action: str,
) -> str | None:
    owner = _possessive_observable_owner_identity(
        value,
        canonical_terms=canonical_terms,
        canonical_identity_map=canonical_identity_map,
        action=action,
    )
    if owner is not None:
        return owner
    return _base_actor_identity_key_v5(
        value,
        canonical_terms=canonical_terms,
        canonical_identity_map=canonical_identity_map,
        action=action,
    )


def _direct_target_in_event_tail_v5(
    value: str, *, canonical_terms: tuple[str, ...]
) -> bool:
    """Use the same bounded target grammar consumed by legacy-core normalization."""
    return target_starts_after_bounded_prefix(
        value,
        _V4_TARGET_TERMS(canonical_terms),
    )


def _normalize_canonical_actor_modifiers_for_core(
    text: str,
    *,
    canonical_identity_map: dict[str, str],
) -> tuple[str, bool]:
    """Strip only validated modifiers between a canonical actor and predicate."""
    if not text:
        return text, False
    actions = tuple(sorted(set(_ALL_ACTOR_PREDICATE_ACTIONS), key=len, reverse=True))
    changed_any = False
    result = text
    for term in sorted(canonical_identity_map, key=len, reverse=True):
        search_from = 0
        while True:
            hit = result.find(term, search_from)
            if hit < 0:
                break
            actor_end = hit + len(term)
            candidate_actions: list[tuple[int, str]] = []
            for action in actions:
                action_pos = result.find(action, actor_end)
                if action_pos >= 0 and action_pos - actor_end <= 16:
                    candidate_actions.append((action_pos, action))
            if not candidate_actions:
                search_from = actor_end
                continue
            action_pos, action = min(candidate_actions, key=lambda item: item[0])
            between = result[actor_end:action_pos]
            if between and _V4_MODIFIER_TAIL(between):
                result = result[:actor_end] + result[action_pos:]
                changed_any = True
                search_from = actor_end + len(action)
            else:
                search_from = actor_end
    return result, changed_any


def _normalize_explicit_subject_coordination_for_core(
    text: str,
    *,
    canonical_terms: tuple[str, ...],
) -> tuple[str, bool]:
    """Split bounded coordinated next subjects for the punctuation-based frozen core.

    Only an explicit actor token immediately followed by a known predicate can
    trigger the split. Original text remains untouched for the final safety
    facade, so this adapter cannot mint actor authority.
    """
    actor_terms = tuple(
        sorted(
            set(canonical_terms)
            | set(HUMAN_ROLE_HEADS)
            | set(PRONOUN_AGENT_TERMS)
            | {"群众", "人群", "百姓", "信徒", "民众", "居民", "人物", "角色"},
            key=len,
            reverse=True,
        )
    )
    actions = tuple(sorted(set(_ALL_ACTOR_PREDICATE_ACTIONS), key=len, reverse=True))
    if not text or not actor_terms or not actions:
        return text, False
    glue_alt = "|".join(re.escape(x) for x in sorted(_CORE_COORDINATION_TERMS, key=len, reverse=True))
    actor_alt = "|".join(re.escape(x) for x in actor_terms)
    action_alt = "|".join(re.escape(x) for x in actions)
    pattern = re.compile(
        rf"(?P<glue>{glue_alt})(?P<actor>{actor_alt})(?P<action>{action_alt})"
    )
    normalized, count = pattern.subn(
        lambda m: f"，{m.group('actor')}{m.group('action')}",
        text,
    )
    return normalized, bool(count)


def _core_input_projection(
    text: str,
    *,
    canonical_identity_map: dict[str, str],
    canonical_terms: tuple[str, ...],
) -> tuple[str, dict[str, bool]]:
    actor_normalized, actor_changed = _normalize_canonical_actor_modifiers_for_core(
        text,
        canonical_identity_map=canonical_identity_map,
    )
    subject_normalized, subject_changed = _normalize_explicit_subject_coordination_for_core(
        actor_normalized,
        canonical_terms=canonical_terms,
    )
    target_normalized, target_changed = normalize_post_action_target_prefixes(
        subject_normalized,
        action_terms=_FACING_ACTIONS,
        target_terms=_V4_TARGET_TERMS(canonical_terms),
    )
    return target_normalized, {
        "canonical_actor_modifier_normalized": actor_changed,
        "explicit_subject_coordination_segmented": subject_changed,
        "shared_target_prefix_normalized": target_changed,
    }


# The private v4 scanner resolves these callbacks from its own globals at call
# time. Install v5 callbacks there so old event/carry logic remains intact.
_legacy._TARGET_PREFIX_MODIFIERS = TARGET_PREFIX_TOKENS
_legacy._base_actor_identity_key = _base_actor_identity_key_v5
_legacy._classify_explicit_leader = _classify_explicit_leader_v5
_legacy._actor_identity_key = _actor_identity_key_v5
_legacy._direct_target_in_event_tail = _direct_target_in_event_tail_v5

_sanitize_actor_target_relations = _legacy._sanitize_actor_target_relations
_scan_actor_event_support = _legacy._scan_actor_event_support
_target_terms = _legacy._target_terms
_modifier_tail = _legacy._modifier_tail
_strip_leading_glue = _legacy._strip_leading_glue


def compile_director_features(task: str, *, strict: bool = True) -> DirectorFeatures:
    if not isinstance(task, str) or not task.strip():
        raise FeatureCompilationError("EMPTY_DIRECTOR_TASK")
    canonical_identity_map, canonical_terms = _canonical_actor_authority()
    core_text, _ = _core_input_projection(
        task,
        canonical_identity_map=canonical_identity_map,
        canonical_terms=canonical_terms,
    )
    parsed = _legacy._core.compile_director_features(
        core_text,
        strict=False,
        known_actor_terms=canonical_terms,
    )
    result, _ = _sanitize_actor_target_relations(
        task,
        parsed,
        canonical_terms=canonical_terms,
        canonical_identity_map=canonical_identity_map,
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
    if not isinstance(description, str) or not description.strip():
        raise FeatureCompilationError("EMPTY_DIRECTOR_TASK")
    canonical_identity_map, canonical_terms = _canonical_actor_authority()
    core_text, normalization = _core_input_projection(
        description,
        canonical_identity_map=canonical_identity_map,
        canonical_terms=canonical_terms,
    )
    parsed = _legacy._core.compile_director_features(
        core_text,
        strict=False,
        known_actor_terms=canonical_terms,
    )
    features, filtered = _sanitize_actor_target_relations(
        description,
        parsed,
        canonical_terms=canonical_terms,
        canonical_identity_map=canonical_identity_map,
    )
    if strict and not features.recognized:
        raise FeatureCompilationError("NO_RECOGNIZED_DIRECTOR_FEATURES")

    task = dict(base_task or {})
    task["task_id"] = str(task.get("task_id") or task_id)
    for key, compiled in features.as_dict().items():
        task[key] = _V4_MERGE(task.get(key), compiled)
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
        "facade_revision": "predicate_grammar_v5",
        "status": "PASS" if features.recognized else "FAIL",
        "input_fingerprint": hashlib.sha256(description.encode("utf-8")).hexdigest()[:16],
        "compiled_feature_keys": [key for key in FEATURE_KEYS if getattr(features, key)],
        "known_actor_terms_count": len(canonical_terms),
        "canonical_character_row_count": len(set(canonical_identity_map.values())),
        "actor_terms_source": "PROJECT_INDEX.canonical.character_db",
        "actor_identity_authority": "canonical_character_row_v1",
        "caller_actor_terms_supported": False,
        "actor_subject_binding": "per_target_event_actor_identity_v3",
        "event_target_segmentation": "predicate_local_subject_boundary_v1",
        "shared_target_grammar": "predicate_semantics_v1",
        "canonical_actor_modifier_normalized_for_core": normalization[
            "canonical_actor_modifier_normalized"
        ],
        "explicit_subject_coordination_segmented_for_core": normalization[
            "explicit_subject_coordination_segmented"
        ],
        "shared_target_prefix_normalized_for_core": normalization[
            "shared_target_prefix_normalized"
        ],
        "actor_subject_safety_filtered": filtered,
        "matched_rules": list(features.matched_rules),
        "semantic_trace": list(features.semantic_trace),
        "route_resolution": "director_route_index",
        "hard_routes": list(task["hard_routes"]),
        "authority_boundary": "retrieval_query_only",
    }
    return task


def __getattr__(name: str) -> Any:
    return getattr(_legacy, name)
