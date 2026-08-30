"""Mechanical Expected-vs-Observed evaluation for SOAC reverse observations.

This module compares declared CinematicIntent execution expectations with
manual or AI-assisted observations. It does not inspect media, define film
method, score aesthetics, rewrite prompts, or promote learning maturity.
Canonical observed-field, failure-category, and controlled-eval requirements
come from ``10_运行时/screen_observable_audible_ir_schema.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


class ExpectedObservedEvalError(ValueError):
    """Fail-closed structural/provenance error for reverse evaluation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ObservationProvenance:
    evidence_source: str
    inspection_mode: str
    temporal_coverage: dict[str, Any]
    confidence: str
    media_refs: tuple[str, ...]
    claimed_frame_by_frame_review: bool


_ALLOWED_ROOT_KEYS = {
    "eval_id",
    "expectations",
    "reverse_observation",
    "context",
    "controlled_eval",
}
_ALLOWED_REVERSE_KEYS = {"fields", "expectation_observations", "provenance"}
_ALLOWED_PROVENANCE_KEYS = {
    "evidence_source",
    "inspection_mode",
    "temporal_coverage",
    "confidence",
    "media_refs",
    "claimed_frame_by_frame_review",
}
_ALLOWED_CONTEXT_KEYS = {"model", "model_version", "generation_id", "work_item_id"}
_ALLOWED_CONTROL_KEYS = {"target_variable", "confounds", "non_target_controls_verified", "control_provenance"}
_ALLOWED_CONTROL_PROVENANCE_KEYS = {
    "source",
    "verified_equal",
    "not_applicable",
    "not_applicable_reasons",
    "evidence_refs",
}
_ALLOWED_OBSERVATION_KEYS = {
    "comparison_mode",
    "observed_value",
    "match_state",
    "failure_category",
    "evidence_refs",
    "note",
}
_ALLOWED_COMPARISON_MODES = {"exact_value", "explicit_observation_judgment"}
_ALLOWED_MATCH_STATES = {"MATCH", "CONTRADICTS", "UNKNOWN", "NOT_APPLICABLE"}
_ALLOWED_CONFIDENCE = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
_SAMPLED_INSPECTION_MODES = {
    "fixed_interval_sampling",
    "selected_frames",
    "sparse_sampling",
    "contact_sheet_sampling",
}
_FULL_FRAME_INSPECTION_MODE = "full_decoded_frame_review"

STRUCTURAL_GATE_CODES = {
    "EVAL_INVALID_SHAPE",
    "EVAL_UNKNOWN_FIELD",
    "EVAL_UNKNOWN_OBSERVED_FIELD",
    "EVAL_UNKNOWN_EXPECTATION_FIELD",
    "EVAL_MISSING_PROVENANCE",
    "EVAL_INVALID_FAILURE_CATEGORY",
    "EVAL_FRAME_BY_FRAME_CLAIM_CONFLICT",
    "EVAL_EXPECTATION_PROVENANCE_MISSING",
    "EVAL_CONTROL_PROVENANCE_INVALID",
    "EVAL_CONTROL_REQUIREMENTS_INCOMPLETE",
}


def _load_reverse_schema(project_root: str | Path) -> tuple[dict[str, Any], set[str], set[str], set[str]]:
    path = Path(project_root) / "10_运行时/screen_observable_audible_ir_schema.yaml"
    schema = yaml.safe_load(path.read_text(encoding="utf-8"))
    reverse = schema.get("reverse_compiler") or {}
    observed_fields = {str(item) for item in reverse.get("observed_fields") or []}
    failure_categories = {str(item) for item in reverse.get("failure_categories") or []}
    cinematic_fields = {
        str(item)
        for item in ((schema.get("ir_layers") or {}).get("CinematicIntentIR") or {}).get("fields") or []
    }
    if not observed_fields or not failure_categories or not cinematic_fields:
        raise ExpectedObservedEvalError(
            "EVAL_INVALID_SHAPE",
            "canonical SOAC schema is missing reverse-compiler or CinematicIntent vocabularies",
        )
    return schema, observed_fields, failure_categories, cinematic_fields


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ExpectedObservedEvalError("EVAL_INVALID_SHAPE", f"{field} must be a mapping")
    return dict(value)


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _validate_keys(mapping: Mapping[str, Any], allowed: set[str], *, field: str) -> None:
    unknown = set(mapping) - allowed
    if unknown:
        raise ExpectedObservedEvalError(
            "EVAL_UNKNOWN_FIELD", f"unknown {field} fields: {sorted(unknown)}"
        )


