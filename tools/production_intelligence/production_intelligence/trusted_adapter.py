"""Trusted upstream adapter for candidate Production Intelligence coordination.

Serialized Signal Envelopes remain structural transport metadata, not route-authority
tokens. This module implements the first bounded trusted adapter by re-executing the
canonical Expected-vs-Observed path through the canonical Targeted Repair planner and
minting one opaque, integrity-bound in-process receipt. The Atlas may only coordinate
capability consumers already allowed by the canonical repair surface.

A trusted receipt binds both the adapter policy and the exact canonical Targeted Repair
policy content used to produce it. Final consumer resolution fresh-reads those policies
again, so a stable policy id with changed routing semantics cannot reuse a stale receipt.
Trust-bearing mint/consume paths are additionally bound to the governed source checkout;
a caller-selected alternate project tree can never define a second trust universe.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import hmac
import json
from pathlib import Path
import secrets
from typing import Any, Iterable, Mapping

from learning_retriever.targeted_repair import plan_targeted_repair

from .contracts import ProductionIntelligenceError, as_list, load_yaml, require_mapping
from .trust_root import require_governed_project_root

TRUSTED_ADAPTER_POLICY_PATH = Path(
    "10_运行时/production_intelligence_trusted_adapter_policy.yaml"
)
TARGETED_REPAIR_POLICY_PATH = Path("10_运行时/targeted_repair_policy.yaml")
GRAPH_PATH = Path("10_运行时/production_intelligence_capability_graph.yaml")
PICG_WORKFLOW_PATH = Path(".github/workflows/production-intelligence-capability-atlas.yml")
LEARNING_WORKFLOW_PATH = Path(".github/workflows/learning-feature-compiler.yml")

_ADAPTER_ID = "EXPECTED_OBSERVED_TARGETED_REPAIR_V1"
_TRUST_TOKEN = object()
_INTEGRITY_KEY = secrets.token_bytes(32)
_FORBIDDEN_CONSUMERS = {
    "CAP-LEARNING",
    "CAP-PROACTIVE-COLLABORATION",
    "CAP-INFRASTRUCTURE-TRANSPORT",
}


@dataclass(frozen=True)
class TrustedRepairItem:
    field: str
    outcome: str
    failure_category: str | None
    repair_surface: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class TrustedEvalCoordinationReceipt:
    receipt_id: str
    adapter_id: str
    source_eval_id: str
    source_eval_status: str
    source_binding_mode: str
    routing_policy_id: str
    work_item_projection: str | None
    source_input_digest: str
    adapter_policy_digest: str
    targeted_repair_policy_digest: str
    repair_items: tuple[TrustedRepairItem, ...]
    authority_refs: tuple[str, ...]
    serialized_route_authority: bool = False
    canonical_mutation_authorized: bool = False
    learning_writeback_authorized: bool = False
    _integrity: str = field(default="", repr=False, compare=False)
    _trust_token: object = field(default=None, repr=False, compare=False)


def _fail(code: str, **details: Any) -> ProductionIntelligenceError:
    return ProductionIntelligenceError(code, details=details or None)


def _stable_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
    except (TypeError, ValueError) as exc:
        raise _fail("TRUSTED_ADAPTER_SOURCE_NOT_SERIALIZABLE") from exc


def _stable_digest(value: Any) -> str:
    return sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _policy_digest(policy: Mapping[str, Any]) -> str:
    return _stable_digest(dict(policy))


def _repair_item_payload(item: TrustedRepairItem) -> dict[str, Any]:
    return {
        "field": item.field,
        "outcome": item.outcome,
        "failure_category": item.failure_category,
        "repair_surface": item.repair_surface,
        "evidence_refs": list(item.evidence_refs),
    }


def _receipt_integrity_payload(receipt: TrustedEvalCoordinationReceipt) -> dict[str, Any]:
    return {
        "receipt_id": receipt.receipt_id,
        "adapter_id": receipt.adapter_id,
        "source_eval_id": receipt.source_eval_id,
        "source_eval_status": receipt.source_eval_status,
        "source_binding_mode": receipt.source_binding_mode,
        "routing_policy_id": receipt.routing_policy_id,
        "work_item_projection": receipt.work_item_projection,
        "source_input_digest": receipt.source_input_digest,
        "adapter_policy_digest": receipt.adapter_policy_digest,
        "targeted_repair_policy_digest": receipt.targeted_repair_policy_digest,
        "repair_items": [_repair_item_payload(item) for item in receipt.repair_items],
        "authority_refs": list(receipt.authority_refs),
        "serialized_route_authority": receipt.serialized_route_authority,
        "canonical_mutation_authorized": receipt.canonical_mutation_authorized,
        "learning_writeback_authorized": receipt.learning_writeback_authorized,
    }


def _integrity_for(receipt: TrustedEvalCoordinationReceipt) -> str:
    return hmac.new(
        _INTEGRITY_KEY,
        _stable_json(_receipt_integrity_payload(receipt)).encode("utf-8"),
        "sha256",
    ).hexdigest()


def load_trusted_adapter_policy(project_root: str | Path) -> dict[str, Any]:
    return load_yaml(Path(project_root) / TRUSTED_ADAPTER_POLICY_PATH)


def is_trusted_eval_receipt(value: Any) -> bool:
    if not isinstance(value, TrustedEvalCoordinationReceipt):
        return False
    if value._trust_token is not _TRUST_TOKEN:
        return False
    if value.adapter_id != _ADAPTER_ID:
        return False
    if value.serialized_route_authority is not False:
        return False
    if value.canonical_mutation_authorized is not False:
        return False
    if value.learning_writeback_authorized is not False:
        return False
    expected = _integrity_for(value)
    return bool(value._integrity) and hmac.compare_digest(value._integrity, expected)


def require_trusted_eval_receipt(value: Any) -> TrustedEvalCoordinationReceipt:
    if not is_trusted_eval_receipt(value):
        raise _fail(
            "TRUSTED_SIGNAL_RECEIPT_REQUIRED",
            accepted_adapter=_ADAPTER_ID,
            serialized_signal_envelope_route_authority=False,
        )
    return value


def _capability_ids(graph: Mapping[str, Any]) -> set[str]:
    nodes = graph.get("capability_nodes")
    if not isinstance(nodes, list):
        raise _fail("TRUSTED_ADAPTER_GRAPH_CAPABILITIES_INVALID")
    result = {
        str(node.get("capability_id") or "").strip()
        for node in nodes
        if isinstance(node, Mapping) and str(node.get("capability_id") or "").strip()
    }
    if not result:
        raise _fail("TRUSTED_ADAPTER_GRAPH_CAPABILITIES_INVALID")
    return result


def validate_trusted_adapter_policy(
    project_root: str | Path,
    *,
    graph: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Cross-check the coordination map against current canonical repair routing.

    This function intentionally remains fixture-root capable because it is a policy
    validator, not a trust-minting route. Receipt mint/consume functions below enforce
    the governed root separately.
    """
    root = Path(project_root)
    policy = load_trusted_adapter_policy(root)
    repair_policy = load_yaml(root / TARGETED_REPAIR_POLICY_PATH)
    graph = dict(graph or load_yaml(root / GRAPH_PATH))

    if policy.get("policy_id") != "EUSTIA_PRODUCTION_INTELLIGENCE_TRUSTED_ADAPTER_V1":
        raise _fail("TRUSTED_ADAPTER_POLICY_ID_MISMATCH")
    if not str(policy.get("status") or "").startswith("candidate"):
        raise _fail("TRUSTED_ADAPTER_POLICY_MUST_REMAIN_CANDIDATE")

    boundary = require_mapping(
        policy.get("authority_boundary"), "TRUSTED_ADAPTER_AUTHORITY_BOUNDARY_INVALID"
    )
    required_false = (
        "serialized_signal_envelope_accepted_as_route_authority",
        "caller_producer_label_grants_authority",
        "caller_authority_refs_grant_authority",
        "caller_problem_signatures_grant_capability_selection",
        "raw_serialized_eval_result_accepted_as_authority",
        "learning_writeback_authority",
        "canonical_writeback_authority",
    )
    if any(boundary.get(key) is not False for key in required_false):
        raise _fail("TRUSTED_ADAPTER_SERIALIZED_AUTHORITY_LEAK")
    if boundary.get("canonical_expected_observed_reexecution_required") is not True:
        raise _fail("TRUSTED_ADAPTER_EVAL_REEXECUTION_NOT_REQUIRED")
    if boundary.get("canonical_targeted_repair_reexecution_required") is not True:
        raise _fail("TRUSTED_ADAPTER_REPAIR_REEXECUTION_NOT_REQUIRED")

    adapters = require_mapping(policy.get("trusted_adapters"), "TRUSTED_ADAPTERS_INVALID")
    if set(adapters) != {_ADAPTER_ID}:
        raise _fail("TRUSTED_ADAPTER_SET_INVALID", adapters=sorted(adapters))
    adapter = require_mapping(adapters[_ADAPTER_ID], "TRUSTED_ADAPTER_SPEC_INVALID")
    if adapter.get("source_runtime") != "learning_retriever.targeted_repair.plan_targeted_repair":
        raise _fail("TRUSTED_ADAPTER_SOURCE_RUNTIME_MISMATCH")
    if adapter.get("receipt_transport") != "in_process_opaque_object_only":
        raise _fail("TRUSTED_ADAPTER_RECEIPT_TRANSPORT_INVALID")
    if adapter.get("serialized_receipt_rehydration") != "forbidden":
        raise _fail("TRUSTED_ADAPTER_SERIALIZED_REHYDRATION_ALLOWED")
    if adapter.get("targeted_repair_policy_id_required") != repair_policy.get("policy_id"):
        raise _fail("TRUSTED_ADAPTER_REPAIR_POLICY_ID_MISMATCH")

    canonical_surfaces = set(str(x) for x in (repair_policy.get("repair_surfaces") or {}))
    allowlists = require_mapping(
        policy.get("repair_surface_capability_allowlist"),
        "TRUSTED_ADAPTER_SURFACE_ALLOWLIST_INVALID",
    )
    if set(allowlists) != canonical_surfaces:
        raise _fail(
            "TRUSTED_ADAPTER_SURFACE_COVERAGE_MISMATCH",
            missing=sorted(canonical_surfaces - set(allowlists)),
            extra=sorted(set(allowlists) - canonical_surfaces),
        )

    canonical_routes = {
        str(category): str(surface)
        for category, surface in (repair_policy.get("failure_category_routes") or {}).items()
    }
    category_map = require_mapping(
        policy.get("failure_category_consumer_map"),
        "TRUSTED_ADAPTER_CATEGORY_MAP_INVALID",
    )
    if set(category_map) != set(canonical_routes):
        raise _fail(
            "TRUSTED_ADAPTER_CATEGORY_COVERAGE_MISMATCH",
            missing=sorted(set(canonical_routes) - set(category_map)),
            extra=sorted(set(category_map) - set(canonical_routes)),
        )

    capabilities = _capability_ids(graph)
    for surface, raw_allowed in allowlists.items():
        allowed = {str(x) for x in as_list(raw_allowed)}
        if not allowed:
            raise _fail("TRUSTED_ADAPTER_SURFACE_WITHOUT_CONSUMER", repair_surface=surface)
        unknown = allowed - capabilities
        if unknown:
            raise _fail(
                "TRUSTED_ADAPTER_UNKNOWN_CAPABILITY",
                repair_surface=surface,
                capabilities=sorted(unknown),
            )
        forbidden = allowed.intersection(_FORBIDDEN_CONSUMERS)
        if forbidden:
            raise _fail(
                "TRUSTED_ADAPTER_FORBIDDEN_CONSUMER",
                repair_surface=surface,
                capabilities=sorted(forbidden),
            )

    for category, surface in canonical_routes.items():
        consumers = {str(x) for x in as_list(category_map.get(category))}
        allowed = {str(x) for x in as_list(allowlists[surface])}
        if not consumers:
            raise _fail("TRUSTED_ADAPTER_CATEGORY_WITHOUT_CONSUMER", category=category)
        if not consumers.issubset(allowed):
            raise _fail(
                "TRUSTED_ADAPTER_CONSUMER_ESCAPES_REPAIR_SURFACE",
                category=category,
                repair_surface=surface,
                illegal=sorted(consumers - allowed),
            )

    unknown = require_mapping(
        policy.get("unknown_outcome_consumer"),
        "TRUSTED_ADAPTER_UNKNOWN_POLICY_INVALID",
    )
    canonical_unknown_surface = str(repair_policy.get("unknown_outcome_route") or "")
    if unknown.get("repair_surface_required") != canonical_unknown_surface:
        raise _fail("TRUSTED_ADAPTER_UNKNOWN_SURFACE_MISMATCH")
    unknown_consumers = {str(x) for x in as_list(unknown.get("capability_consumers"))}
    if not unknown_consumers:
        raise _fail("TRUSTED_ADAPTER_UNKNOWN_WITHOUT_CONSUMER")
    if not unknown_consumers.issubset(
        {str(x) for x in as_list(allowlists[canonical_unknown_surface])}
    ):
        raise _fail("TRUSTED_ADAPTER_UNKNOWN_CONSUMER_ESCAPES_SURFACE")
    if unknown.get("same_evaluated_signal_may_not_reenter_reverse_observation") is not True:
        raise _fail("TRUSTED_ADAPTER_UNKNOWN_REENTRY_GUARD_MISSING")
    if unknown.get("new_evidence_or_new_generation_required_before_expected_observed_reentry") is not True:
        raise _fail("TRUSTED_ADAPTER_UNKNOWN_NEW_EVIDENCE_GUARD_MISSING")

    dedicated = (root / PICG_WORKFLOW_PATH).read_text(encoding="utf-8")
    learning = (root / LEARNING_WORKFLOW_PATH).read_text(encoding="utf-8")
    required_dedicated = (
        str(TRUSTED_ADAPTER_POLICY_PATH),
        "tools/learning_retriever/learning_retriever/expected_observed.py",
        "tools/learning_retriever/learning_retriever/targeted_repair.py",
        str(TARGETED_REPAIR_POLICY_PATH),
        "PYTHONPATH=tools/production_intelligence:tools/learning_retriever",
    )
    missing_dedicated = [item for item in required_dedicated if item not in dedicated]
    if missing_dedicated:
        raise _fail(
            "TRUSTED_ADAPTER_WORKFLOW_COVERAGE_INCOMPLETE",
            workflow=str(PICG_WORKFLOW_PATH),
            missing=missing_dedicated,
        )
    required_learning = (
        str(TRUSTED_ADAPTER_POLICY_PATH),
        "tools/production_intelligence/**",
        "PYTHONPATH=tools/production_intelligence:tools/learning_retriever",
    )
    missing_learning = [item for item in required_learning if item not in learning]
    if missing_learning:
        raise _fail(
            "TRUSTED_ADAPTER_WORKFLOW_COVERAGE_INCOMPLETE",
            workflow=str(LEARNING_WORKFLOW_PATH),
            missing=missing_learning,
        )

    return {
        "status": "PASS",
        "adapter_id": _ADAPTER_ID,
        "repair_surface_count": len(canonical_surfaces),
        "failure_category_count": len(canonical_routes),
        "capability_consumer_count": len(
            set().union(*(set(as_list(v)) for v in allowlists.values()))
        ),
        "serialized_route_authority": False,
        "targeted_repair_policy_digest": _policy_digest(repair_policy),
    }


