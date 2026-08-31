"""Structured runtime for the candidate Production Intelligence Capability Atlas.

The runtime intentionally does not parse free-form director language. Natural-language
feature compilation remains owned by the existing Director Feature Compiler. This
module consumes already-structured problem signals, validates the capability graph,
selects bounded experiment strategies, and validates cross-department handoff packets.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

GRAPH_PATH = Path("10_运行时/production_intelligence_capability_graph.yaml")
HANDOFF_SCHEMA_PATH = Path("10_运行时/production_handoff_packet_schema.yaml")
REGRESSION_PATH = Path("11_验收/production_intelligence_capability_graph_regression_cases.yaml")


class ProductionIntelligenceError(ValueError):
    def __init__(self, code: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(code)


@dataclass(frozen=True)
class CapabilityResolution:
    problem_signatures: tuple[str, ...]
    selected_capabilities: tuple[str, ...]
    unmatched_signatures: tuple[str, ...]
    sparse_expansion: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "problem_signatures": list(self.problem_signatures),
            "selected_capabilities": list(self.selected_capabilities),
            "unmatched_signatures": list(self.unmatched_signatures),
            "sparse_expansion": self.sparse_expansion,
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProductionIntelligenceError("PICG_FILE_MISSING", details={"path": str(path)}) from exc
    except yaml.YAMLError as exc:
        raise ProductionIntelligenceError("PICG_YAML_INVALID", details={"path": str(path), "error": str(exc)}) from exc
    if not isinstance(payload, dict):
        raise ProductionIntelligenceError("PICG_DOCUMENT_NOT_MAPPING", details={"path": str(path)})
    return payload


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class CapabilityAtlas:
    """Validated read-only view over the candidate capability graph."""

    def __init__(self, graph: Mapping[str, Any]) -> None:
        self.graph = dict(graph)
        self._nodes: dict[str, dict[str, Any]] = {}
        self._validate_and_index()

    @classmethod
    def from_project_root(cls, project_root: str | Path) -> "CapabilityAtlas":
        root = Path(project_root)
        return cls(_load_yaml(root / GRAPH_PATH))

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
                raise ProductionIntelligenceError("PICG_EVAL_DIMENSION_INVALID", details={"dimension": dim_id})
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
                raise ProductionIntelligenceError("PICG_CAPABILITY_ID_INVALID", details={"capability_id": node_id})
            if node_id in self._nodes:
                raise ProductionIntelligenceError("PICG_DUPLICATE_CAPABILITY_ID", details={"capability_id": node_id})
            owner = node.get("department_owner")
            if owner not in participants:
                raise ProductionIntelligenceError(
                    "PICG_CAPABILITY_OWNER_UNKNOWN",
                    details={"capability_id": node_id, "owner": owner},
                )
            node_zones = set(_as_list(node.get("epistemic_zones")))
            if not node_zones or not node_zones.issubset(expected_zones):
                raise ProductionIntelligenceError(
                    "PICG_CAPABILITY_ZONE_INVALID",
                    details={"capability_id": node_id, "zones": sorted(node_zones)},
                )
            node_dimensions = _as_list(node.get("evaluation_dimensions"))
            for dimension in node_dimensions:
                if dimension in {"material_dimensions_from_handoff_only", "experiment_specific"}:
                    continue
                if dimension not in dimensions:
                    raise ProductionIntelligenceError(
                        "PICG_CAPABILITY_EVAL_DIMENSION_UNKNOWN",
                        details={"capability_id": node_id, "dimension": dimension},
                    )
            self._nodes[node_id] = dict(node)

        for node_id, node in self._nodes.items():
            for target in _as_list(node.get("handoff_to")):
                if isinstance(target, str) and target.startswith("CAP-") and target not in self._nodes:
                    raise ProductionIntelligenceError(
                        "PICG_HANDOFF_TARGET_UNKNOWN",
                        details={"capability_id": node_id, "target": target},
                    )

        strategies = self.graph.get("experiment_strategy_router")
        if not isinstance(strategies, Mapping):
            raise ProductionIntelligenceError("PICG_EXPERIMENT_ROUTER_MISSING")
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
        if set(strategies) != expected_strategies:
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
        problem_signatures: Iterable[str],
        *,
        material_capabilities: Iterable[str] = (),
    ) -> CapabilityResolution:
        """Resolve exact structured signatures without performing free-text NLP.

        `material_capabilities` is an explicit sparse expansion supplied by an
        upstream director/authority layer. The atlas never recursively expands every
        handoff target because doing so would create department over-expansion.
        """
        signatures = tuple(dict.fromkeys(str(x).strip() for x in problem_signatures if str(x).strip()))
        selected: list[str] = []
        matched: set[str] = set()
        for node_id, node in self._nodes.items():
            node_signatures = {str(x) for x in _as_list(node.get("problem_signatures"))}
            intersection = node_signatures.intersection(signatures)
            if intersection:
                matched.update(intersection)
                selected.append(node_id)

        for capability_id in material_capabilities:
            capability_id = str(capability_id).strip()
            if not capability_id:
                continue
            if capability_id not in self._nodes:
                raise ProductionIntelligenceError(
                    "PICG_CAPABILITY_UNKNOWN", details={"capability_id": capability_id}
                )
            if capability_id not in selected:
                selected.append(capability_id)

        unmatched = tuple(sig for sig in signatures if sig not in matched)
        return CapabilityResolution(signatures, tuple(selected), unmatched, True)

    def select_experiment_strategy(self, profile: Mapping[str, Any]) -> str:
        """Choose a bounded strategy from structured uncertainty metadata.

        This is a routing heuristic, not a statistical inference engine. It selects
        the *form* of the next information-gathering step and makes no significance
        claim.
        """
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


def _require_mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProductionIntelligenceError(code)
    return value


def validate_handoff_packet(
    packet: Mapping[str, Any],
    *,
    expected_work_item_id: str | None = None,
) -> bool:
    """Validate authority/epistemic invariants of a handoff packet.

    The function intentionally does not decide creative correctness or evaluation
    verdicts. It only checks coordination invariants that must survive handoff.
    """
    required = {
        "packet_id",
        "task",
        "context",
        "participant",
        "authority_receipt",
        "creative_contract",
        "inputs",
        "expected_outputs",
        "acceptance_contract",
        "unresolved_unknowns",
        "next_handoff",
    }
    missing = sorted(required.difference(packet))
    if missing:
        raise ProductionIntelligenceError("HANDOFF_REQUIRED_FIELD_MISSING", details={"missing": missing})

    context = _require_mapping(packet["context"], "HANDOFF_CONTEXT_INVALID")
    observed_work_item = str(context.get("work_item_id_when_required") or "").strip()
    expected = str(expected_work_item_id or "").strip()
    if expected and observed_work_item != expected:
        raise ProductionIntelligenceError(
            "WORK_ITEM_IDENTITY_MISMATCH",
            details={"expected": expected, "observed": observed_work_item or None},
        )

    authority = _require_mapping(packet["authority_receipt"], "HANDOFF_AUTHORITY_RECEIPT_INVALID")
    for item in _as_list(authority.get("inferred_user_constraints")):
        if not isinstance(item, Mapping):
            raise ProductionIntelligenceError("K2_INFERENCE_INVALID")
        if not all(item.get(key) not in (None, "", []) for key in ("statement", "confidence", "evidence")):
            raise ProductionIntelligenceError("K2_INFERENCE_MISSING_PROVENANCE")
        if item.get("explicit_user_confirmed") is True:
            raise ProductionIntelligenceError("K2_INFERENCE_MASQUERADES_AS_EXPLICIT_USER_FACT")

    for item in _as_list(authority.get("external_candidate_refs")):
        if not isinstance(item, Mapping):
            raise ProductionIntelligenceError("K3_EXTERNAL_CANDIDATE_INVALID")
        required_external = ("source_ref", "supported_claim", "project_translation", "scope", "boundary", "maturity")
        if not all(item.get(key) not in (None, "", []) for key in required_external):
            raise ProductionIntelligenceError("K3_EXTERNAL_CANDIDATE_MISSING_BOUNDARY")
        if str(item.get("maturity")).casefold() not in {"candidate", "needs_revalidation", "conflicted"}:
            raise ProductionIntelligenceError("K3_EXTERNAL_CANDIDATE_ILLEGAL_MATURITY")

    for unknown in _as_list(packet.get("unresolved_unknowns")):
        if not isinstance(unknown, Mapping):
            raise ProductionIntelligenceError("K4_UNKNOWN_INVALID")
        if unknown.get("epistemic_zone") != "K4_FRONTIER_OR_OPAQUE":
            raise ProductionIntelligenceError("K4_UNKNOWN_WRONG_ZONE")
        if unknown.get("materiality") == "HIGH" and not unknown.get("next_information_action"):
            raise ProductionIntelligenceError("K4_MATERIAL_UNKNOWN_MISSING_NEXT_ACTION")

    inputs = _require_mapping(packet["inputs"], "HANDOFF_INPUTS_INVALID")
    responsibilities = inputs.get("reference_responsibilities")
    if isinstance(responsibilities, Mapping):
        for namespace, claim in responsibilities.items():
            if not isinstance(claim, Mapping):
                raise ProductionIntelligenceError(
                    "REFERENCE_RESPONSIBILITY_INVALID", details={"namespace": namespace}
                )
            owners = claim.get("owners")
            if isinstance(owners, list) and len(set(str(x) for x in owners)) > 1 and claim.get("both_declared_strong") is True and claim.get("compatibility_proven") is not True:
                raise ProductionIntelligenceError(
                    "STRONG_REFERENCE_RESPONSIBILITY_CONFLICT",
                    details={"namespace": namespace, "owners": owners},
                )

    acceptance = _require_mapping(packet["acceptance_contract"], "HANDOFF_ACCEPTANCE_INVALID")
    material_dimensions = _as_list(acceptance.get("material_dimensions"))
    if not material_dimensions:
        raise ProductionIntelligenceError("HANDOFF_MATERIAL_DIMENSIONS_MISSING")
    pass_logic = acceptance.get("pass_logic")
    if isinstance(pass_logic, Mapping) and pass_logic.get("global_score_overrides_material_failure") is True:
        raise ProductionIntelligenceError("GLOBAL_SCORE_HIDES_MATERIAL_FAILURE")

    experiment = packet.get("experiment_contract")
    if isinstance(experiment, Mapping):
        factors = _as_list(experiment.get("factors"))
        if len(factors) > 1 and not experiment.get("factor_ledger"):
            raise ProductionIntelligenceError("MULTIFACTOR_EXPERIMENT_WITHOUT_LEDGER")
        if experiment.get("proxy_pass_equals_final_pass") is True:
            raise ProductionIntelligenceError("PROXY_FINAL_CONFUSION")

    return True


def validate_project(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root)
    graph = _load_yaml(root / GRAPH_PATH)
    handoff = _load_yaml(root / HANDOFF_SCHEMA_PATH)
    regression = _load_yaml(root / REGRESSION_PATH)
    atlas = CapabilityAtlas(graph)

    if handoff.get("schema_id") != "EUSTIA_PRODUCTION_HANDOFF_PACKET":
        raise ProductionIntelligenceError("HANDOFF_SCHEMA_ID_MISMATCH")
    if not str(handoff.get("status") or "").startswith("candidate"):
        raise ProductionIntelligenceError("HANDOFF_UNREVIEWED_SCHEMA_MUST_REMAIN_CANDIDATE")

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
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    print(validate_project(args.project_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