def _string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ExpectedObservedEvalError(
            "EVAL_CONTROL_PROVENANCE_INVALID", f"{field} must be a list of non-empty strings"
        )
    return [item.strip() for item in value]


def _canonical_control_requirements(schema: Mapping[str, Any]) -> list[str]:
    requirements = [
        str(item).strip()
        for item in ((schema.get("validation") or {}).get("controlled_eval_requirements") or [])
        if str(item).strip()
    ]
    if not requirements:
        raise ExpectedObservedEvalError(
            "EVAL_INVALID_SHAPE", "canonical SOAC schema has no controlled_eval_requirements"
        )
    return requirements


def _validate_control_provenance(
    raw: Any,
    *,
    canonical_requirements: list[str],
    target_variable: str,
    require_complete: bool,
) -> dict[str, Any] | None:
    if raw is None:
        if require_complete:
            raise ExpectedObservedEvalError(
                "EVAL_MISSING_PROVENANCE", "verified non-target controls require control_provenance"
            )
        return None

    provenance = _mapping(raw, field="controlled_eval.control_provenance")
    _validate_keys(provenance, _ALLOWED_CONTROL_PROVENANCE_KEYS, field="control_provenance")
    source = str(provenance.get("source") or "").strip()
    if not source:
        raise ExpectedObservedEvalError(
            "EVAL_MISSING_PROVENANCE", "control_provenance.source is required"
        )

    verified_equal = _string_list(provenance.get("verified_equal"), field="control_provenance.verified_equal")
    not_applicable = _string_list(provenance.get("not_applicable"), field="control_provenance.not_applicable")
    evidence_refs = _string_list(provenance.get("evidence_refs"), field="control_provenance.evidence_refs")
    reasons = _mapping(provenance.get("not_applicable_reasons"), field="control_provenance.not_applicable_reasons")

    canonical = set(canonical_requirements)
    declared = set(verified_equal) | set(not_applicable)
    unknown = declared - canonical
    if unknown:
        raise ExpectedObservedEvalError(
            "EVAL_CONTROL_PROVENANCE_INVALID",
            f"control provenance references non-canonical requirements: {sorted(unknown)}",
        )
    overlap = set(verified_equal) & set(not_applicable)
    if overlap:
        raise ExpectedObservedEvalError(
            "EVAL_CONTROL_PROVENANCE_INVALID",
            f"control requirements cannot be both verified and not applicable: {sorted(overlap)}",
        )
    unknown_reason_keys = set(reasons) - set(not_applicable)
    if unknown_reason_keys:
        raise ExpectedObservedEvalError(
            "EVAL_CONTROL_PROVENANCE_INVALID",
            f"not_applicable_reasons reference undeclared requirements: {sorted(unknown_reason_keys)}",
        )
    missing_reasons = [
        requirement
        for requirement in not_applicable
        if not _nonempty(reasons.get(requirement))
    ]
    if missing_reasons:
        raise ExpectedObservedEvalError(
            "EVAL_CONTROL_PROVENANCE_INVALID",
            f"not-applicable requirements require explicit reasons: {missing_reasons}",
        )
    if not_applicable and not target_variable:
        raise ExpectedObservedEvalError(
            "EVAL_CONTROL_PROVENANCE_INVALID",
            "not-applicable control requirements require an explicit target_variable",
        )

    if require_complete:
        if not target_variable:
            raise ExpectedObservedEvalError(
                "EVAL_CONTROL_PROVENANCE_INVALID",
                "non_target_controls_verified=true requires target_variable",
            )
        if not evidence_refs:
            raise ExpectedObservedEvalError(
                "EVAL_MISSING_PROVENANCE",
                "verified non-target controls require control_provenance.evidence_refs",
            )
        missing = canonical - declared
        if missing:
            raise ExpectedObservedEvalError(
                "EVAL_CONTROL_REQUIREMENTS_INCOMPLETE",
                f"CLEAN control claim does not cover canonical SOAC requirements: {sorted(missing)}",
            )

    return {
        "source": source,
        "verified_equal": verified_equal,
        "not_applicable": not_applicable,
        "not_applicable_reasons": reasons,
        "evidence_refs": evidence_refs,
        "canonical_requirements_covered": sorted(declared),
        "complete_against_canonical": declared == canonical,
    }