def compile_expected_observed_coordination(
    raw_eval_input: Mapping[str, Any],
    *,
    project_root: str | Path,
) -> TrustedEvalCoordinationReceipt:
    """Re-execute canonical evaluation + repair and mint one opaque routing receipt."""
    if not isinstance(raw_eval_input, Mapping):
        raise _fail("TRUSTED_ADAPTER_SOURCE_MAPPING_REQUIRED")
    root = require_governed_project_root(project_root)
    policy = load_trusted_adapter_policy(root)
    repair_policy = load_yaml(root / TARGETED_REPAIR_POLICY_PATH)
    validate_trusted_adapter_policy(root)
    adapter = require_mapping(
        require_mapping(policy.get("trusted_adapters"), "TRUSTED_ADAPTERS_INVALID")[_ADAPTER_ID],
        "TRUSTED_ADAPTER_SPEC_INVALID",
    )

    plan = plan_targeted_repair(raw_eval_input, project_root=root)
    source_binding = require_mapping(plan.get("source_binding"), "TRUSTED_ADAPTER_SOURCE_BINDING_INVALID")
    required_mode = str(adapter.get("source_binding_mode_required") or "")
    if source_binding.get("mode") != required_mode:
        raise _fail(
            "TRUSTED_ADAPTER_SOURCE_BINDING_MISMATCH",
            expected=required_mode,
            observed=source_binding.get("mode"),
        )
    if source_binding.get("serialized_eval_result_accepted") is not False:
        raise _fail("TRUSTED_ADAPTER_SERIALIZED_EVAL_ACCEPTED")
    if plan.get("routing_policy_id") != adapter.get("targeted_repair_policy_id_required"):
        raise _fail("TRUSTED_ADAPTER_REPAIR_POLICY_ID_MISMATCH")
    for forbidden_true in (
        "prompt_mutation_authorized",
        "generation_authorized",
        "camera_authority_mutation_authorized",
        "canonical_mutation_authorized",
        "learning_writeback_authorized",
        "maturity_promotion_authorized",
        "causal_claim_authorized",
    ):
        if plan.get(forbidden_true) is not False:
            raise _fail("TRUSTED_ADAPTER_UPSTREAM_AUTHORITY_LEAK", field=forbidden_true)

    items: list[TrustedRepairItem] = []
    for raw in plan.get("repair_items") or []:
        item = require_mapping(raw, "TRUSTED_ADAPTER_REPAIR_ITEM_INVALID")
        outcome = str(item.get("outcome") or "").upper()
        if outcome not in {"FAIL", "UNKNOWN"}:
            raise _fail("TRUSTED_ADAPTER_REPAIR_ITEM_OUTCOME_INVALID", outcome=outcome)
        category = item.get("failure_category")
        if category is not None:
            category = str(category)
        items.append(
            TrustedRepairItem(
                field=str(item.get("field") or ""),
                outcome=outcome,
                failure_category=category,
                repair_surface=str(item.get("repair_surface") or ""),
                evidence_refs=tuple(str(x) for x in item.get("evidence_refs") or []),
            )
        )

    context = raw_eval_input.get("context")
    work_item_projection = None
    if isinstance(context, Mapping):
        candidate = str(context.get("work_item_id") or "").strip()
        work_item_projection = candidate or None

    digest = _stable_digest(dict(raw_eval_input))
    eval_id = str(plan.get("source_eval_id") or "UNSPECIFIED_EXPECTED_OBSERVED_EVAL")
    unsigned = TrustedEvalCoordinationReceipt(
        receipt_id=f"PICG-EOE::{eval_id}::{digest[:16]}",
        adapter_id=_ADAPTER_ID,
        source_eval_id=eval_id,
        source_eval_status=str(plan.get("source_eval_status") or ""),
        source_binding_mode=str(source_binding.get("mode") or ""),
        routing_policy_id=str(plan.get("routing_policy_id") or ""),
        work_item_projection=work_item_projection,
        source_input_digest=digest,
        adapter_policy_digest=_policy_digest(policy),
        targeted_repair_policy_digest=_policy_digest(repair_policy),
        repair_items=tuple(items),
        authority_refs=(
            "tools/learning_retriever/learning_retriever/expected_observed.py",
            "tools/learning_retriever/learning_retriever/targeted_repair.py",
            "10_运行时/targeted_repair_policy.yaml",
        ),
        _trust_token=_TRUST_TOKEN,
    )
    return TrustedEvalCoordinationReceipt(
        **{
            name: getattr(unsigned, name)
            for name in (
                "receipt_id",
                "adapter_id",
                "source_eval_id",
                "source_eval_status",
                "source_binding_mode",
                "routing_policy_id",
                "work_item_projection",
                "source_input_digest",
                "adapter_policy_digest",
                "targeted_repair_policy_digest",
                "repair_items",
                "authority_refs",
                "serialized_route_authority",
                "canonical_mutation_authorized",
                "learning_writeback_authorized",
            )
        },
        _integrity=_integrity_for(unsigned),
        _trust_token=_TRUST_TOKEN,
    )


