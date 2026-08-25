"""Machine route resolution for director tasks.

The resolver owns no route definitions. It consumes director_route_index.yaml as
the sole route authority. Routes may expose machine-readable compiled-feature
triggers there; literal symptom and legacy ASCII-atom matching remain fallbacks.
"""

from __future__ import annotations

import re
from typing import Any


class RouteResolutionError(ValueError):
    """Raised when canonical director route authority is unavailable."""


_STOP_ATOMS = {"to", "from", "the", "a", "an", "of", "and", "or", "relation", "with"}
_FEATURE_KEYS = ("dramatic_function", "relation_type", "spatial_action_features", "failure_mechanism")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _norm(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"[_/\\-]+", " ", text)
    return " ".join(text.split())


def _norm_set(value: Any) -> set[str]:
    return {_norm(item) for item in _as_list(value) if _norm(item)}


def _atoms(value: Any) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", _norm(value)) if x not in _STOP_ATOMS}


def _semantic_match(feature: str, symptom: str) -> bool:
    left = _norm(feature)
    right = _norm(symptom)
    if not left or not right:
        return False
    if left == right:
        return True
    la = _atoms(left)
    ra = _atoms(right)
    return len(la) >= 2 and len(ra) >= 2 and len(la & ra) >= 2


def _trigger_group_matches(task: dict[str, Any], group: Any, *, mode: str) -> bool:
    if not isinstance(group, dict) or not group:
        return mode != "any"
    matches: list[bool] = []
    for key, expected in group.items():
        if key not in _FEATURE_KEYS:
            continue
        observed = _norm_set(task.get(key))
        required = _norm_set(expected)
        if not required:
            continue
        if mode == "all":
            matches.append(required.issubset(observed))
        else:
            matches.append(bool(observed & required))
    if not matches:
        return mode != "any"
    return all(matches) if mode == "all" else any(matches)


def _machine_trigger_match(task: dict[str, Any], trigger_spec: Any) -> bool:
    """Evaluate route-local structured triggers without owning route semantics."""
    if not isinstance(trigger_spec, dict) or not trigger_spec:
        return False

    any_of = trigger_spec.get("any_of")
    all_of = trigger_spec.get("all_of")
    none_of = trigger_spec.get("none_of")

    positive_declared = bool(any_of) or bool(all_of)
    positive_match = (
        (not any_of or _trigger_group_matches(task, any_of, mode="any"))
        and (not all_of or _trigger_group_matches(task, all_of, mode="all"))
    )
    blocked = bool(none_of) and _trigger_group_matches(task, none_of, mode="any")
    return positive_declared and positive_match and not blocked


def resolve_hard_routes(
    task: dict[str, Any],
    route_data: dict[str, Any] | None,
    *,
    description: str | None = None,
) -> list[str]:
    """Resolve route IDs from canonical director_route_index data only."""
    if not isinstance(route_data, dict) or not isinstance(route_data.get("routes"), list):
        raise RouteResolutionError("DIRECTOR_ROUTE_INDEX_REQUIRED")

    resolved = [str(x) for x in _as_list(task.get("hard_routes")) if str(x)]
    normalized_description = _norm(description)
    features: list[str] = []
    for key in _FEATURE_KEYS:
        features.extend(str(x) for x in _as_list(task.get(key)) if str(x))

    for route in route_data.get("routes", []):
        if not isinstance(route, dict) or not route.get("id"):
            continue
        symptoms = [str(x) for x in _as_list(route.get("symptoms")) if str(x)]
        raw_match = False
        if normalized_description:
            raw_match = any(
                len(_norm(symptom)) >= 4 and _norm(symptom) in normalized_description
                for symptom in symptoms
            )
        structured_match = _machine_trigger_match(task, route.get("machine_triggers"))
        legacy_semantic_match = any(
            _semantic_match(feature, symptom)
            for feature in features
            for symptom in symptoms
        )
        if raw_match or structured_match or legacy_semantic_match:
            resolved.append(str(route["id"]))

    return list(dict.fromkeys(resolved))