def _validate_expectations(
    raw: Any, *, cinematic_fields: set[str]
) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise ExpectedObservedEvalError(
            "EVAL_INVALID_SHAPE", "expectations must be a non-empty list"
        )
    expectations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ExpectedObservedEvalError(
                "EVAL_INVALID_SHAPE", f"expectations[{index}] must be a mapping"
            )
        item = dict(item)
        allowed = {"field", "declared_value", "provenance"}
        unknown = set(item) - allowed
        if unknown:
            raise ExpectedObservedEvalError(
                "EVAL_UNKNOWN_FIELD",
                f"unknown expectations[{index}] fields: {sorted(unknown)}",
            )
        field = str(item.get("field") or "").strip()
        if not field or field not in cinematic_fields:
            raise ExpectedObservedEvalError(
                "EVAL_UNKNOWN_EXPECTATION_FIELD",
                f"expectation field {field!r} is not canonical CinematicIntentIR",
            )
        if field in seen:
            raise ExpectedObservedEvalError(
                "EVAL_INVALID_SHAPE", f"duplicate expectation field {field!r}"
            )
        if "declared_value" not in item:
            raise ExpectedObservedEvalError(
                "EVAL_INVALID_SHAPE", f"expectation {field!r} has no declared_value"
            )
        if not _nonempty(item.get("provenance")):
            raise ExpectedObservedEvalError(
                "EVAL_EXPECTATION_PROVENANCE_MISSING",
                f"expectation {field!r} has no non-empty provenance",
            )
        seen.add(field)
        expectations.append(item)
    return expectations


