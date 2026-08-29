"""Executable contract runtime for canonical CinematicIntentIR.

This module is deliberately mechanical.  It does not define directing method,
choose shots, invent story facts, or create a second visual authority.  Method
remains in ``01_AI电影系统/AI电影系统.md`` and field/static-check authority
remains in ``10_运行时/screen_observable_audible_ir_schema.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

import yaml


class CinematicIntentContractError(ValueError):
    """Fail-closed structural/authority error before aesthetic evaluation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    field: str | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "field": self.field,
            "message": self.message,
        }


@dataclass(frozen=True)
class CinematicIntentContract:
    contract_id: str
    intent: dict[str, Any]
    provenance: dict[str, Any]
    context: dict[str, Any]



_TOP_LEVEL_KEYS = {"contract_id", "intent", "provenance", "context"}
_FORBIDDEN_AUTHORITY_KEYS = {
    "blocking",
    "blocking_ir",
    "BlockingIR",
    "blocking_override",
    "map",
    "canonical_map",
    "map_override",
    "world_state",
    "WorldStateIR",
    "canonical_facts",
    "story_override",
    "character_override",
    "asset_override",
    "continuity_override",
    "locked_contracts",
}
_CONTEXT_KEYS = {
    "material_fields",
    "material_attention_reveal",
    "reference_decoupling_applied",
    "model",
    "model_version",
}
_CONTEXT_BOOLEAN_KEYS = {"material_attention_reveal", "reference_decoupling_applied"}
_CAMERA_SENSITIVE_CAPTURE_KEYS = {"camera_physical_position", "lens_intent"}

_NESTED_FIELD_MAP = {
    "relation_pressure": "relation_pressure_fields",
    "attention_flow": "attention_flow_fields",
    "composition": "composition_fields",
    "color_intent": "color_intent_fields",
    "capture_intent": "capture_intent_fields",
    "visual_density": "visual_density_fields",
    "reference_signal_roles": "reference_signal_role_fields",
    "anti_template_signature": "anti_template_fields",
    "attention_handoff": "attention_handoff_fields",
}

# These are structural runtime gates, not additions to the canonical film-method
# static-check vocabulary.
STRUCTURAL_GATE_CODES = {
    "CONTRACT_UNKNOWN_FIELD",
    "CONTRACT_UNKNOWN_NESTED_FIELD",
    "CINEMATIC_INTENT_AUTHORITY_VIOLATION",
    "MISSING_PROVENANCE",
    "INVALID_MATERIAL_FIELD",
    "INVALID_CONTRACT_SHAPE",
    "MISSING_CANONICAL_UPSTREAM_BINDING",
}


def _load_schema(project_root: str | Path) -> dict[str, Any]:
    path = Path(project_root) / "10_运行时/screen_observable_audible_ir_schema.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return not value
    return False


def _is_enabled_option(value: Any) -> bool:
    """Treat an explicit false option as disabled rather than materially declared."""

    if value is False:
        return False
    return not _is_empty(value)


