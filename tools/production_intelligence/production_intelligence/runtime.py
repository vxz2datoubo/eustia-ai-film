"""Candidate Production Intelligence Capability Atlas runtime.

This runtime coordinates already-adjudicated production failures. Serialized
Signal Envelopes remain structural transport metadata only; they are not accepted
as routing authority. The first trusted route is canonical Expected-vs-Observed
re-execution through canonical Targeted Repair, followed by sparse capability
consumer selection constrained by the existing repair surface.

Final receipt consumption always fresh-reads the current adapter and canonical
Targeted Repair policy through the governed source root. Atlas construction-time policy
objects are diagnostics only and cannot freeze old routing semantics into authority.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .contracts import (
    GRAPH_PATH,
    HANDOFF_SCHEMA_PATH,
    RESEARCH_POLICY_PATH,
    SIGNAL_SCHEMA_PATH,
    ProductionIntelligenceError,
    as_list,
    load_yaml,
    validate_handoff_packet as _validate_handoff_packet,
    validate_handoff_schema,
    validate_handoff_transition as _validate_handoff_transition,
    validate_research_policy,
    validate_signal_schema,
    validate_workflow_coverage,
)
from .trust_root import governed_project_root, require_governed_project_root
from .trusted_adapter import (
    TRUSTED_ADAPTER_POLICY_PATH,
    TrustedEvalCoordinationReceipt,
    compile_expected_observed_coordination,
    load_trusted_adapter_policy,
    require_trusted_eval_receipt,
    resolve_receipt_consumers,
    validate_trusted_adapter_policy,
)

REGRESSION_PATH = Path("11_验收/production_intelligence_capability_graph_regression_cases.yaml")


@dataclass(frozen=True)
class CapabilityResolution:
    signal_id: str
    signal_type: str
    source_stage: str
    materiality: str
    problem_signatures: tuple[str, ...]
    selected_capabilities: tuple[str, ...]
    unmatched_signatures: tuple[str, ...]
    trusted_adapter: str
    work_item_projection: str | None
    sparse_expansion: bool = True
    admitted: bool = True
    consumer_policy_enforced: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "source_stage": self.source_stage,
            "materiality": self.materiality,
            "problem_signatures": list(self.problem_signatures),
            "selected_capabilities": list(self.selected_capabilities),
            "unmatched_signatures": list(self.unmatched_signatures),
            "trusted_adapter": self.trusted_adapter,
            "work_item_projection": self.work_item_projection,
            "work_item_projection_is_authority": False,
            "sparse_expansion": self.sparse_expansion,
            "admitted": self.admitted,
            "consumer_policy_enforced": self.consumer_policy_enforced,
            "serialized_signal_envelope_route_authority": False,
            "authority_boundary": "coordination_receipt_only",
        }


class CapabilityAtlas:
    """Validated read-only view over the candidate capability graph.

    Public ``resolve`` deliberately refuses caller-authored dictionaries. A route
    must first pass a trusted in-process adapter that re-executes an existing
    canonical runtime. Trust-bearing Atlas construction is mechanically pinned to the
    repository root containing this executing governed package.
    """

    def __init__(
        self,
        graph: Mapping[str, Any],
        signal_schema: Mapping[str, Any],
        trusted_adapter_policy: Mapping[str, Any],
        *,
        project_root: str | Path,
    ) -> None:
        self.project_root = require_governed_project_root(project_root)
        self.graph = dict(graph)
        self.signal_schema = dict(signal_schema)
        # Kept for inspection/validation only. Final resolve does not trust this cached
        # object; trusted_adapter.resolve_receipt_consumers fresh-reads from project_root.
        self.trusted_adapter_policy = dict(trusted_adapter_policy)
        validate_signal_schema(self.signal_schema)
        self._nodes: dict[str, dict[str, Any]] = {}
        self._validate_and_index()

    @classmethod
    def from_project_root(cls, project_root: str | Path) -> "CapabilityAtlas":
        root = require_governed_project_root(project_root)
        graph = load_yaml(root / GRAPH_PATH)
        validate_trusted_adapter_policy(root, graph=graph)
        return cls(
            graph,
            load_yaml(root / SIGNAL_SCHEMA_PATH),
            load_trusted_adapter_policy(root),
            project_root=root,
        )

    def _validate_and_index(self) -> None:
        if self.graph.get("graph_id") != "EUSTIA_PRODUCTION_INTELLIGENCE_CAPABILITY_GRAPH":
            raise ProductionIntelligenceError("PICG_GRAPH_ID_MISMATCH")
        if not str(self.graph.get("status") or "").startswith("candidate"):
            raise ProductionIntelligenceError("PICG_UNREVIEWED_GRAPH_MUST_REMAIN_CANDIDATE")

        zones = self.graph.get("epistemic_zones")
        expected_zones = {
            "K1_EXPLICIT_USER",
            "K2_TACIT_OR_IMPLICIT",
            "K3_ADJACENT_EXPERT",
            "K4_FRONTIER_OR_OPAQUE",
        }
        if not isinstance(zones, Mapping) or set(zones) != expected_zones:
            raise ProductionIntelligenceError("PICG_EPISTEMIC_ZONE_CONTRACT_INVALID")

        participants = self.graph.get("participant_roles")
        if not isinstance(participants, Mapping) or not participants:
            raise ProductionIntelligenceError("PICG_PARTICIPANT_ROLES_MISSING")

        dimensions = self.graph.get("evaluation_dimension_registry")
        if not isinstance(dimensions, Mapping) or not dimensions:
            raise ProductionIntelligenceError("PICG_EVAL_DIMENSION_REGISTRY_MISSING")
        for dim_id, dim in dimensions.items():
            if not isinstance(dim, Mapping):
                raise ProductionIntelligenceError(
                    "PICG_EVAL_DIMENSION_INVALID", details={"dimension": dim_id}
                )
            owner = dim.get("owner")
            if owner not in participants:
                raise ProductionIntelligenceError(
                    "PICG_EVAL_DIMENSION_OWNER_UNKNOWN",
                    details={"dimension": dim_id, "owner": owner},
                )

        nodes = self.graph.get("capability_nodes")
        if not isinstance(nodes, list) or not nodes:
            raise ProductionIntelligenceError("PICG_CAPABILITY_NODES_MISSING")
        for node in nodes:
            if not isinstance(node, Mapping):
                raise ProductionIntelligenceError("PICG_CAPABILITY_NODE_INVALID")
            node_id = str(node.get("capability_id") or "").strip()
            if not node_id.startswith("CAP-"):
                raise ProductionIntelligenceError(
                    "PICG_CAPABILITY_ID_INVALID", details={"capability_id": node_id}
                )
            if node_id in self._nodes:
                raise ProductionIntelligenceError(
                    "PICG_DUPLICATE_CAPABILITY_ID", details={"capability_id": node_id}
                )
            owner = node.get("department_owner")
            if owner not in participants:
                raise ProductionIntelligenceError(
                    "PICG_CAPABILITY_OWNER_UNKNOWN",
                    details={"capability_id": node_id, "owner": owner},
                )
            node_zones = set(as_list(node.get("epistemic_zones")))
            if not node_zones or not node_zones.issubset(expected_zones):
                raise ProductionIntelligenceError(
                    "PICG_CAPABILITY_ZONE_INVALID",
                    details={"capability_id": node_id, "zones": sorted(node_zones)},
                )
            for dimension in as_list(node.get("evaluation_dimensions")):
                if dimension in {"material_dimensions_from_handoff_only", "experiment_specific"}:
                    continue
                if dimension not in dimensions:
                    raise ProductionIntelligenceError(
                        "PICG_CAPABILITY_EVAL_DIMENSION_UNKNOWN",
                        details={"capability_id": node_id, "dimension": dimension},
                    )
            self._nodes[node_id] = dict(node)

        for node_id, node in self._nodes.items():
            for target in as_list(node.get("handoff_to")):
                if isinstance(target, str) and target.startswith("CAP-") and target not in self._nodes:
                    raise ProductionIntelligenceError(
                        "PICG_HANDOFF_TARGET_UNKNOWN",
                        details={"capability_id": node_id, "target": target},
                    )

        strategies = self.graph.get("experiment_strategy_router")
        expected_strategies = {
            "NONE",
            "COMPARATIVE_AB",
            "SCREENING",
            "BOUNDED_FACTORIAL",
            "SEQUENTIAL_PROBE",
            "PARAMETER_SEARCH",
            "MEASUREMENT_SYSTEM_CHECK",
            "EXTERNAL_RESEARCH",
            "HUMAN_DECISION",
        }
        if not isinstance(strategies, Mapping) or set(strategies) != expected_strategies:
            raise ProductionIntelligenceError("PICG_EXPERIMENT_STRATEGIES_INVALID")

    @property
    def capability_ids(self) -> tuple[str, ...]:
        return tuple(self._nodes)

    def node(self, capability_id: str) -> dict[str, Any]:
        try:
            return dict(self._nodes[capability_id])
        except KeyError as exc:
            raise ProductionIntelligenceError(
                "PICG_CAPABILITY_UNKNOWN", details={"capability_id": capability_id}
            ) from exc

    def resolve(
        self,
        signal_receipt: TrustedEvalCoordinationReceipt,
        *,
        expected_work_item_id: str | None = None,
    ) -> CapabilityResolution:
        receipt = require_trusted_eval_receipt(signal_receipt)
        expected_work_item = str(expected_work_item_id or "").strip()
        observed_work_item = str(receipt.work_item_projection or "").strip()
        if expected_work_item:
            if not observed_work_item:
                raise ProductionIntelligenceError(
                    "TRUSTED_ADAPTER_WORK_ITEM_PROJECTION_REQUIRED",
                    details={"expected": expected_work_item},
                )
            if observed_work_item != expected_work_item:
                raise ProductionIntelligenceError(
                    "TRUSTED_ADAPTER_WORK_ITEM_PROJECTION_MISMATCH",
                    details={"expected": expected_work_item, "observed": observed_work_item},
                )

        selected, signatures = resolve_receipt_consumers(
            receipt,
            project_root=self.project_root,
            capability_ids=self.capability_ids,
        )
        if any(item.outcome == "FAIL" for item in receipt.repair_items):
            materiality = "MATERIAL"
        elif any(item.outcome == "UNKNOWN" for item in receipt.repair_items):
            materiality = "DIAGNOSTIC"
        else:
            materiality = "INFORMATIONAL"

        return CapabilityResolution(
            signal_id=receipt.receipt_id,
            signal_type="EVAL_DIMENSION_RESULT",
            source_stage="EVALUATED",
            materiality=materiality,
            problem_signatures=signatures,
            selected_capabilities=selected,
            unmatched_signatures=(),
            trusted_adapter=receipt.adapter_id,
            work_item_projection=receipt.work_item_projection,
        )

    def resolve_expected_observed(
        self,
        raw_eval_input: Mapping[str, Any],
        *,
        project_root: str | Path,
        expected_work_item_id: str | None = None,
    ) -> CapabilityResolution:
        requested_root = require_governed_project_root(project_root)
        if requested_root != self.project_root:
            raise ProductionIntelligenceError(
                "TRUSTED_ADAPTER_PROJECT_ROOT_MISMATCH",
                details={"atlas_root": str(self.project_root), "requested_root": str(requested_root)},
            )
        receipt = compile_expected_observed_coordination(
            raw_eval_input,
            project_root=self.project_root,
        )
        return self.resolve(receipt, expected_work_item_id=expected_work_item_id)

    def select_experiment_strategy(self, profile: Mapping[str, Any]) -> str:
        if profile.get("high_impact_human_choice") is True:
            return "HUMAN_DECISION"
        if profile.get("evaluator_disagreement") is True and profile.get("decision_impact") in {"MEDIUM", "HIGH"}:
            return "MEASUREMENT_SYSTEM_CHECK"
        if profile.get("external_knowledge_missing") is True:
            return "EXTERNAL_RESEARCH"
        if profile.get("expensive_final_model") is True and profile.get("valid_proxy_available") is True:
            return "SEQUENTIAL_PROBE"
        if profile.get("continuous_parameter") is True:
            return "PARAMETER_SEARCH"
        factor_count = int(profile.get("factor_count") or 0)
        if factor_count > 1 and profile.get("interaction_suspected") is True:
            return "BOUNDED_FACTORIAL"
        if factor_count > 1:
            return "SCREENING"
        if profile.get("primary_factor_known") is True or factor_count == 1:
            return "COMPARATIVE_AB"
        if profile.get("uncertainty_material") is True:
            return "EXTERNAL_RESEARCH"
        return "NONE"


def resolve_expected_observed(
    raw_eval_input: Mapping[str, Any],
    *,
    project_root: str | Path,
    expected_work_item_id: str | None = None,
) -> CapabilityResolution:
    root = require_governed_project_root(project_root)
    atlas = CapabilityAtlas.from_project_root(root)
    return atlas.resolve_expected_observed(
        raw_eval_input,
        project_root=root,
        expected_work_item_id=expected_work_item_id,
    )


def validate_handoff_packet(
    packet: Mapping[str, Any],
    *,
    project_root: str | Path,
    expected_work_item_id: str | None = None,
) -> bool:
    return _validate_handoff_packet(
        packet,
        project_root=project_root,
        expected_work_item_id=expected_work_item_id,
    )


def validate_handoff_transition(
    upstream_packet: Mapping[str, Any],
    downstream_packet: Mapping[str, Any],
    *,
    project_root: str | Path,
    expected_work_item_id: str | None = None,
) -> bool:
    return _validate_handoff_transition(
        upstream_packet,
        downstream_packet,
        project_root=project_root,
        expected_work_item_id=expected_work_item_id,
    )


def validate_project(project_root: str | Path) -> dict[str, Any]:
    # Project validation is allowed to inspect only the governed checkout for this
    # production runtime. Separate pure policy validators retain fixture-root support.
    root = require_governed_project_root(project_root)
    graph = load_yaml(root / GRAPH_PATH)
    handoff = load_yaml(root / HANDOFF_SCHEMA_PATH)
    signal = load_yaml(root / SIGNAL_SCHEMA_PATH)
    research = load_yaml(root / RESEARCH_POLICY_PATH)
    regression = load_yaml(root / REGRESSION_PATH)

    validate_handoff_schema(handoff)
    validate_signal_schema(signal)
    validate_research_policy(research)
    validate_workflow_coverage(root)
    adapter_receipt = validate_trusted_adapter_policy(root, graph=graph)
    atlas = CapabilityAtlas(
        graph,
        signal,
        load_trusted_adapter_policy(root),
        project_root=root,
    )

    cases = regression.get("cases")
    if not isinstance(cases, list) or len(cases) < 20:
        raise ProductionIntelligenceError("PICG_REGRESSION_COVERAGE_TOO_SMALL")
    case_ids = [str(case.get("id") or "") for case in cases if isinstance(case, Mapping)]
    if len(case_ids) != len(set(case_ids)):
        raise ProductionIntelligenceError("PICG_DUPLICATE_REGRESSION_ID")

    return {
        "status": "PASS",
        "capability_count": len(atlas.capability_ids),
        "regression_case_count": len(cases),
        "epistemic_zone_count": len(graph["epistemic_zones"]),
        "evaluation_dimension_count": len(graph["evaluation_dimension_registry"]),
        "signal_type_count": len(signal["signal_types"]),
        "signal_envelope_bound": True,
        "serialized_signal_envelope_route_authority": False,
        "trusted_adapter_bound": True,
        "trusted_adapter_id": adapter_receipt["adapter_id"],
        "trusted_failure_category_count": adapter_receipt["failure_category_count"],
        "targeted_repair_policy_content_bound": bool(adapter_receipt.get("targeted_repair_policy_digest")),
        "final_consumer_fresh_policy_revalidation": True,
        "governed_project_root_bound": True,
        "handoff_nested_contract_bound": True,
        "research_policy_bound": True,
        "workflow_coverage_bound": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root",
        default=str(governed_project_root()),
        help="must resolve to the governed checkout; alternate authority roots are rejected",
    )
    args = parser.parse_args()
    print(validate_project(args.project_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
