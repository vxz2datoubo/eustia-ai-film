"""Machine route resolution for director tasks.

The resolver owns no route definitions. It consumes director_route_index.yaml as
the sole route authority and matches either exact surface symptoms or compiled
semantic feature atoms against that authority.
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
        semantic_match = any(
            _semantic_match(feature, symptom)
            for feature in features
            for symptom in symptoms
        )
        if raw_match or semantic_match:
            resolved.append(str(route["id"]))

    return list(dict.fromkeys(resolved))
