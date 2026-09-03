"""Provenance-verified public facade for the Production Intelligence trusted adapter.

The reviewed coordination semantics live in ``_trusted_adapter_core``. This facade
adds the missing trust-root closure before any receipt can be minted or consumed:

Production Intelligence -> canonical Targeted Repair -> canonical Expected-vs-Observed.

The core candidate remains coordination-only. This module does not add route,
learning, repair, director, canonical-write, or activation authority.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

from learning_retriever import expected_observed as _expected_observed_module
from learning_retriever import targeted_repair as _targeted_repair_module

from . import _trusted_adapter_core as _core
from ._trusted_adapter_core import *  # noqa: F401,F403
from .contracts import ProductionIntelligenceError
from .trust_root import require_governed_project_root

_CORE_SOURCE_REL = Path(
    "tools/production_intelligence/production_intelligence/_trusted_adapter_core.py"
)
_TARGETED_REPAIR_SOURCE_REL = Path(
    "tools/learning_retriever/learning_retriever/targeted_repair.py"
)
_EXPECTED_OBSERVED_SOURCE_REL = Path(
    "tools/learning_retriever/learning_retriever/expected_observed.py"
)


def _fail(code: str, **details: Any) -> ProductionIntelligenceError:
    return ProductionIntelligenceError(code, details=details or None)


def _source_path(module: Any, *, label: str) -> Path:
    raw = getattr(module, "__file__", None)
    if not raw:
        raise _fail(
            "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_INVALID",
            component=label,
            reason="source_path_missing",
        )
    try:
        return Path(raw).resolve()
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise _fail(
            "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_INVALID",
            component=label,
            reason="source_path_invalid",
        ) from exc


def _source_digest(path: Path, *, label: str) -> str:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise _fail(
            "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_INVALID",
            component=label,
            reason="source_unreadable",
        ) from exc


# Import-time pins are observations of the executing governed candidate. Runtime
# mint/consume paths revalidate them immediately before and after trust-bearing work.
_PINNED_CORE_MODULE = _core
_PINNED_CORE_COMPILE = _core.compile_expected_observed_coordination
_PINNED_CORE_RESOLVE = _core.resolve_receipt_consumers
_PINNED_CORE_PLAN_BINDING = _core.plan_targeted_repair
_PINNED_TARGETED_REPAIR_MODULE = _targeted_repair_module
_PINNED_TARGETED_REPAIR_CALLABLE = _targeted_repair_module.plan_targeted_repair
_PINNED_PUBLIC_PLAN_BINDING = plan_targeted_repair
_PINNED_TARGETED_EVAL_BINDING = _targeted_repair_module.evaluate_expected_vs_observed
_PINNED_EXPECTED_OBSERVED_MODULE = _expected_observed_module
_PINNED_EXPECTED_OBSERVED_CALLABLE = _expected_observed_module.evaluate_expected_vs_observed

_PINNED_CORE_SOURCE_PATH = _source_path(_PINNED_CORE_MODULE, label="trusted_adapter_core")
_PINNED_TARGETED_REPAIR_SOURCE_PATH = _source_path(
    _PINNED_TARGETED_REPAIR_MODULE, label="targeted_repair"
)
_PINNED_EXPECTED_OBSERVED_SOURCE_PATH = _source_path(
    _PINNED_EXPECTED_OBSERVED_MODULE, label="expected_observed"
)
_PINNED_CORE_SOURCE_DIGEST = _source_digest(
    _PINNED_CORE_SOURCE_PATH, label="trusted_adapter_core"
)
_PINNED_TARGETED_REPAIR_SOURCE_DIGEST = _source_digest(
    _PINNED_TARGETED_REPAIR_SOURCE_PATH, label="targeted_repair"
)
_PINNED_EXPECTED_OBSERVED_SOURCE_DIGEST = _source_digest(
    _PINNED_EXPECTED_OBSERVED_SOURCE_PATH, label="expected_observed"
)

if _PINNED_CORE_PLAN_BINDING is not _PINNED_TARGETED_REPAIR_CALLABLE:
    raise _fail(
        "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_INVALID",
        component="targeted_repair",
        reason="core_planner_binding_not_canonical_at_import",
    )
if _PINNED_PUBLIC_PLAN_BINDING is not _PINNED_TARGETED_REPAIR_CALLABLE:
    raise _fail(
        "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_INVALID",
        component="targeted_repair",
        reason="public_planner_binding_not_canonical_at_import",
    )
if _PINNED_TARGETED_EVAL_BINDING is not _PINNED_EXPECTED_OBSERVED_CALLABLE:
    raise _fail(
        "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_INVALID",
        component="expected_observed",
        reason="planner_evaluator_binding_not_canonical_at_import",
    )


def _require_runtime_provenance(project_root: str | Path) -> None:
    root = Path(project_root).resolve()
    expected_paths = {
        "trusted_adapter_core": (root / _CORE_SOURCE_REL).resolve(),
        "targeted_repair": (root / _TARGETED_REPAIR_SOURCE_REL).resolve(),
        "expected_observed": (root / _EXPECTED_OBSERVED_SOURCE_REL).resolve(),
    }

    identity_checks = (
        (_core is _PINNED_CORE_MODULE, "trusted_adapter_core", "module_binding_substituted"),
        (
            _core.compile_expected_observed_coordination is _PINNED_CORE_COMPILE,
            "trusted_adapter_core",
            "compile_binding_substituted",
        ),
        (
            _core.resolve_receipt_consumers is _PINNED_CORE_RESOLVE,
            "trusted_adapter_core",
            "consumer_binding_substituted",
        ),
        (
            plan_targeted_repair is _PINNED_TARGETED_REPAIR_CALLABLE,
            "targeted_repair",
            "public_planner_binding_substituted",
        ),
        (
            _core.plan_targeted_repair is _PINNED_TARGETED_REPAIR_CALLABLE,
            "targeted_repair",
            "core_planner_binding_substituted",
        ),
        (
            _targeted_repair_module is _PINNED_TARGETED_REPAIR_MODULE,
            "targeted_repair",
            "module_binding_substituted",
        ),
        (
            _targeted_repair_module.plan_targeted_repair is _PINNED_TARGETED_REPAIR_CALLABLE,
            "targeted_repair",
            "planner_binding_substituted",
        ),
        (
            _targeted_repair_module.evaluate_expected_vs_observed
            is _PINNED_EXPECTED_OBSERVED_CALLABLE,
            "expected_observed",
            "planner_evaluator_binding_substituted",
        ),
        (
            _expected_observed_module is _PINNED_EXPECTED_OBSERVED_MODULE,
            "expected_observed",
            "module_binding_substituted",
        ),
        (
            _expected_observed_module.evaluate_expected_vs_observed
            is _PINNED_EXPECTED_OBSERVED_CALLABLE,
            "expected_observed",
            "evaluator_binding_substituted",
        ),
    )
    for valid, component, reason in identity_checks:
        if not valid:
            raise _fail(
                "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_SUBSTITUTED",
                component=component,
                reason=reason,
            )

    source_specs = (
        (
            "trusted_adapter_core",
            _PINNED_CORE_MODULE,
            _PINNED_CORE_SOURCE_PATH,
            _PINNED_CORE_SOURCE_DIGEST,
        ),
        (
            "targeted_repair",
            _PINNED_TARGETED_REPAIR_MODULE,
            _PINNED_TARGETED_REPAIR_SOURCE_PATH,
            _PINNED_TARGETED_REPAIR_SOURCE_DIGEST,
        ),
        (
            "expected_observed",
            _PINNED_EXPECTED_OBSERVED_MODULE,
            _PINNED_EXPECTED_OBSERVED_SOURCE_PATH,
            _PINNED_EXPECTED_OBSERVED_SOURCE_DIGEST,
        ),
    )
    for component, module, pinned_path, pinned_digest in source_specs:
        current_path = _source_path(module, label=component)
        if current_path != pinned_path or current_path != expected_paths[component]:
            raise _fail(
                "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_SUBSTITUTED",
                component=component,
                reason="source_path_substituted",
                expected=str(expected_paths[component]),
                observed=str(current_path),
            )
        if _source_digest(current_path, label=component) != pinned_digest:
            raise _fail(
                "TRUSTED_ADAPTER_RUNTIME_PROVENANCE_SUBSTITUTED",
                component=component,
                reason="source_digest_changed",
            )


def compile_expected_observed_coordination(
    raw_eval_input: Mapping[str, Any],
    *,
    project_root: str | Path,
) -> TrustedEvalCoordinationReceipt:
    """Mint only after the complete upstream runtime trust chain is fresh-verified."""
    root = require_governed_project_root(project_root)
    _require_runtime_provenance(root)
    receipt = _PINNED_CORE_COMPILE(raw_eval_input, project_root=root)
    # A mutation detected after the upstream call invalidates the result before it can
    # escape this public facade.
    _require_runtime_provenance(root)
    return receipt


def resolve_receipt_consumers(
    receipt: TrustedEvalCoordinationReceipt,
    *,
    project_root: str | Path,
    capability_ids: Iterable[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Consume only while the same mint authority chain remains intact."""
    root = require_governed_project_root(project_root)
    _require_runtime_provenance(root)

    # Preserve the existing synthetic policy-drift tests at the public facade while the
    # unchanged core independently performs the real fresh-file validation.
    adapter_policy = load_trusted_adapter_policy(root)
    repair_policy = load_yaml(root / TARGETED_REPAIR_POLICY_PATH)
    if receipt.adapter_policy_digest != _core._policy_digest(adapter_policy):
        raise _fail("TRUSTED_ADAPTER_POLICY_STALE")
    if receipt.targeted_repair_policy_digest != _core._policy_digest(repair_policy):
        raise _fail("TRUSTED_ADAPTER_REPAIR_POLICY_STALE")

    result = _PINNED_CORE_RESOLVE(
        receipt,
        project_root=root,
        capability_ids=capability_ids,
    )
    _require_runtime_provenance(root)
    return result