def _validate_observation_provenance(raw: Any) -> ObservationProvenance:
    provenance = _mapping(raw, field="reverse_observation.provenance")
    _validate_keys(provenance, _ALLOWED_PROVENANCE_KEYS, field="observation provenance")
    required = ("evidence_source", "inspection_mode", "temporal_coverage", "confidence")
    missing = [key for key in required if not _nonempty(provenance.get(key))]
    if missing:
        raise ExpectedObservedEvalError(
            "EVAL_MISSING_PROVENANCE", f"missing observation provenance: {missing}"
        )
    evidence_source = str(provenance["evidence_source"]).strip()
    inspection_mode = str(provenance["inspection_mode"]).strip()
    confidence = str(provenance["confidence"]).strip().upper()
    if confidence not in _ALLOWED_CONFIDENCE:
        raise ExpectedObservedEvalError(
            "EVAL_INVALID_SHAPE", f"invalid confidence {confidence!r}"
        )
    temporal_coverage = _mapping(provenance["temporal_coverage"], field="temporal_coverage")
    if not temporal_coverage:
        raise ExpectedObservedEvalError(
            "EVAL_MISSING_PROVENANCE", "temporal_coverage cannot be empty"
        )
    coverage_type = str(temporal_coverage.get("type") or "").strip()
    if not coverage_type:
        raise ExpectedObservedEvalError(
            "EVAL_MISSING_PROVENANCE", "temporal_coverage.type is required"
        )
    frame_by_frame_coverage_claims = {
        "frame_by_frame",
        "all_frames",
        "full_decoded_frames",
        "full_frame_sequence",
    }
    if inspection_mode in _SAMPLED_INSPECTION_MODES and coverage_type in frame_by_frame_coverage_claims:
        raise ExpectedObservedEvalError(
            "EVAL_FRAME_BY_FRAME_CLAIM_CONFLICT",
            f"sampled inspection mode {inspection_mode!r} cannot use frame-by-frame temporal coverage {coverage_type!r}",
        )
    media_refs_raw = provenance.get("media_refs") or []
    if not isinstance(media_refs_raw, list) or not all(isinstance(item, str) for item in media_refs_raw):
        raise ExpectedObservedEvalError(
            "EVAL_INVALID_SHAPE", "media_refs must be a list of strings"
        )
    claim = provenance.get("claimed_frame_by_frame_review", False)
    if not isinstance(claim, bool):
        raise ExpectedObservedEvalError(
            "EVAL_INVALID_SHAPE", "claimed_frame_by_frame_review must be boolean"
        )
    if claim and inspection_mode in _SAMPLED_INSPECTION_MODES:
        raise ExpectedObservedEvalError(
            "EVAL_FRAME_BY_FRAME_CLAIM_CONFLICT",
            f"sampled inspection mode {inspection_mode!r} cannot claim frame-by-frame review",
        )
    if claim and inspection_mode != _FULL_FRAME_INSPECTION_MODE:
        raise ExpectedObservedEvalError(
            "EVAL_FRAME_BY_FRAME_CLAIM_CONFLICT",
            "frame-by-frame claim requires full_decoded_frame_review inspection mode",
        )
    return ObservationProvenance(
        evidence_source=evidence_source,
        inspection_mode=inspection_mode,
        temporal_coverage=temporal_coverage,
        confidence=confidence,
        media_refs=tuple(media_refs_raw),
        claimed_frame_by_frame_review=claim,
    )


def _derive_outcome(observation: Mapping[str, Any], expected_value: Any) -> tuple[str, Any]:
    mode = str(observation.get("comparison_mode") or "explicit_observation_judgment")
    if mode not in _ALLOWED_COMPARISON_MODES:
        raise ExpectedObservedEvalError(
            "EVAL_INVALID_SHAPE", f"invalid comparison_mode {mode!r}"
        )
    if mode == "exact_value":
        if "observed_value" not in observation:
            return "UNKNOWN", None
        observed_value = observation.get("observed_value")
        return ("PASS" if observed_value == expected_value else "FAIL"), observed_value

    match_state = str(observation.get("match_state") or "UNKNOWN").upper()
    if match_state not in _ALLOWED_MATCH_STATES:
        raise ExpectedObservedEvalError(
            "EVAL_INVALID_SHAPE", f"invalid match_state {match_state!r}"
        )
    if match_state in {"MATCH", "CONTRADICTS"} and not any(
        _nonempty(observation.get(key)) for key in ("observed_value", "evidence_refs", "note")
    ):
        raise ExpectedObservedEvalError(
            "EVAL_MISSING_PROVENANCE",
            f"explicit judgment {match_state} requires observed_value, evidence_refs, or note",
        )
    mapping = {
        "MATCH": "PASS",
        "CONTRADICTS": "FAIL",
        "UNKNOWN": "UNKNOWN",
        "NOT_APPLICABLE": "NOT_APPLICABLE",
    }
    return mapping[match_state], observation.get("observed_value")


