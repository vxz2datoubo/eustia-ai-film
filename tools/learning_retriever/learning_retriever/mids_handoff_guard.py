"""Final authority guard for a MIDS DiscoverySpecCandidate.

The discovery core may hold caller/orchestrator context projections while a shadow
session is being explored. This module is the only candidate handoff surface that
may be used before the existing Director Feature Compiler. It re-checks user
provenance and deliberately *downgrades* work-item data to a non-authoritative
projection that downstream orchestration must revalidate with the canonical
Active Work Item gate.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from .mids_discovery import MIDSDiscoveryError, compile_spec_candidate, validate_session

_ALLOWED_EXISTING_BINDING_KEYS = {"mode", "work_item_id", "trust_basis"}
_FORBIDDEN_AUTHORITY_ASSERTION_KEYS = {
    "validated",
    "verified",
    "freshness_verified",
    "canonical_authority_verified",
    "canonical_verified",
    "trusted",
    "authority_granted",
    "receipt",
    "token",
    "signature",
    "attestation",
}


def _fail(code: str, **details: Any) -> MIDSDiscoveryError:
    return MIDSDiscoveryError(code, details=details or None)


def _has_user_source(items: Any) -> bool:
    if not isinstance(items, list):
        return False
    return any(
        isinstance(item, Mapping)
        and str(item.get("source") or "").strip().upper() == "USER"
        for item in items
    )


def validate_confirmed_decision_authority(session: Mapping[str, Any]) -> None:
    validate_session(session)
    rejected = {
        str(item.get("alternative_id") or "").strip()
        for item in session.get("rejected_alternatives", [])
        if isinstance(item, Mapping) and str(item.get("alternative_id") or "").strip()
    }
    for record in session.get("confirmed_decisions", []):
        if not isinstance(record, Mapping):
            raise _fail("MIDS_CONFIRMED_DECISION_INVALID")
        decision_id = str(record.get("decision_id") or "").strip()
        epistemic = str(record.get("epistemic_class") or "").strip()
        status = str(record.get("status") or "").strip()
        if decision_id in rejected:
            raise _fail("MIDS_REJECTED_ALTERNATIVE_LEAKED", decision_id=decision_id)
        if epistemic == "USER_EXPLICIT_CONFIRMED":
            if status != "CONFIRMED" or not _has_user_source(record.get("provenance")):
                raise _fail("MIDS_USER_EXPLICIT_PROVENANCE_MUST_BE_USER", decision_id=decision_id)
        elif epistemic == "USER_TACIT_CANDIDATE":
            if status != "CONFIRMED" or not _has_user_source(record.get("user_confirmation_provenance")):
                raise _fail("MIDS_TACIT_CONFIRMATION_MUST_BE_USER", decision_id=decision_id)
        elif epistemic == "AI_DISCOVERABLE_OPTION":
            if status != "ACCEPTED" or not _has_user_source(record.get("user_acceptance_provenance")):
                raise _fail("MIDS_AI_PROPOSAL_ACCEPTANCE_MUST_BE_USER", decision_id=decision_id)
        else:
            raise _fail(
                "MIDS_CONFIRMED_DECISION_EPISTEMIC_CLASS_FORBIDDEN",
                decision_id=decision_id,
                epistemic_class=epistemic,
            )


def validate_work_item_projection_boundary(session: Mapping[str, Any]) -> dict[str, Any]:
    validate_session(session)
    raw = session.get("work_item_binding")
    if not isinstance(raw, Mapping):
        raise _fail("MIDS_WORK_ITEM_BINDING_MODE_INVALID")
    binding = dict(raw)
    mode = str(binding.get("mode") or "").strip()
    asserted = sorted(_FORBIDDEN_AUTHORITY_ASSERTION_KEYS.intersection(binding))
    if asserted:
        raise _fail("MIDS_WORK_ITEM_AUTHORITY_ASSERTION_FORBIDDEN", keys=asserted)
    if mode == "TRUSTED_EXISTING":
        extra = sorted(set(binding) - _ALLOWED_EXISTING_BINDING_KEYS)
        if extra:
            raise _fail("MIDS_WORK_ITEM_PROJECTION_FIELD_FORBIDDEN", keys=extra)
        work_item_id = str(binding.get("work_item_id") or "").strip()
        if not work_item_id:
            raise _fail("MIDS_WORK_ITEM_BINDING_MODE_INVALID")
        return {
            "mode": "EXISTING_WORK_ITEM_CONTEXT_PROJECTION",
            "work_item_id": work_item_id,
            "upstream_basis_label": str(binding.get("trust_basis") or "").strip(),
            "authority_granted_by_mids": False,
            "downstream_active_work_item_revalidation_required": True,
        }
    if mode == "NEW_UNBOUND":
        if str(binding.get("work_item_id") or "").strip():
            raise _fail("MIDS_UNBOUND_WORK_ITEM_CANNOT_CLAIM_CANONICAL_ID")
        extra = sorted(set(binding) - {"mode", "work_item_id"})
        if extra:
            raise _fail("MIDS_WORK_ITEM_PROJECTION_FIELD_FORBIDDEN", keys=extra)
        return {
            "mode": "NEW_UNBOUND_DISCOVERY_TARGET",
            "work_item_id": None,
            "authority_granted_by_mids": False,
            "downstream_active_work_item_revalidation_required": False,
        }
    raise _fail("MIDS_WORK_ITEM_BINDING_MODE_INVALID", mode=mode)


def compile_guarded_spec_candidate(session: Mapping[str, Any]) -> dict[str, Any]:
    """Compile only after provenance and work-item authority boundaries pass."""
    validate_confirmed_decision_authority(session)
    projection = validate_work_item_projection_boundary(session)
    spec = copy.deepcopy(compile_spec_candidate(session))
    spec["work_item_binding"] = projection
    boundary = dict(spec.get("authority_boundary") or {})
    boundary.update(
        {
            "handoff_guard_passed": True,
            "work_item_projection_is_not_authority": True,
            "downstream_must_use_existing_active_work_item_gate": projection[
                "downstream_active_work_item_revalidation_required"
            ],
            "mids_receipt_cannot_replace_active_work_item_receipt": True,
        }
    )
    spec["authority_boundary"] = boundary
    spec["handoff_guard_receipt"] = {
        "schema": "MIDS_HANDOFF_GUARD/v1",
        "status": "PASS",
        "confirmed_decision_authority_checked": True,
        "work_item_context_downgraded_to_projection": True,
        "canonical_authority_granted": False,
        "feature_compiler_authority_granted": False,
        "hard_route_authority_granted": False,
    }
    return spec
