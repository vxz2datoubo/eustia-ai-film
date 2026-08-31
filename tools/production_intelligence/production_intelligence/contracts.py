"""Fail-closed machine contracts for candidate Production Intelligence coordination.

These validators deliberately consume repository-owned candidate schemas. They do
not infer project story truth, parse director language, choose hard routes, evaluate
generated media, or promote learning maturity.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

GRAPH_PATH = Path("10_运行时/production_intelligence_capability_graph.yaml")
SIGNAL_SCHEMA_PATH = Path("10_运行时/production_intelligence_signal_envelope_schema.yaml")
HANDOFF_SCHEMA_PATH = Path("10_运行时/production_handoff_packet_schema.yaml")
RESEARCH_POLICY_PATH = Path("10_运行时/production_intelligence_research_intake_policy.yaml")
PICG_WORKFLOW_PATH = Path(".github/workflows/production-intelligence-capability-atlas.yml")
LEARNING_WORKFLOW_PATH = Path(".github/workflows/learning-feature-compiler.yml")


class ProductionIntelligenceError(ValueError):
    def __init__(self, code: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(code)


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProductionIntelligenceError("PICG_FILE_MISSING", details={"path": str(path)}) from exc
    except yaml.YAMLError as exc:
        raise ProductionIntelligenceError("PICG_YAML_INVALID", details={"path": str(path), "error": str(exc)}) from exc
    if not isinstance(payload, dict):
        raise ProductionIntelligenceError("PICG_DOCUMENT_NOT_MAPPING", details={"path": str(path)})
    return payload


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def require_mapping(value: Any, code: str, *, path: str | None = None) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProductionIntelligenceError(code, details={"path": path} if path else None)
    return value


def require_list(value: Any, code: str, *, path: str | None = None) -> list[Any]:
    if not isinstance(value, list):
        raise ProductionIntelligenceError(code, details={"path": path} if path else None)
    return value


def require_fields(mapping: Mapping[str, Any], fields: list[str] | tuple[str, ...], code: str, *, path: str) -> None:
    missing = [field for field in fields if field not in mapping]
    if missing:
        raise ProductionIntelligenceError(code, details={"path": path, "missing": missing})


def nonempty_text(value: Any) -> bool:
    return bool(str(value or "").strip())


@dataclass(frozen=True)
class SignalAdmission:
    signal_id: str
    signal_type: str
    source_stage: str
    producer: str
    work_item_id: str | None
    materiality: str
    epistemic_zone: str
    authority_refs: tuple[str, ...]
    problem_signatures: tuple[str, ...]
    provenance_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "source_stage": self.source_stage,
            "producer": self.producer,
            "work_item_id": self.work_item_id,
            "materiality": self.materiality,
            "epistemic_zone": self.epistemic_zone,
            "authority_refs": list(self.authority_refs),
            "problem_signatures": list(self.problem_signatures),
            "provenance_count": self.provenance_count,
        }


def validate_signal_schema(schema: Mapping[str, Any]) -> None:
    if schema.get("schema_id") != "EUSTIA_PRODUCTION_INTELLIGENCE_SIGNAL_ENVELOPE":
        raise ProductionIntelligenceError("SIGNAL_SCHEMA_ID_MISMATCH")
    if not str(schema.get("status") or "").startswith("candidate"):
        raise ProductionIntelligenceError("SIGNAL_SCHEMA_MUST_REMAIN_CANDIDATE")

    required_fields = set(as_list(schema.get("required_fields")))
    expected_required = {
        "signal_id", "signal_type", "source_stage", "producer",
        "work_item_id_when_required", "materiality", "epistemic_zone",
        "authority_refs", "payload", "provenance_chain",
    }
    if not expected_required.issubset(required_fields):
        raise ProductionIntelligenceError(
            "SIGNAL_SCHEMA_REQUIRED_FIELDS_INCOMPLETE",
            details={"missing": sorted(expected_required - required_fields)},
        )

    signal_types = require_mapping(schema.get("signal_types"), "SIGNAL_SCHEMA_TYPES_INVALID")
    source_stages = set(as_list(schema.get("source_stages")))
    if not signal_types or not source_stages:
        raise ProductionIntelligenceError("SIGNAL_SCHEMA_VOCABULARY_EMPTY")
    for signal_type, spec in signal_types.items():
        spec = require_mapping(spec, "SIGNAL_SCHEMA_TYPE_SPEC_INVALID", path=f"signal_types.{signal_type}")
        valid_stages = set(as_list(spec.get("valid_source_stages")))
        if not valid_stages or not valid_stages.issubset(source_stages):
            raise ProductionIntelligenceError(
                "SIGNAL_SCHEMA_TYPE_STAGE_CONTRACT_INVALID",
                details={"signal_type": signal_type, "valid_source_stages": sorted(valid_stages)},
            )

    producer_contract = require_mapping(schema.get("producer_contract"), "SIGNAL_PRODUCER_CONTRACT_INVALID")
    allowed_producers = set(as_list(producer_contract.get("allowed")))
    by_signal_type = require_mapping(
        producer_contract.get("by_signal_type"),
        "SIGNAL_PRODUCER_TYPE_BINDING_MISSING",
    )
    if set(by_signal_type) != set(signal_types):
        raise ProductionIntelligenceError(
            "SIGNAL_PRODUCER_TYPE_BINDING_INCOMPLETE",
            details={
                "missing": sorted(set(signal_types) - set(by_signal_type)),
                "extra": sorted(set(by_signal_type) - set(signal_types)),
            },
        )
    for signal_type, producers in by_signal_type.items():
        producer_set = set(as_list(producers))
        if not producer_set or not producer_set.issubset(allowed_producers):
            raise ProductionIntelligenceError(
                "SIGNAL_PRODUCER_TYPE_BINDING_INVALID",
                details={"signal_type": signal_type, "producers": sorted(producer_set)},
            )

    routing = require_mapping(schema.get("capability_routing"), "SIGNAL_CAPABILITY_ROUTING_CONTRACT_MISSING")
    routable = set(as_list(routing.get("routable_signal_types")))
    if not routable or not routable.issubset(set(signal_types)):
        raise ProductionIntelligenceError("SIGNAL_CAPABILITY_ROUTING_TYPES_INVALID")
    if routing.get("caller_capability_ids_forbidden") is not True:
        raise ProductionIntelligenceError("SIGNAL_CALLER_CAPABILITY_INJECTION_NOT_FORBIDDEN")
    if routing.get("informational_signal_mode") != "receipt_only_no_capability_selection":
        raise ProductionIntelligenceError("SIGNAL_INFORMATIONAL_ROUTING_MODE_UNSAFE")


def validate_signal_envelope(
    envelope: Mapping[str, Any],
    *,
    schema: Mapping[str, Any],
    expected_work_item_id: str | None = None,
) -> SignalAdmission:
    validate_signal_schema(schema)
    envelope = require_mapping(envelope, "SIGNAL_ENVELOPE_REQUIRED")
    required = [str(x) for x in as_list(schema.get("required_fields"))]
    require_fields(envelope, required, "SIGNAL_REQUIRED_FIELD_MISSING", path="signal")

    signal_id = str(envelope.get("signal_id") or "").strip()
    signal_type = str(envelope.get("signal_type") or "").strip()
    source_stage = str(envelope.get("source_stage") or "").strip()
    producer = str(envelope.get("producer") or "").strip()
    if not signal_id:
        raise ProductionIntelligenceError("SIGNAL_ID_MISSING")

    signal_types = require_mapping(schema.get("signal_types"), "SIGNAL_SCHEMA_TYPES_INVALID")
    if signal_type not in signal_types:
        raise ProductionIntelligenceError("SIGNAL_TYPE_UNKNOWN", details={"signal_type": signal_type})
    type_spec = require_mapping(signal_types[signal_type], "SIGNAL_SCHEMA_TYPE_SPEC_INVALID")
    valid_stages = set(str(x) for x in as_list(type_spec.get("valid_source_stages")))
    if source_stage not in valid_stages:
        raise ProductionIntelligenceError(
            "SIGNAL_TYPE_STAGE_MISMATCH",
            details={"signal_type": signal_type, "source_stage": source_stage, "valid": sorted(valid_stages)},
        )

    producer_contract = require_mapping(schema.get("producer_contract"), "SIGNAL_PRODUCER_CONTRACT_INVALID")
    allowed_by_type = require_mapping(
        producer_contract.get("by_signal_type"),
        "SIGNAL_PRODUCER_TYPE_BINDING_MISSING",
    )
    expected_producers = set(str(x) for x in as_list(allowed_by_type.get(signal_type)))
    if producer not in expected_producers:
        raise ProductionIntelligenceError(
            "SIGNAL_PRODUCER_TYPE_MISMATCH",
            details={"signal_type": signal_type, "producer": producer, "allowed": sorted(expected_producers)},
        )

    expected_work_item = str(expected_work_item_id or "").strip()
    observed_work_item = str(envelope.get("work_item_id_when_required") or "").strip()
    required_types = set(str(x) for x in as_list(schema.get("work_item_required_signal_types")))
    if signal_type in required_types and not observed_work_item:
        raise ProductionIntelligenceError("SIGNAL_WORK_ITEM_IDENTITY_REQUIRED", details={"signal_type": signal_type})
    if expected_work_item and observed_work_item != expected_work_item:
        raise ProductionIntelligenceError(
            "SIGNAL_WORK_ITEM_IDENTITY_MISMATCH",
            details={"expected": expected_work_item, "observed": observed_work_item or None},
        )

    materiality = str(envelope.get("materiality") or "").strip()
    materiality_spec = require_mapping(schema.get("materiality"), "SIGNAL_MATERIALITY_SCHEMA_INVALID")
    allowed_materiality = set(str(x) for x in as_list(materiality_spec.get("values")))
    if materiality not in allowed_materiality:
        raise ProductionIntelligenceError("SIGNAL_MATERIALITY_INVALID", details={"materiality": materiality})

    epistemic_zone = str(envelope.get("epistemic_zone") or "").strip()
    epistemic_spec = require_mapping(schema.get("epistemic_zone"), "SIGNAL_EPISTEMIC_SCHEMA_INVALID")
    allowed_zones = set(str(x) for x in as_list(epistemic_spec.get("values")))
    if epistemic_zone not in allowed_zones:
        raise ProductionIntelligenceError("SIGNAL_EPISTEMIC_ZONE_INVALID", details={"zone": epistemic_zone})

    authority_refs_raw = require_list(envelope.get("authority_refs"), "SIGNAL_AUTHORITY_REFS_INVALID")
    authority_refs = tuple(str(x).strip() for x in authority_refs_raw if str(x).strip())
    if not authority_refs:
        raise ProductionIntelligenceError("SIGNAL_AUTHORITY_REFS_MISSING")

    payload = require_mapping(envelope.get("payload"), "SIGNAL_PAYLOAD_INVALID")
    forbidden_capability_keys = {"material_capabilities", "selected_capabilities", "capability_ids", "force_capabilities"}
    injected = sorted(forbidden_capability_keys.intersection(payload))
    if injected:
        raise ProductionIntelligenceError(
            "CALLER_CAPABILITY_SELECTION_FORBIDDEN",
            details={"keys": injected},
        )
    signatures_raw = payload.get("problem_signatures", [])
    signatures_list = require_list(signatures_raw, "SIGNAL_PROBLEM_SIGNATURES_INVALID")
    problem_signatures = tuple(dict.fromkeys(str(x).strip() for x in signatures_list if str(x).strip()))

    provenance = require_list(envelope.get("provenance_chain"), "SIGNAL_PROVENANCE_INVALID")
    if not provenance:
        raise ProductionIntelligenceError("SIGNAL_PROVENANCE_MISSING")
    provenance_spec = require_mapping(schema.get("provenance_chain"), "SIGNAL_PROVENANCE_SCHEMA_INVALID")
    item_fields = [str(x) for x in as_list(provenance_spec.get("item_fields"))]
    allowed_actions = set(str(x) for x in as_list(provenance_spec.get("actions")))
    for index, item in enumerate(provenance):
        item = require_mapping(item, "SIGNAL_PROVENANCE_ITEM_INVALID", path=f"provenance_chain[{index}]")
        require_fields(item, item_fields, "SIGNAL_PROVENANCE_ITEM_MISSING_FIELD", path=f"provenance_chain[{index}]")
        if str(item.get("action") or "") not in allowed_actions:
            raise ProductionIntelligenceError("SIGNAL_PROVENANCE_ACTION_INVALID", details={"index": index})
    tail = require_mapping(provenance[-1], "SIGNAL_PROVENANCE_ITEM_INVALID")
    if str(tail.get("stage") or "") != source_stage or str(tail.get("producer") or "") != producer:
        raise ProductionIntelligenceError("SIGNAL_PROVENANCE_TAIL_MISMATCH")
    if str(tail.get("signal_or_packet_ref") or "") != signal_id:
        raise ProductionIntelligenceError("SIGNAL_PROVENANCE_IDENTITY_MISMATCH")

    return SignalAdmission(
        signal_id=signal_id,
        signal_type=signal_type,
        source_stage=source_stage,
        producer=producer,
        work_item_id=observed_work_item or None,
        materiality=materiality,
        epistemic_zone=epistemic_zone,
        authority_refs=authority_refs,
        problem_signatures=problem_signatures,
        provenance_count=len(provenance),
    )


def validate_handoff_schema(schema: Mapping[str, Any]) -> None:
    if schema.get("schema_id") != "EUSTIA_PRODUCTION_HANDOFF_PACKET":
        raise ProductionIntelligenceError("HANDOFF_SCHEMA_ID_MISMATCH")
    if not str(schema.get("status") or "").startswith("candidate"):
        raise ProductionIntelligenceError("HANDOFF_UNREVIEWED_SCHEMA_MUST_REMAIN_CANDIDATE")
    packet = require_mapping(schema.get("packet"), "HANDOFF_SCHEMA_PACKET_INVALID")
    top_required = set(str(x) for x in as_list(packet.get("required_fields")))
    expected_top = {
        "packet_id", "task", "context", "participant", "authority_receipt",
        "creative_contract", "inputs", "expected_outputs", "acceptance_contract",
        "unresolved_unknowns", "next_handoff",
    }
    if not expected_top.issubset(top_required):
        raise ProductionIntelligenceError("HANDOFF_SCHEMA_REQUIRED_FIELDS_INCOMPLETE")
    for section in (
        "task", "context", "participant", "authority_receipt", "creative_contract",
        "inputs", "expected_outputs", "acceptance_contract", "next_handoff",
    ):
        if not isinstance(packet.get(section), Mapping):
            raise ProductionIntelligenceError("HANDOFF_SCHEMA_SECTION_INVALID", details={"section": section})
    next_required = set(str(x) for x in as_list(packet["next_handoff"].get("required")))
    carry_required = {"next_owner", "next_task_class", "live_hard_invariants", "material_unknown_ids"}
    if not carry_required.issubset(next_required):
        raise ProductionIntelligenceError(
            "HANDOFF_SCHEMA_NEXT_CARRY_CONTRACT_INCOMPLETE",
            details={"missing": sorted(carry_required - next_required)},
        )


def validate_research_policy(policy: Mapping[str, Any]) -> None:
    if policy.get("policy_id") != "EUSTIA_PRODUCTION_INTELLIGENCE_RESEARCH_INTAKE_POLICY":
        raise ProductionIntelligenceError("RESEARCH_POLICY_ID_MISMATCH")
    if not str(policy.get("status") or "").startswith("candidate"):
        raise ProductionIntelligenceError("RESEARCH_POLICY_MUST_REMAIN_CANDIDATE")
    boundary = require_mapping(policy.get("authority_boundary"), "RESEARCH_POLICY_AUTHORITY_BOUNDARY_INVALID")
    rules = set(str(x) for x in as_list(boundary.get("rules")))
    required_rules = {
        "external_research_cannot_override_project_story_character_scene_map_asset_or_continuity",
        "external_research_cannot_self_promote_maturity",
    }
    if not required_rules.issubset(rules):
        raise ProductionIntelligenceError("RESEARCH_POLICY_AUTHORITY_RULES_INCOMPLETE")
    unit = require_mapping(policy.get("research_unit"), "RESEARCH_POLICY_UNIT_INVALID")
    required_unit = set(str(x) for x in as_list(unit.get("required_fields")))
    required_boundary_fields = {
        "research_question", "production_problem_ref", "source_ref", "source_tier",
        "source_date_or_version", "source_claim", "project_translation", "applicable_when",
        "not_applicable_when", "failure_boundary", "version_scope", "maturity",
        "targeted_validation", "integration_route",
    }
    if not required_boundary_fields.issubset(required_unit):
        raise ProductionIntelligenceError("RESEARCH_POLICY_UNIT_FIELDS_INCOMPLETE")
    routes = require_mapping(policy.get("integration_routes"), "RESEARCH_POLICY_ROUTES_INVALID")
    expected_routes = {
        "OFFICIAL_MODEL_OR_API", "INDUSTRY_INTEROP_STANDARD", "GENERATIVE_MEDIA_PAPER",
        "GENERATIVE_MEDIA_BENCHMARK", "MASTER_OR_PRODUCTION_CASE",
        "HUMAN_FACTORS_OR_COGNITIVE_RESEARCH", "SYSTEMS_ENGINEERING_OR_EXPERIMENT_METHOD",
    }
    if not expected_routes.issubset(routes):
        raise ProductionIntelligenceError("RESEARCH_POLICY_ROUTES_INCOMPLETE")


def _load_contract_bundle(project_root: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = Path(project_root)
    graph = load_yaml(root / GRAPH_PATH)
    handoff_schema = load_yaml(root / HANDOFF_SCHEMA_PATH)
    research_policy = load_yaml(root / RESEARCH_POLICY_PATH)
    validate_handoff_schema(handoff_schema)
    validate_research_policy(research_policy)
    return graph, handoff_schema, research_policy


def validate_handoff_packet(
    packet: Mapping[str, Any],
    *,
    project_root: str | Path,
    expected_work_item_id: str | None = None,
) -> bool:
    graph, schema, _ = _load_contract_bundle(project_root)
    packet_spec = require_mapping(schema.get("packet"), "HANDOFF_SCHEMA_PACKET_INVALID")
    packet = require_mapping(packet, "HANDOFF_PACKET_INVALID")
    required = [str(x) for x in as_list(packet_spec.get("required_fields"))]
    require_fields(packet, required, "HANDOFF_REQUIRED_FIELD_MISSING", path="packet")
    if not nonempty_text(packet.get("packet_id")):
        raise ProductionIntelligenceError("MISSING_PACKET_ID")

    participants = require_mapping(graph.get("participant_roles"), "PICG_PARTICIPANT_ROLES_MISSING")
    dimensions = require_mapping(graph.get("evaluation_dimension_registry"), "PICG_EVAL_DIMENSION_REGISTRY_MISSING")

    task_spec = require_mapping(packet_spec.get("task"), "HANDOFF_SCHEMA_TASK_INVALID")
    task = require_mapping(packet.get("task"), "HANDOFF_TASK_INVALID")
    require_fields(task, [str(x) for x in as_list(task_spec.get("required"))], "HANDOFF_TASK_REQUIRED_FIELD_MISSING", path="task")
    if not nonempty_text(task.get("task_id")):
        raise ProductionIntelligenceError("HANDOFF_TASK_ID_MISSING")
    task_class = str(task.get("task_class") or "")
    if task_class not in set(str(x) for x in as_list(task_spec.get("task_class_enum"))):
        raise ProductionIntelligenceError("HANDOFF_TASK_CLASS_INVALID", details={"task_class": task_class})
    state = str(task.get("state") or "")
    if state not in set(str(x) for x in as_list(task_spec.get("state_enum"))):
        raise ProductionIntelligenceError("HANDOFF_TASK_STATE_INVALID", details={"state": state})

    context_spec = require_mapping(packet_spec.get("context"), "HANDOFF_SCHEMA_CONTEXT_INVALID")
    context = require_mapping(packet.get("context"), "HANDOFF_CONTEXT_INVALID")
    require_fields(context, [str(x) for x in as_list(context_spec.get("required"))], "HANDOFF_CONTEXT_REQUIRED_FIELD_MISSING", path="context")
    if not nonempty_text(context.get("project_id")):
        raise ProductionIntelligenceError("HANDOFF_PROJECT_ID_MISSING")
    context_level = str(context.get("context_level") or "")
    if context_level not in set(str(x) for x in as_list(context_spec.get("context_level_enum"))):
        raise ProductionIntelligenceError("HANDOFF_CONTEXT_LEVEL_INVALID")
    observed_work_item = str(context.get("work_item_id_when_required") or "").strip()
    expected_work_item = str(expected_work_item_id or "").strip()
    if expected_work_item and observed_work_item != expected_work_item:
        raise ProductionIntelligenceError(
            "WORK_ITEM_IDENTITY_MISMATCH",
            details={"expected": expected_work_item, "observed": observed_work_item or None},
        )

    participant_spec = require_mapping(packet_spec.get("participant"), "HANDOFF_SCHEMA_PARTICIPANT_INVALID")
    participant = require_mapping(packet.get("participant"), "HANDOFF_PARTICIPANT_INVALID")
    require_fields(participant, [str(x) for x in as_list(participant_spec.get("required"))], "HANDOFF_PARTICIPANT_REQUIRED_FIELD_MISSING", path="participant")
    owner_role = str(participant.get("owner_role") or "").strip()
    if owner_role not in participants:
        raise ProductionIntelligenceError("HANDOFF_PARTICIPANT_OWNER_UNKNOWN", details={"owner_role": owner_role})

    authority_spec = require_mapping(packet_spec.get("authority_receipt"), "HANDOFF_SCHEMA_AUTHORITY_INVALID")
    authority = require_mapping(packet.get("authority_receipt"), "HANDOFF_AUTHORITY_RECEIPT_INVALID")
    require_fields(authority, [str(x) for x in as_list(authority_spec.get("required"))], "HANDOFF_AUTHORITY_REQUIRED_FIELD_MISSING", path="authority_receipt")
    if not nonempty_text(authority.get("project_index_ref")):
        raise ProductionIntelligenceError("HANDOFF_PROJECT_INDEX_REF_MISSING")
    if not isinstance(authority.get("canonical_refs_used"), list):
        raise ProductionIntelligenceError("HANDOFF_CANONICAL_REFS_INVALID")
    if not isinstance(authority.get("user_explicit_constraints"), list):
        raise ProductionIntelligenceError("HANDOFF_K1_CONSTRAINTS_INVALID")
    for item in as_list(authority.get("inferred_user_constraints")):
        item = require_mapping(item, "K2_INFERENCE_INVALID")
        if not all(item.get(key) not in (None, "", []) for key in ("statement", "confidence", "evidence")):
            raise ProductionIntelligenceError("K2_INFERENCE_MISSING_PROVENANCE")
        if item.get("explicit_user_confirmed") is True:
            raise ProductionIntelligenceError("K2_INFERENCE_MASQUERADES_AS_EXPLICIT_USER_FACT")
    for item in as_list(authority.get("external_candidate_refs")):
        item = require_mapping(item, "K3_EXTERNAL_CANDIDATE_INVALID")
        required_external = ("source_ref", "supported_claim", "project_translation", "scope", "boundary", "maturity")
        if not all(item.get(key) not in (None, "", []) for key in required_external):
            raise ProductionIntelligenceError("K3_EXTERNAL_CANDIDATE_MISSING_BOUNDARY")
        if str(item.get("maturity")).casefold() not in {"candidate", "needs_revalidation", "conflicted"}:
            raise ProductionIntelligenceError("K3_EXTERNAL_CANDIDATE_ILLEGAL_MATURITY")

    creative_spec = require_mapping(packet_spec.get("creative_contract"), "HANDOFF_SCHEMA_CREATIVE_INVALID")
    creative = require_mapping(packet.get("creative_contract"), "HANDOFF_CREATIVE_CONTRACT_INVALID")
    creative_required = [str(x) for x in as_list(creative_spec.get("required"))]
    require_fields(creative, creative_required, "HANDOFF_CREATIVE_REQUIRED_FIELD_MISSING", path="creative_contract")
    for list_field in ("hard_invariants", "guided_constraints", "free_space"):
        require_list(creative.get(list_field), "HANDOFF_CREATIVE_LIST_INVALID", path=f"creative_contract.{list_field}")
    hard_invariants = tuple(dict.fromkeys(str(x).strip() for x in creative.get("hard_invariants", []) if str(x).strip()))

    inputs_spec = require_mapping(packet_spec.get("inputs"), "HANDOFF_SCHEMA_INPUTS_INVALID")
    inputs = require_mapping(packet.get("inputs"), "HANDOFF_INPUTS_INVALID")
    require_fields(inputs, [str(x) for x in as_list(inputs_spec.get("required"))], "HANDOFF_INPUTS_REQUIRED_FIELD_MISSING", path="inputs")
    assets_spec = require_mapping(inputs_spec.get("consumed_assets"), "HANDOFF_SCHEMA_CONSUMED_ASSETS_INVALID")
    consumed_assets = require_list(inputs.get("consumed_assets"), "HANDOFF_CONSUMED_ASSETS_INVALID")
    role_enum = set(str(x) for x in as_list(assets_spec.get("role_enum")))
    for index, asset in enumerate(consumed_assets):
        asset = require_mapping(asset, "HANDOFF_CONSUMED_ASSET_ITEM_INVALID", path=f"inputs.consumed_assets[{index}]")
        for key in ("asset_ref", "role", "authority_status"):
            if not nonempty_text(asset.get(key)):
                raise ProductionIntelligenceError("HANDOFF_CONSUMED_ASSET_FIELD_MISSING", details={"index": index, "field": key})
        if str(asset.get("role")) not in role_enum:
            raise ProductionIntelligenceError("HANDOFF_CONSUMED_ASSET_ROLE_INVALID", details={"index": index})
    responsibilities_spec = require_mapping(inputs_spec.get("reference_responsibilities"), "HANDOFF_SCHEMA_REFERENCE_RESPONSIBILITY_INVALID")
    responsibilities = require_mapping(inputs.get("reference_responsibilities"), "HANDOFF_REFERENCE_RESPONSIBILITIES_INVALID")
    namespaces = set(str(x) for x in as_list(responsibilities_spec.get("namespaces")))
    owner_enum = set(str(x) for x in as_list(responsibilities_spec.get("owner_enum")))
    for namespace, claim in responsibilities.items():
        if namespace not in namespaces:
            raise ProductionIntelligenceError("REFERENCE_RESPONSIBILITY_NAMESPACE_UNKNOWN", details={"namespace": namespace})
        claim = require_mapping(claim, "REFERENCE_RESPONSIBILITY_INVALID", path=f"inputs.reference_responsibilities.{namespace}")
        owner = str(claim.get("owner") or "").strip()
        owners = [str(x).strip() for x in as_list(claim.get("owners")) if str(x).strip()]
        if owner:
            if owner not in owner_enum:
                raise ProductionIntelligenceError("REFERENCE_RESPONSIBILITY_OWNER_INVALID", details={"namespace": namespace, "owner": owner})
        elif not owners:
            raise ProductionIntelligenceError("REFERENCE_RESPONSIBILITY_OWNER_MISSING", details={"namespace": namespace})
        if any(x not in owner_enum for x in owners):
            raise ProductionIntelligenceError("REFERENCE_RESPONSIBILITY_OWNER_INVALID", details={"namespace": namespace})
        if len(set(owners)) > 1 and claim.get("both_declared_strong") is True and claim.get("compatibility_proven") is not True:
            raise ProductionIntelligenceError("STRONG_REFERENCE_RESPONSIBILITY_CONFLICT", details={"namespace": namespace, "owners": owners})

    expected_spec = require_mapping(packet_spec.get("expected_outputs"), "HANDOFF_SCHEMA_EXPECTED_OUTPUTS_INVALID")
    expected_outputs = require_mapping(packet.get("expected_outputs"), "HANDOFF_EXPECTED_OUTPUTS_INVALID")
    require_fields(expected_outputs, [str(x) for x in as_list(expected_spec.get("required"))], "HANDOFF_EXPECTED_OUTPUT_REQUIRED_FIELD_MISSING", path="expected_outputs")
    output_type = str(expected_outputs.get("output_type") or "")
    if output_type not in set(str(x) for x in as_list(expected_spec.get("output_type_enum"))):
        raise ProductionIntelligenceError("HANDOFF_OUTPUT_TYPE_INVALID")
    expectation_spec = require_mapping(expected_spec.get("observable_or_audible_expectations"), "HANDOFF_SCHEMA_EXPECTATION_INVALID")
    expectations = require_list(expected_outputs.get("observable_or_audible_expectations"), "HANDOFF_EXPECTATIONS_INVALID")
    if not expectations:
        raise ProductionIntelligenceError("HANDOFF_EXPECTATIONS_MISSING")
    expectation_fields = [str(x) for x in as_list(expectation_spec.get("item_fields"))]
    expectation_materiality = set(str(x) for x in as_list(expectation_spec.get("materiality_enum")))
    for index, expectation in enumerate(expectations):
        expectation = require_mapping(expectation, "HANDOFF_EXPECTATION_ITEM_INVALID")
        require_fields(expectation, expectation_fields, "HANDOFF_EXPECTATION_FIELD_MISSING", path=f"expected_outputs.observable_or_audible_expectations[{index}]")
        if str(expectation.get("materiality") or "") not in expectation_materiality:
            raise ProductionIntelligenceError("HANDOFF_EXPECTATION_MATERIALITY_INVALID", details={"index": index})

    acceptance_spec = require_mapping(packet_spec.get("acceptance_contract"), "HANDOFF_SCHEMA_ACCEPTANCE_INVALID")
    acceptance = require_mapping(packet.get("acceptance_contract"), "HANDOFF_ACCEPTANCE_INVALID")
    require_fields(acceptance, [str(x) for x in as_list(acceptance_spec.get("required"))], "HANDOFF_ACCEPTANCE_REQUIRED_FIELD_MISSING", path="acceptance_contract")
    material_dimensions = require_list(acceptance.get("material_dimensions"), "HANDOFF_MATERIAL_DIMENSIONS_INVALID")
    if not material_dimensions:
        raise ProductionIntelligenceError("HANDOFF_MATERIAL_DIMENSIONS_MISSING")
    unknown_dimensions = [str(x) for x in material_dimensions if str(x) not in dimensions]
    if unknown_dimensions:
        raise ProductionIntelligenceError("HANDOFF_MATERIAL_DIMENSION_UNKNOWN", details={"dimensions": unknown_dimensions})
    measurement_spec = require_mapping(acceptance_spec.get("measurement_plan"), "HANDOFF_SCHEMA_MEASUREMENT_PLAN_INVALID")
    measurement = require_mapping(acceptance.get("measurement_plan"), "HANDOFF_MEASUREMENT_PLAN_INVALID")
    require_fields(measurement, [str(x) for x in as_list(measurement_spec.get("required"))], "HANDOFF_MEASUREMENT_REQUIRED_FIELD_MISSING", path="acceptance_contract.measurement_plan")
    if str(measurement.get("inspection_mode") or "") not in set(str(x) for x in as_list(measurement_spec.get("inspection_mode_enum"))):
        raise ProductionIntelligenceError("HANDOFF_INSPECTION_MODE_INVALID")
    pass_logic = require_mapping(acceptance.get("pass_logic"), "HANDOFF_PASS_LOGIC_INVALID")
    if pass_logic.get("global_score_overrides_material_failure") is True:
        raise ProductionIntelligenceError("GLOBAL_SCORE_HIDES_MATERIAL_FAILURE")

    unknowns = require_list(packet.get("unresolved_unknowns"), "HANDOFF_UNRESOLVED_UNKNOWNS_INVALID")
    material_unknown_ids: list[str] = []
    for index, unknown in enumerate(unknowns):
        unknown = require_mapping(unknown, "K4_UNKNOWN_INVALID", path=f"unresolved_unknowns[{index}]")
        for key in ("unknown_id_or_local_id", "question", "epistemic_zone", "materiality", "safe_default", "next_information_action"):
            if not nonempty_text(unknown.get(key)):
                raise ProductionIntelligenceError("K4_UNKNOWN_REQUIRED_FIELD_MISSING", details={"index": index, "field": key})
        if unknown.get("epistemic_zone") != "K4_FRONTIER_OR_OPAQUE":
            raise ProductionIntelligenceError("K4_UNKNOWN_WRONG_ZONE")
        if str(unknown.get("materiality")) in {"HIGH", "MATERIAL", "HARD"}:
            material_unknown_ids.append(str(unknown.get("unknown_id_or_local_id")))

    experiment = packet.get("experiment_contract")
    if experiment is not None:
        experiment = require_mapping(experiment, "HANDOFF_EXPERIMENT_INVALID")
        factors = as_list(experiment.get("factors"))
        if len(factors) > 1 and not experiment.get("factor_ledger"):
            raise ProductionIntelligenceError("MULTIFACTOR_EXPERIMENT_WITHOUT_LEDGER")
        if experiment.get("proxy_pass_equals_final_pass") is True:
            raise ProductionIntelligenceError("PROXY_FINAL_CONFUSION")

    next_spec = require_mapping(packet_spec.get("next_handoff"), "HANDOFF_SCHEMA_NEXT_INVALID")
    next_handoff = require_mapping(packet.get("next_handoff"), "HANDOFF_NEXT_HANDOFF_INVALID")
    require_fields(next_handoff, [str(x) for x in as_list(next_spec.get("required"))], "HANDOFF_NEXT_REQUIRED_FIELD_MISSING", path="next_handoff")
    next_owner = str(next_handoff.get("next_owner") or "").strip()
    if next_owner not in participants:
        raise ProductionIntelligenceError("HANDOFF_NEXT_OWNER_UNKNOWN", details={"next_owner": next_owner})
    next_task_class = str(next_handoff.get("next_task_class") or "").strip()
    if next_task_class not in set(str(x) for x in as_list(task_spec.get("task_class_enum"))):
        raise ProductionIntelligenceError("HANDOFF_NEXT_TASK_CLASS_INVALID", details={"next_task_class": next_task_class})
    carried_hard = set(str(x).strip() for x in require_list(next_handoff.get("live_hard_invariants"), "HANDOFF_NEXT_HARD_INVARIANTS_INVALID") if str(x).strip())
    missing_hard = sorted(set(hard_invariants) - carried_hard)
    if missing_hard:
        raise ProductionIntelligenceError("HANDOFF_HARD_INVARIANT_DROPPED", details={"missing": missing_hard})
    carried_unknowns = set(str(x).strip() for x in require_list(next_handoff.get("material_unknown_ids"), "HANDOFF_NEXT_MATERIAL_UNKNOWNS_INVALID") if str(x).strip())
    missing_unknowns = sorted(set(material_unknown_ids) - carried_unknowns)
    if missing_unknowns:
        raise ProductionIntelligenceError("HANDOFF_MATERIAL_UNKNOWN_DROPPED", details={"missing": missing_unknowns})

    high_impact_classes = [str(x) for x in as_list(next_handoff.get("high_impact_change_classes")) if str(x)]
    if high_impact_classes:
        allowed_high_impact = set(str(x) for x in as_list(next_spec.get("high_impact_change_class_enum")))
        invalid = sorted(set(high_impact_classes) - allowed_high_impact)
        if invalid:
            raise ProductionIntelligenceError("HANDOFF_HIGH_IMPACT_CLASS_INVALID", details={"classes": invalid})
        if next_handoff.get("approval_required") is not True or not nonempty_text(next_handoff.get("approval_gate_ref")):
            raise ProductionIntelligenceError("HIGH_IMPACT_GATE_BYPASS", details={"classes": high_impact_classes})

    return True


def validate_handoff_transition(
    upstream_packet: Mapping[str, Any],
    downstream_packet: Mapping[str, Any],
    *,
    project_root: str | Path,
    expected_work_item_id: str | None = None,
) -> bool:
    validate_handoff_packet(upstream_packet, project_root=project_root, expected_work_item_id=expected_work_item_id)
    validate_handoff_packet(downstream_packet, project_root=project_root, expected_work_item_id=expected_work_item_id)
    upstream_next = require_mapping(upstream_packet.get("next_handoff"), "HANDOFF_NEXT_HANDOFF_INVALID")
    downstream_participant = require_mapping(downstream_packet.get("participant"), "HANDOFF_PARTICIPANT_INVALID")
    downstream_task = require_mapping(downstream_packet.get("task"), "HANDOFF_TASK_INVALID")
    upstream_context = require_mapping(upstream_packet.get("context"), "HANDOFF_CONTEXT_INVALID")
    downstream_context = require_mapping(downstream_packet.get("context"), "HANDOFF_CONTEXT_INVALID")
    if str(upstream_next.get("next_owner")) != str(downstream_participant.get("owner_role")):
        raise ProductionIntelligenceError("HANDOFF_TRANSITION_OWNER_MISMATCH")
    if str(upstream_next.get("next_task_class")) != str(downstream_task.get("task_class")):
        raise ProductionIntelligenceError("HANDOFF_TRANSITION_TASK_CLASS_MISMATCH")
    if str(upstream_context.get("work_item_id_when_required") or "") != str(downstream_context.get("work_item_id_when_required") or ""):
        raise ProductionIntelligenceError("HANDOFF_TRANSITION_WORK_ITEM_MISMATCH")
    upstream_hard = set(str(x) for x in as_list(upstream_next.get("live_hard_invariants")))
    downstream_hard = set(str(x) for x in as_list(require_mapping(downstream_packet.get("creative_contract"), "HANDOFF_CREATIVE_CONTRACT_INVALID").get("hard_invariants")))
    missing_hard = sorted(upstream_hard - downstream_hard)
    if missing_hard:
        raise ProductionIntelligenceError("HANDOFF_TRANSITION_HARD_INVARIANT_DROPPED", details={"missing": missing_hard})
    upstream_unknown_ids = set(str(x) for x in as_list(upstream_next.get("material_unknown_ids")))
    downstream_unknown_ids = {
        str(item.get("unknown_id_or_local_id"))
        for item in as_list(downstream_packet.get("unresolved_unknowns"))
        if isinstance(item, Mapping)
    }
    missing_unknowns = sorted(upstream_unknown_ids - downstream_unknown_ids)
    if missing_unknowns:
        raise ProductionIntelligenceError("HANDOFF_TRANSITION_MATERIAL_UNKNOWN_DROPPED", details={"missing": missing_unknowns})
    return True


def validate_workflow_coverage(project_root: str | Path) -> None:
    root = Path(project_root)
    required_picg_paths = (
        "10_运行时/production_intelligence_capability_graph.yaml",
        "10_运行时/production_intelligence_epistemic_cycle_policy.yaml",
        "10_运行时/production_handoff_packet_schema.yaml",
        "10_运行时/production_intelligence_signal_envelope_schema.yaml",
        "10_运行时/production_intelligence_research_intake_policy.yaml",
        "11_验收/production_intelligence_capability_graph_regression_cases.yaml",
        "tools/production_intelligence/**",
    )
    for workflow_path in (PICG_WORKFLOW_PATH, LEARNING_WORKFLOW_PATH):
        try:
            text = (root / workflow_path).read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ProductionIntelligenceError("PICG_WORKFLOW_MISSING", details={"path": str(workflow_path)}) from exc
        missing = [path for path in required_picg_paths if path not in text]
        if missing:
            raise ProductionIntelligenceError(
                "PICG_WORKFLOW_COVERAGE_INCOMPLETE",
                details={"workflow": str(workflow_path), "missing": missing},
            )