def evaluate_expected_vs_observed(
    raw: Mapping[str, Any], *, project_root: str | Path
) -> dict[str, Any]:
    """Validate supplied reverse observations and compare them to declared expectations."""

    if not isinstance(raw, Mapping):
        raise ExpectedObservedEvalError("EVAL_INVALID_SHAPE", "evaluation root must be a mapping")
    raw = dict(raw)
    _validate_keys(raw, _ALLOWED_ROOT_KEYS, field="root")

    schema, observed_vocabulary, failure_vocabulary, cinematic_fields = _load_reverse_schema(project_root)
    canonical_control_requirements = _canonical_control_requirements(schema)
    expectations = _validate_expectations(raw.get("expectations"), cinematic_fields=cinematic_fields)
    expectation_by_field = {item["field"]: item for item in expectations}

    reverse = _mapping(raw.get("reverse_observation"), field="reverse_observation")
    _validate_keys(reverse, _ALLOWED_REVERSE_KEYS, field="reverse_observation")
    provenance = _validate_observation_provenance(reverse.get("provenance"))

    observed_fields = _mapping(reverse.get("fields"), field="reverse_observation.fields")
    unknown_observed = set(observed_fields) - observed_vocabulary
    if unknown_observed:
        raise ExpectedObservedEvalError(
            "EVAL_UNKNOWN_OBSERVED_FIELD",
            f"unknown reverse observation fields: {sorted(unknown_observed)}",
        )

    expectation_observations = _mapping(
        reverse.get("expectation_observations"), field="reverse_observation.expectation_observations"
    )
    unknown_expectations = set(expectation_observations) - set(expectation_by_field)
    if unknown_expectations:
        raise ExpectedObservedEvalError(
            "EVAL_UNKNOWN_EXPECTATION_FIELD",
            f"observations reference undeclared expectations: {sorted(unknown_expectations)}",
        )

    context = _mapping(raw.get("context"), field="context")
    _validate_keys(context, _ALLOWED_CONTEXT_KEYS, field="context")
    controlled = _mapping(raw.get("controlled_eval"), field="controlled_eval")
    _validate_keys(controlled, _ALLOWED_CONTROL_KEYS, field="controlled_eval")
    confounds = controlled.get("confounds") or []
    if not isinstance(confounds, list) or not all(isinstance(item, str) for item in confounds):
        raise ExpectedObservedEvalError(
            "EVAL_INVALID_SHAPE", "controlled_eval.confounds must be a list of strings"
        )
    target_variable = str(controlled.get("target_variable") or "").strip()
    controls_verified = controlled.get("non_target_controls_verified", False)
    if not isinstance(controls_verified, bool):
        raise ExpectedObservedEvalError(
            "EVAL_INVALID_SHAPE",
            "controlled_eval.non_target_controls_verified must be boolean",
        )
    control_provenance = _validate_control_provenance(
        controlled.get("control_provenance"),
        canonical_requirements=canonical_control_requirements,
        target_variable=target_variable,
        require_complete=controls_verified,
    )
    if confounds:
        control_status = "CONFOUNDED"
    elif target_variable and controls_verified:
        control_status = "CLEAN"
    elif target_variable:
        control_status = "UNVERIFIED_CONTROL"
    else:
        control_status = "UNCONTROLLED"

    results: list[dict[str, Any]] = []
    for expectation in expectations:
        field = expectation["field"]
        observation_raw = expectation_observations.get(field)
        if observation_raw is None:
            results.append(
                {
                    "field": field,
                    "outcome": "UNKNOWN",
                    "expected_value": expectation["declared_value"],
                    "observed_value": None,
                    "failure_category": None,
                    "expectation_provenance": expectation["provenance"],
                    "evidence_refs": [],
                    "note": "material expectation was not observed",
                }
            )
            continue
        observation = _mapping(observation_raw, field=f"expectation_observations.{field}")
        _validate_keys(observation, _ALLOWED_OBSERVATION_KEYS, field=f"expectation observation {field}")
        outcome, observed_value = _derive_outcome(observation, expectation["declared_value"])
        category = observation.get("failure_category")
        if outcome == "FAIL":
            if not _nonempty(category) or str(category) not in failure_vocabulary:
                raise ExpectedObservedEvalError(
                    "EVAL_INVALID_FAILURE_CATEGORY",
                    f"failed expectation {field!r} requires a canonical failure_category",
                )
            category = str(category)
        elif _nonempty(category):
            raise ExpectedObservedEvalError(
                "EVAL_INVALID_FAILURE_CATEGORY",
                f"failure_category is only valid for FAIL outcomes, got {outcome} for {field!r}",
            )
        else:
            category = None
        evidence_refs = observation.get("evidence_refs") or []
        if not isinstance(evidence_refs, list) or not all(isinstance(item, str) for item in evidence_refs):
            raise ExpectedObservedEvalError(
                "EVAL_INVALID_SHAPE", f"evidence_refs for {field!r} must be a list of strings"
            )
        results.append(
            {
                "field": field,
                "outcome": outcome,
                "expected_value": expectation["declared_value"],
                "observed_value": observed_value,
                "failure_category": category,
                "expectation_provenance": expectation["provenance"],
                "evidence_refs": evidence_refs,
                "note": observation.get("note"),
            }
        )

    failed = [item for item in results if item["outcome"] == "FAIL"]
    unknown = [item for item in results if item["outcome"] == "UNKNOWN"]
    if failed:
        status = "FAIL"
    elif unknown:
        status = "INCOMPLETE"
    else:
        status = "PASS"

    repair_items = [
        {
            "field": item["field"],
            "outcome": item["outcome"],
            "expected_value": item["expected_value"],
            "observed_value": item["observed_value"],
            "failure_category": item["failure_category"],
            "evidence_refs": item["evidence_refs"],
        }
        for item in results
        if item["outcome"] in {"FAIL", "UNKNOWN"}
    ]

    provenance_payload = {
        "evidence_source": provenance.evidence_source,
        "inspection_mode": provenance.inspection_mode,
        "temporal_coverage": provenance.temporal_coverage,
        "confidence": provenance.confidence,
        "media_refs": list(provenance.media_refs),
        "claimed_frame_by_frame_review": provenance.claimed_frame_by_frame_review,
        "sampled_temporal_evidence": provenance.inspection_mode in _SAMPLED_INSPECTION_MODES,
    }

    return {
        "status": status,
        "eval_id": str(raw.get("eval_id") or "UNSPECIFIED_EXPECTED_OBSERVED_EVAL"),
        "comparison_authority": schema["reverse_compiler"]["comparison"],
        "reverse_observation_boundary": schema["reverse_compiler"]["boundary"],
        "results": results,
        "observation_fields": observed_fields,
        "observation_provenance": provenance_payload,
        "control_status": control_status,
        "controlled_eval": {
            "target_variable": target_variable or None,
            "confounds": confounds,
            "non_target_controls_verified": controls_verified,
            "control_provenance": control_provenance,
            "canonical_control_requirements": canonical_control_requirements,
        },
        "targeted_repair_handoff": {
            "items": repair_items,
            "prompt_mutation_authorized": False,
            "requires_director_or_targeted_repair_step": bool(repair_items),
        },
        "learning_evidence_handoff": {
            "eval_id": str(raw.get("eval_id") or "UNSPECIFIED_EXPECTED_OBSERVED_EVAL"),
            "work_item_id": context.get("work_item_id"),
            "model": context.get("model"),
            "model_version": context.get("model_version"),
            "control_status": control_status,
            "observation_provenance": provenance_payload,
            "field_results": results,
            "maturity_effect": "none",
            "promotion_authorized": False,
            "writeback_authorized": False,
        },
        "automatic_media_grading_performed": False,
        "aesthetic_score": None,
    }