def resolve_receipt_consumers(
    receipt: TrustedEvalCoordinationReceipt,
    *,
    project_root: str | Path,
    capability_ids: Iterable[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Resolve consumers only after fresh current-policy revalidation."""
    receipt = require_trusted_eval_receipt(receipt)
    root = require_governed_project_root(project_root)
    adapter_policy = load_trusted_adapter_policy(root)
    repair_policy = load_yaml(root / TARGETED_REPAIR_POLICY_PATH)
    validate_trusted_adapter_policy(root)

    if receipt.adapter_policy_digest != _policy_digest(adapter_policy):
        raise _fail("TRUSTED_ADAPTER_POLICY_STALE")
    if receipt.targeted_repair_policy_digest != _policy_digest(repair_policy):
        raise _fail("TRUSTED_ADAPTER_REPAIR_POLICY_STALE")

    adapters = require_mapping(adapter_policy.get("trusted_adapters"), "TRUSTED_ADAPTERS_INVALID")
    adapter = require_mapping(adapters.get(receipt.adapter_id), "TRUSTED_ADAPTER_SPEC_INVALID")
    if receipt.routing_policy_id != adapter.get("targeted_repair_policy_id_required"):
        raise _fail("TRUSTED_ADAPTER_REPAIR_POLICY_ID_MISMATCH")
    if receipt.routing_policy_id != repair_policy.get("policy_id"):
        raise _fail("TRUSTED_ADAPTER_REPAIR_POLICY_ID_MISMATCH")

    allowed_ids = set(str(x) for x in capability_ids)
    surface_allowlists = require_mapping(
        adapter_policy.get("repair_surface_capability_allowlist"),
        "TRUSTED_ADAPTER_SURFACE_ALLOWLIST_INVALID",
    )
    category_map = require_mapping(
        adapter_policy.get("failure_category_consumer_map"),
        "TRUSTED_ADAPTER_CATEGORY_MAP_INVALID",
    )
    unknown_policy = require_mapping(
        adapter_policy.get("unknown_outcome_consumer"),
        "TRUSTED_ADAPTER_UNKNOWN_POLICY_INVALID",
    )

    selected: list[str] = []
    signatures: list[str] = []
    for item in receipt.repair_items:
        surface_allowed = {str(x) for x in as_list(surface_allowlists.get(item.repair_surface))}
        if not surface_allowed:
            raise _fail(
                "TRUSTED_ADAPTER_REPAIR_SURFACE_UNKNOWN",
                repair_surface=item.repair_surface,
            )
        if item.outcome == "FAIL":
            if not item.failure_category:
                raise _fail("TRUSTED_ADAPTER_FAIL_WITHOUT_CATEGORY", field=item.field)
            consumers = tuple(str(x) for x in as_list(category_map.get(item.failure_category)))
            signatures.append(f"{item.failure_category}::{item.field}")
        elif item.outcome == "UNKNOWN":
            if item.failure_category not in (None, ""):
                raise _fail("TRUSTED_ADAPTER_UNKNOWN_WITH_FAILURE_CATEGORY", field=item.field)
            if item.repair_surface != unknown_policy.get("repair_surface_required"):
                raise _fail("TRUSTED_ADAPTER_UNKNOWN_SURFACE_MISMATCH", field=item.field)
            consumers = tuple(str(x) for x in as_list(unknown_policy.get("capability_consumers")))
            signatures.append(f"UNKNOWN::{item.field}")
        else:
            raise _fail("TRUSTED_ADAPTER_REPAIR_ITEM_OUTCOME_INVALID", outcome=item.outcome)

        if not consumers:
            raise _fail("TRUSTED_ADAPTER_ROUTE_WITHOUT_CONSUMER", field=item.field)
        illegal_surface = set(consumers) - surface_allowed
        if illegal_surface:
            raise _fail(
                "TRUSTED_ADAPTER_CONSUMER_ESCAPES_REPAIR_SURFACE",
                field=item.field,
                repair_surface=item.repair_surface,
                illegal=sorted(illegal_surface),
            )
        unknown_capabilities = set(consumers) - allowed_ids
        if unknown_capabilities:
            raise _fail(
                "TRUSTED_ADAPTER_UNKNOWN_CAPABILITY",
                field=item.field,
                capabilities=sorted(unknown_capabilities),
            )
        forbidden = set(consumers).intersection(_FORBIDDEN_CONSUMERS)
        if forbidden:
            raise _fail(
                "TRUSTED_ADAPTER_FORBIDDEN_CONSUMER",
                field=item.field,
                capabilities=sorted(forbidden),
            )
        for capability_id in consumers:
            if capability_id not in selected:
                selected.append(capability_id)

    return tuple(selected), tuple(signatures)