def _as_mapping(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise CinematicIntentContractError(
            "INVALID_CONTRACT_SHAPE", f"{field} must be a mapping"
        )
    return dict(value)


def _schema_contract(schema: Mapping[str, Any]) -> tuple[set[str], dict[str, set[str]]]:
    try:
        layer = schema["ir_layers"]["CinematicIntentIR"]
    except (KeyError, TypeError) as exc:
        raise CinematicIntentContractError(
            "INVALID_CONTRACT_SHAPE", "canonical schema has no CinematicIntentIR"
        ) from exc
    fields = set(layer.get("fields") or [])
    nested: dict[str, set[str]] = {}
    for intent_field, schema_field in _NESTED_FIELD_MAP.items():
        nested[intent_field] = set(layer.get(schema_field) or [])
    return fields, nested


def validate_cinematic_intent_contract(
    raw: Mapping[str, Any], *, project_root: str | Path
) -> CinematicIntentContract:
    """Validate structure and authority boundaries without inventing missing intent."""

    if not isinstance(raw, Mapping):
        raise CinematicIntentContractError(
            "INVALID_CONTRACT_SHAPE", "contract root must be a mapping"
        )

    raw_keys = set(raw)
    forbidden = raw_keys & _FORBIDDEN_AUTHORITY_KEYS
    if forbidden:
        raise CinematicIntentContractError(
            "CINEMATIC_INTENT_AUTHORITY_VIOLATION",
            f"CinematicIntent cannot mutate upstream authority keys: {sorted(forbidden)}",
        )
    unknown = raw_keys - _TOP_LEVEL_KEYS
    if unknown:
        raise CinematicIntentContractError(
            "CONTRACT_UNKNOWN_FIELD", f"unknown contract fields: {sorted(unknown)}"
        )

    schema = _load_schema(project_root)
    allowed_intent_fields, nested_fields = _schema_contract(schema)
    intent = _as_mapping(raw.get("intent"), field="intent")

    authority_attempt = set(intent) & _FORBIDDEN_AUTHORITY_KEYS
    if authority_attempt:
        raise CinematicIntentContractError(
            "CINEMATIC_INTENT_AUTHORITY_VIOLATION",
            f"intent cannot carry upstream authority mutations: {sorted(authority_attempt)}",
        )
    unknown_intent = set(intent) - allowed_intent_fields
    if unknown_intent:
        raise CinematicIntentContractError(
            "CONTRACT_UNKNOWN_FIELD", f"unknown CinematicIntentIR fields: {sorted(unknown_intent)}"
        )

    for field, allowed_nested in nested_fields.items():
        if field not in intent or _is_empty(intent[field]):
            continue
        value = intent[field]
        if not isinstance(value, Mapping):
            raise CinematicIntentContractError(
                "INVALID_CONTRACT_SHAPE", f"intent.{field} must be a mapping"
            )
        unknown_nested = set(value) - allowed_nested
        if unknown_nested:
            raise CinematicIntentContractError(
                "CONTRACT_UNKNOWN_NESTED_FIELD",
                f"unknown intent.{field} fields: {sorted(unknown_nested)}",
            )

    for scalar_field in ("unresolved_state", "viewer_position"):
        if scalar_field in intent and not _is_empty(intent[scalar_field]) and not isinstance(intent[scalar_field], str):
            raise CinematicIntentContractError(
                "INVALID_CONTRACT_SHAPE", f"intent.{scalar_field} must be a string"
            )

    provenance = _as_mapping(raw.get("provenance"), field="provenance")
    unknown_provenance = set(provenance) - allowed_intent_fields
    if unknown_provenance:
        raise CinematicIntentContractError(
            "CONTRACT_UNKNOWN_FIELD",
            f"provenance references unknown intent fields: {sorted(unknown_provenance)}",
        )

    context = _as_mapping(raw.get("context"), field="context")
    unknown_context = set(context) - _CONTEXT_KEYS
    if unknown_context:
        raise CinematicIntentContractError(
            "CONTRACT_UNKNOWN_FIELD", f"unknown context fields: {sorted(unknown_context)}"
        )
    for boolean_field in _CONTEXT_BOOLEAN_KEYS:
        if boolean_field in context and not isinstance(context[boolean_field], bool):
            raise CinematicIntentContractError(
                "INVALID_CONTRACT_SHAPE", f"context.{boolean_field} must be boolean"
            )

    material_fields = context.get("material_fields") or []
    if not isinstance(material_fields, list) or not all(isinstance(item, str) for item in material_fields):
        raise CinematicIntentContractError(
            "INVALID_CONTRACT_SHAPE", "context.material_fields must be a list of field names"
        )
    invalid_material = set(material_fields) - allowed_intent_fields
    if invalid_material:
        raise CinematicIntentContractError(
            "INVALID_MATERIAL_FIELD", f"unknown material fields: {sorted(invalid_material)}"
        )

    for field in material_fields:
        if field in intent and not _is_empty(intent[field]):
            if field not in provenance or _is_empty(provenance[field]):
                raise CinematicIntentContractError(
                    "MISSING_PROVENANCE", f"material field {field!r} has no non-empty provenance"
                )

    contract_id = str(raw.get("contract_id") or "UNSPECIFIED_CINEMATIC_INTENT")
    return CinematicIntentContract(
        contract_id=contract_id,
        intent=intent,
        provenance=provenance,
        context=context,
    )


def _declared_static_checks(schema: Mapping[str, Any]) -> dict[str, str]:
    checks: dict[str, str] = {}
    for severity in ("ERROR", "WARNING", "INFO"):
        for code in schema.get("static_checks", {}).get(severity, []) or []:
            checks[str(code)] = severity
    return checks


def _diag(
    diagnostics: list[Diagnostic],
    declared: Mapping[str, str],
    code: str,
    field: str | None,
    message: str,
) -> None:
    if code not in declared:
        raise CinematicIntentContractError(
            "INVALID_CONTRACT_SHAPE", f"runtime diagnostic {code} is absent from canonical schema"
        )
    diagnostics.append(Diagnostic(code, declared[code], field, message))


def evaluate_cinematic_intent(
    contract: CinematicIntentContract,
    *,
    project_root: str | Path,
) -> list[Diagnostic]:
    """Evaluate only static checks already declared by the canonical SOAC schema."""

    schema = _load_schema(project_root)
    declared = _declared_static_checks(schema)
    intent = contract.intent
    diagnostics: list[Diagnostic] = []

    composition = dict(intent.get("composition") or {})
    if composition and _is_empty(composition.get("camera_reason")):
        _diag(
            diagnostics,
            declared,
            "COMPOSITION_MISSING_DRAMATIC_REASON",
            "composition",
            "material composition is declared without camera_reason",
        )

    attention_flow = dict(intent.get("attention_flow") or {})
    if attention_flow and _is_empty(attention_flow.get("decisive_roi")):
        _diag(
            diagnostics,
            declared,
            "ATTENTION_FLOW_UNRESOLVED",
            "attention_flow",
            "attention flow has no decisive_roi",
        )

    attention_handoff = dict(intent.get("attention_handoff") or {})
    if contract.context.get("material_attention_reveal"):
        required = ("from_roi", "cut_or_transition_event", "to_roi")
        if not attention_handoff or any(_is_empty(attention_handoff.get(key)) for key in required):
            _diag(
                diagnostics,
                declared,
                "CUT_ATTENTION_HANDOFF_RISK",
                "attention_handoff",
                "material reveal/search cut lacks complete from/cut/to attention handoff",
            )

    color = dict(intent.get("color_intent") or {})
    if color and not _is_empty(color.get("color_thesis")):
        if _is_empty(color.get("physical_color_sources")) and _is_empty(color.get("practical_light_sources")):
            _diag(
                diagnostics,
                declared,
                "COLOR_SOURCE_UNGROUNDED",
                "color_intent",
                "color thesis has no physical color or practical-light source",
            )

    density = dict(intent.get("visual_density") or {})
    detail_budget = str(density.get("detail_budget") or "").strip().lower()
    highlight_budget = str(density.get("highlight_budget") or "").strip().lower()
    overload_tokens = {"max", "all_high", "all_regions_high", "everything_high", "unlimited"}
    if density and (
        detail_budget in overload_tokens
        or highlight_budget in overload_tokens
        or ((_is_empty(density.get("primary_story_clue"))) and detail_budget and highlight_budget)
    ):
        _diag(
            diagnostics,
            declared,
            "VISUAL_DENSITY_OVERLOAD",
            "visual_density",
            "declared density budget lacks hierarchy or saturates noncritical regions",
        )

    reference = dict(intent.get("reference_signal_roles") or {})
    suppress = reference.get("non_authoritative_signals_to_suppress")
    if reference and not _is_empty(suppress) and not contract.context.get("reference_decoupling_applied", False):
        _diag(
            diagnostics,
            declared,
            "REFERENCE_APPEARANCE_LEAK_RISK",
            "reference_signal_roles",
            "non-authoritative reference signals are declared but decoupling is not marked applied",
        )

    anti_template = dict(intent.get("anti_template_signature") or {})
    similarity = anti_template.get("recent_composition_similarity")
    high_similarity = similarity is True or str(similarity).strip().lower() in {"high", "very_high", "same"}
    if high_similarity and _is_empty(anti_template.get("reuse_justification")):
        _diag(
            diagnostics,
            declared,
            "TEMPLATE_COMPOSITION_REPETITION",
            "anti_template_signature",
            "high recent composition similarity has no reuse justification",
        )

    capture = dict(intent.get("capture_intent") or {})
    substrate = capture.get("substrate_optional")
    if capture and _is_enabled_option(substrate) and _is_empty(capture.get("substrate_story_reason")):
        _diag(
            diagnostics,
            declared,
            "CAPTURE_SUBSTRATE_UNMOTIVATED",
            "capture_intent",
            "capture substrate is declared without a story/perceptual/production reason",
        )


    return diagnostics


def compile_cinematic_intent_contract(
    raw: Mapping[str, Any],
    *,
    project_root: str | Path,
) -> dict[str, Any]:
    """Validate and compile a minimal material overlay.

    Camera position/lens intent remain upstream-owned. This slice has no
    canonical machine-readable ShotPlan/Blocking camera-lock readback, so any
    camera-sensitive proposal fails closed instead of accepting caller-supplied
    authority. Re-opening that surface requires a later canonical readback
    integration, not a token, digest, private Python name, or serialized knob.
    """

    contract = validate_cinematic_intent_contract(raw, project_root=project_root)
    capture = dict(contract.intent.get("capture_intent") or {})
    camera_sensitive = [
        key for key in sorted(_CAMERA_SENSITIVE_CAPTURE_KEYS)
        if not _is_empty(capture.get(key))
    ]
    if camera_sensitive:
        raise CinematicIntentContractError(
            "MISSING_CANONICAL_UPSTREAM_BINDING",
            "camera-sensitive CinematicIntent cannot compile until canonical "
            "machine-readable upstream camera authority is available; refusing "
            f"caller-mintable authority for {camera_sensitive}",
        )

    diagnostics = evaluate_cinematic_intent(
        contract,
        project_root=project_root,
    )
    has_error = any(item.severity == "ERROR" for item in diagnostics)
    has_warning = any(item.severity == "WARNING" for item in diagnostics)

    material_fields = list(contract.context.get("material_fields") or [])
    overlay: dict[str, Any] = {}
    overlay_provenance: dict[str, Any] = {}
    if not has_error:
        for field in material_fields:
            value = contract.intent.get(field)
            if _is_empty(value):
                continue
            overlay[field] = value
            overlay_provenance[field] = contract.provenance[field]

    reverse_expectations = [
        {
            "field": field,
            "declared_value": value,
            "provenance": overlay_provenance[field],
        }
        for field, value in overlay.items()
    ]

    status = "FAIL" if has_error else ("WARN" if has_warning else "PASS")
    return {
        "status": status,
        "contract_id": contract.contract_id,
        "schema_authority": "10_运行时/screen_observable_audible_ir_schema.yaml#CinematicIntentIR",
        "method_authority": "01_AI电影系统/AI电影系统.md#CINEMATIC-VISUAL-GRAMMAR-001",
        "diagnostics": [item.as_dict() for item in diagnostics],
        "execution_overlay": overlay,
        "overlay_provenance": overlay_provenance,
        "reverse_eval_expectations": reverse_expectations,
        "upstream_camera_authority": {
            "status": "CANONICAL_READBACK_REQUIRED_FOR_CAMERA_SENSITIVE_INTENT",
            "caller_supplied_authority_accepted": False,
            "proposal_can_mutate": False,
        },
        "authority_mutation_allowed": False,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Validate/compile canonical CinematicIntentIR contract")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--contract", required=True, help="JSON or YAML downstream proposal file")
    args = parser.parse_args()

    path = Path(args.contract)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        raw = json.loads(text)
    else:
        raw = yaml.safe_load(text)

    try:
        result = compile_cinematic_intent_contract(
            raw,
            project_root=args.project_root,
        )
    except CinematicIntentContractError as exc:
        print(json.dumps({"status": "FAIL", "stage": "contract_gate", "code": exc.code, "error": exc.message}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())