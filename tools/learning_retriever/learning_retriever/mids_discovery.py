"""Public trust-bound facade for the MIDS shadow candidate.

The deterministic implementation lives in :mod:`mids_discovery_core`.  This
facade owns public mutation/state-transition semantics.  It deliberately does
not treat caller-authored RESEARCH/EVIDENCE labels as authority: only an explicit
USER_DECISION can close a material unknown/contradiction inside MIDS.  External
evidence remains a candidate for a future canonical authority adapter.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from .mids_discovery_core import *  # noqa: F401,F403
from . import mids_discovery_core as _core

MIDSDiscoveryError = _core.MIDSDiscoveryError
_TRANSITIONS = "mids_transition_log"
_REVOKED = "revoked_decisions"
_TRANSITION_KEYS = {
    "event_type", "target_kind", "target_id", "from_status", "to_status",
    "basis_type", "basis_ref", "provenance",
}


def _fail(code: str, **details: Any) -> MIDSDiscoveryError:
    return MIDSDiscoveryError(code, details=details or None)


def _user_provenance(value: Any, field: str) -> list[dict[str, str]]:
    provenance = _core._provenance(value, field)
    if not any(str(item.get("source") or "").strip().upper() == "USER" for item in provenance):
        raise _fail("MIDS_USER_PROVENANCE_REQUIRED", field=field)
    return provenance


def _decision_id(record: Mapping[str, Any]) -> str:
    return str(record.get("decision_id") or "").strip()


def _existing_decision_ids(session: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for field in ("confirmed_decisions", "inferred_preferences", "candidate_directions", _REVOKED):
        for raw in session.get(field, []):
            if isinstance(raw, Mapping) and _decision_id(raw):
                result.add(_decision_id(raw))
    return result


def _assert_new_id_available(session: Mapping[str, Any], decision_id: str) -> None:
    normalized = str(decision_id or "").strip()
    if normalized and normalized in _existing_decision_ids(session):
        raise _fail("MIDS_DECISION_ID_COLLISION", decision_id=normalized)


def _append_transition(
    session: dict[str, Any], *, target_kind: str, target_id: str,
    from_status: str, to_status: str, basis_type: str, basis_ref: str,
    provenance: Sequence[Mapping[str, Any]],
) -> None:
    session[_TRANSITIONS].append({
        "event_type": "STATE_TRANSITION",
        "target_kind": target_kind,
        "target_id": str(target_id),
        "from_status": from_status,
        "to_status": to_status,
        "basis_type": basis_type,
        "basis_ref": str(basis_ref),
        "provenance": copy.deepcopy(list(provenance)),
    })


def _matching_transition(
    session: Mapping[str, Any], *, target_kind: str, target_id: str,
    from_status: str, to_status: str, basis_type: str, basis_ref: str,
) -> Mapping[str, Any] | None:
    for raw in reversed(session.get(_TRANSITIONS, [])):
        if not isinstance(raw, Mapping):
            continue
        if (
            str(raw.get("target_kind") or "") == target_kind
            and str(raw.get("target_id") or "") == target_id
            and str(raw.get("from_status") or "") == from_status
            and str(raw.get("to_status") or "") == to_status
            and str(raw.get("basis_type") or "") == basis_type
            and str(raw.get("basis_ref") or "") == basis_ref
        ):
            return raw
    return None


def _validate_transition_log(session: Mapping[str, Any]) -> None:
    log = session.get(_TRANSITIONS)
    if not isinstance(log, list):
        raise _fail("MIDS_TRANSITION_LOG_REQUIRED")
    for index, raw in enumerate(log):
        if not isinstance(raw, Mapping) or set(raw) != _TRANSITION_KEYS:
            raise _fail("MIDS_TRANSITION_SCHEMA_CLOSED", index=index)
        if raw.get("event_type") != "STATE_TRANSITION":
            raise _fail("MIDS_TRANSITION_EVENT_TYPE_INVALID", index=index)
        for key in ("target_kind", "target_id", "from_status", "to_status", "basis_type", "basis_ref"):
            _core._text(raw.get(key), f"{_TRANSITIONS}[{index}].{key}")
        _core._provenance(raw.get("provenance"), f"{_TRANSITIONS}[{index}].provenance")


def _validate_decision_relations(session: Mapping[str, Any]) -> None:
    by_id: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
    for field in ("confirmed_decisions", "inferred_preferences", "candidate_directions"):
        for raw in session.get(field, []):
            if not isinstance(raw, Mapping) or not _decision_id(raw):
                continue
            by_id.setdefault(_decision_id(raw), []).append((field, raw))
    for decision_id, occurrences in by_id.items():
        if len(occurrences) == 1:
            continue
        if len(occurrences) != 2:
            raise _fail("MIDS_DECISION_ID_COLLISION", decision_id=decision_id, occurrences=len(occurrences))
        fields = {field for field, _ in occurrences}
        epistemics = {str(record.get("epistemic_class") or "") for _, record in occurrences}
        statuses = {str(record.get("status") or "") for _, record in occurrences}
        tacit_copy = fields == {"confirmed_decisions", "inferred_preferences"} and epistemics == {"USER_TACIT_CANDIDATE"} and statuses == {"CONFIRMED"}
        ai_copy = fields == {"confirmed_decisions", "candidate_directions"} and epistemics == {"AI_DISCOVERABLE_OPTION"} and statuses == {"ACCEPTED"}
        if not (tacit_copy or ai_copy):
            raise _fail(
                "MIDS_DECISION_ID_COLLISION",
                decision_id=decision_id,
                fields=sorted(fields), epistemic_classes=sorted(epistemics), statuses=sorted(statuses),
            )

    for raw in session.get("confirmed_decisions", []):
        if not isinstance(raw, Mapping):
            continue
        if raw.get("epistemic_class") == "USER_EXPLICIT_CONFIRMED":
            _user_provenance(raw.get("provenance"), "confirmed_decision.provenance")

    revoked_ids: set[str] = set()
    for raw in session.get(_REVOKED, []):
        if not isinstance(raw, Mapping):
            raise _fail("MIDS_REVOKED_DECISION_INVALID")
        _core.validate_decision(raw)
        if raw.get("epistemic_class") != "AI_DISCOVERABLE_OPTION" or raw.get("status") != "REVOKED":
            raise _fail("MIDS_REVOKED_DECISION_HISTORY_INVALID", decision_id=_decision_id(raw))
        _user_provenance(raw.get("user_revocation_provenance"), "revoked_decision.user_revocation_provenance")
        decision_id = _decision_id(raw)
        if not decision_id or decision_id in revoked_ids:
            raise _fail("MIDS_REVOKED_DECISION_ID_DUPLICATE", decision_id=decision_id)
        revoked_ids.add(decision_id)


def _validate_rejection_relations(session: Mapping[str, Any]) -> None:
    candidates = {
        _decision_id(raw): raw
        for raw in session.get("candidate_directions", [])
        if isinstance(raw, Mapping) and _decision_id(raw)
    }
    revoked = {
        _decision_id(raw): raw
        for raw in session.get(_REVOKED, [])
        if isinstance(raw, Mapping) and _decision_id(raw)
    }
    for raw in session.get("rejected_alternatives", []):
        if not isinstance(raw, Mapping):
            raise _fail("MIDS_REJECTION_RECORD_INVALID")
        allowed = {"alternative_id", "reason", "provenance", "transition"}
        if set(raw) != allowed:
            raise _fail("MIDS_REJECTION_SCHEMA_CLOSED", keys=sorted(raw))
        alternative_id = _core._text(raw.get("alternative_id"), "rejection.alternative_id")
        _core._text(raw.get("reason"), "rejection.reason")
        _user_provenance(raw.get("provenance"), "rejection.provenance")
        transition = str(raw.get("transition") or "")
        candidate = candidates.get(alternative_id)
        if candidate is None or candidate.get("epistemic_class") != "AI_DISCOVERABLE_OPTION":
            raise _fail("MIDS_REJECTION_TARGET_NOT_BOUND", alternative_id=alternative_id)
        if transition == "PROPOSED_TO_REJECTED":
            if candidate.get("status") != "REJECTED" or alternative_id in revoked:
                raise _fail("MIDS_REJECTION_TARGET_STATE_MISMATCH", alternative_id=alternative_id)
        elif transition == "ACCEPTED_TO_REVOKED":
            if candidate.get("status") != "REVOKED" or alternative_id not in revoked:
                raise _fail("MIDS_REVOCATION_HISTORY_MISSING", alternative_id=alternative_id)
        else:
            raise _fail("MIDS_REJECTION_TRANSITION_INVALID", transition=transition)


def _validate_resolution_transitions(session: Mapping[str, Any]) -> None:
    for raw in session.get("unknowns", []):
        if not isinstance(raw, Mapping) or str(raw.get("status") or "") != "RESOLVED":
            continue
        basis = raw.get("resolution_basis")
        if not isinstance(basis, Mapping):
            raise _fail("MIDS_TYPED_RESOLUTION_BASIS_REQUIRED", unknown_id=raw.get("unknown_id"))
        basis_type = str(basis.get("type") or "")
        basis_ref = str(basis.get("result_ref") or "")
        if basis_type != "USER_DECISION":
            raise _fail(
                "MIDS_EXTERNAL_RESOLUTION_REQUIRES_AUTHORITY_ADAPTER",
                unknown_id=raw.get("unknown_id"), basis_type=basis_type,
            )
        _user_provenance(basis.get("provenance"), "unknown.resolution_basis.provenance")
        transition = _matching_transition(
            session, target_kind="UNKNOWN", target_id=str(raw.get("unknown_id") or ""),
            from_status="OPEN", to_status="RESOLVED", basis_type=basis_type, basis_ref=basis_ref,
        )
        if transition is None:
            raise _fail("MIDS_UNKNOWN_RESOLUTION_TRANSITION_MISSING", unknown_id=raw.get("unknown_id"))
        _user_provenance(transition.get("provenance"), "unknown.transition.provenance")

    for raw in session.get("contradictions", []):
        if not isinstance(raw, Mapping) or str(raw.get("status") or "") != "RESOLVED":
            continue
        basis = raw.get("resolution_basis")
        if not isinstance(basis, Mapping):
            raise _fail("MIDS_TYPED_RESOLUTION_BASIS_REQUIRED", contradiction_id=raw.get("contradiction_id"))
        basis_type = str(basis.get("type") or "")
        basis_ref = str(basis.get("result_ref") or "")
        if basis_type != "USER_DECISION":
            raise _fail(
                "MIDS_EXTERNAL_RESOLUTION_REQUIRES_AUTHORITY_ADAPTER",
                contradiction_id=raw.get("contradiction_id"), basis_type=basis_type,
            )
        _user_provenance(basis.get("provenance"), "contradiction.resolution_basis.provenance")
        transition = _matching_transition(
            session, target_kind="CONTRADICTION", target_id=str(raw.get("contradiction_id") or ""),
            from_status="OPEN", to_status="RESOLVED", basis_type=basis_type, basis_ref=basis_ref,
        )
        if transition is None:
            raise _fail("MIDS_CONTRADICTION_RESOLUTION_TRANSITION_MISSING", contradiction_id=raw.get("contradiction_id"))
        _user_provenance(transition.get("provenance"), "contradiction.transition.provenance")


def validate_session(session: Mapping[str, Any]) -> None:
    _core.validate_session(session)
    if not isinstance(session.get(_REVOKED), list):
        raise _fail("MIDS_REVOKED_DECISIONS_LEDGER_REQUIRED")
    _validate_transition_log(session)
    _validate_decision_relations(session)
    _validate_rejection_relations(session)
    _validate_resolution_transitions(session)


def new_session(*args: Any, **kwargs: Any) -> dict[str, Any]:
    session = _core.new_session(*args, **kwargs)
    session[_TRANSITIONS] = []
    session[_REVOKED] = []
    validate_session(session)
    return session


def _delegate(name: str, session: Mapping[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    validate_session(session)
    result = getattr(_core, name)(session, *args, **kwargs)
    validate_session(result)
    return result


def add_user_confirmed_decision(session: Mapping[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    decision_id = kwargs.get("decision_id") if "decision_id" in kwargs else (args[0] if args else "")
    _assert_new_id_available(session, str(decision_id))
    return _delegate("add_user_confirmed_decision", session, *args, **kwargs)


def add_tacit_candidate(session: Mapping[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    decision_id = kwargs.get("decision_id") if "decision_id" in kwargs else (args[0] if args else "")
    _assert_new_id_available(session, str(decision_id))
    return _delegate("add_tacit_candidate", session, *args, **kwargs)


def add_ai_proposal(session: Mapping[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    proposal_id = kwargs.get("proposal_id") if "proposal_id" in kwargs else (args[0] if args else "")
    _assert_new_id_available(session, str(proposal_id))
    return _delegate("add_ai_proposal", session, *args, **kwargs)


def confirm_tacit_candidate(session: Mapping[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    return _delegate("confirm_tacit_candidate", session, *args, **kwargs)


def accept_ai_proposal(session: Mapping[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    return _delegate("accept_ai_proposal", session, *args, **kwargs)


def reject_alternative(session: Mapping[str, Any], alternative_id: str, *,
                       user_rejection_provenance: Sequence[Mapping[str, Any]], reason: str) -> dict[str, Any]:
    validate_session(session)
    provenance = _user_provenance(list(user_rejection_provenance), "decision.user_rejection_provenance")
    result = _core.reject_alternative(
        session, alternative_id,
        user_rejection_provenance=provenance, reason=reason,
    )
    _append_transition(
        result, target_kind="AI_PROPOSAL", target_id=alternative_id,
        from_status="PROPOSED", to_status="REJECTED", basis_type="USER_DECISION",
        basis_ref=provenance[-1]["ref"], provenance=provenance,
    )
    validate_session(result)
    return result


def revoke_accepted_ai_proposal(session: Mapping[str, Any], proposal_id: str, *,
                                user_revocation_provenance: Sequence[Mapping[str, Any]], reason: str) -> dict[str, Any]:
    validate_session(session)
    provenance = _user_provenance(list(user_revocation_provenance), "decision.user_revocation_provenance")
    result = _core.revoke_accepted_ai_proposal(
        session, proposal_id,
        user_revocation_provenance=provenance, reason=reason,
    )
    preserved_history = [
        copy.deepcopy(record) for record in result.get("confirmed_decisions", [])
        if isinstance(record, Mapping)
        and record.get("decision_id") == proposal_id
        and record.get("epistemic_class") == "AI_DISCOVERABLE_OPTION"
        and record.get("status") == "REVOKED"
    ]
    if len(preserved_history) != 1:
        raise _fail("MIDS_REVOCATION_HISTORY_MISSING", proposal_id=proposal_id)
    result["confirmed_decisions"] = [
        record for record in result.get("confirmed_decisions", [])
        if not (
            isinstance(record, Mapping)
            and record.get("decision_id") == proposal_id
            and record.get("epistemic_class") == "AI_DISCOVERABLE_OPTION"
            and record.get("status") == "REVOKED"
        )
    ]
    result[_REVOKED].append(preserved_history[0])
    _append_transition(
        result, target_kind="AI_PROPOSAL", target_id=proposal_id,
        from_status="ACCEPTED", to_status="REVOKED", basis_type="USER_DECISION",
        basis_ref=provenance[-1]["ref"], provenance=provenance,
    )
    validate_session(result)
    return result


def set_material_director_intent(session: Mapping[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    return _delegate("set_material_director_intent", session, *args, **kwargs)


def add_unknown(session: Mapping[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    return _delegate("add_unknown", session, *args, **kwargs)


def defer_unknown_as_assumption(session: Mapping[str, Any], unknown_id: str, *, safe_default: str,
                                reason: str, provenance: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    validate_session(session)
    result = _core.defer_unknown_as_assumption(
        session, unknown_id, safe_default=safe_default, reason=reason, provenance=provenance,
    )
    prov = _core._provenance(list(provenance), "unknown.defer_provenance")
    _append_transition(
        result, target_kind="UNKNOWN", target_id=unknown_id,
        from_status="OPEN", to_status="DEFERRED_ASSUMPTION", basis_type="BOUNDED_ASSUMPTION",
        basis_ref=prov[-1]["ref"], provenance=prov,
    )
    validate_session(result)
    return result


def resolve_unknown(session: Mapping[str, Any], unknown_id: str, *,
                    resolution_basis: Mapping[str, Any] | None = None,
                    resolution_ref: str | None = None) -> dict[str, Any]:
    validate_session(session)
    if resolution_ref is not None and resolution_basis is None:
        raise _fail("MIDS_TYPED_RESOLUTION_BASIS_REQUIRED", unknown_id=unknown_id)
    if not isinstance(resolution_basis, Mapping):
        raise _fail("MIDS_TYPED_RESOLUTION_BASIS_REQUIRED", unknown_id=unknown_id)
    basis_type = str(resolution_basis.get("type") or "")
    if basis_type != "USER_DECISION":
        raise _fail("MIDS_EXTERNAL_RESOLUTION_REQUIRES_AUTHORITY_ADAPTER", unknown_id=unknown_id, basis_type=basis_type)
    provenance = _user_provenance(resolution_basis.get("provenance"), "unknown.resolution_basis.provenance")
    basis_ref = _core._text(resolution_basis.get("result_ref"), "unknown.resolution_basis.result_ref")
    result = _core.resolve_unknown(session, unknown_id, resolution_basis=resolution_basis)
    _append_transition(
        result, target_kind="UNKNOWN", target_id=unknown_id,
        from_status="OPEN", to_status="RESOLVED", basis_type="USER_DECISION",
        basis_ref=basis_ref, provenance=provenance,
    )
    validate_session(result)
    return result


def add_contradiction(session: Mapping[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    return _delegate("add_contradiction", session, *args, **kwargs)


def resolve_contradiction(session: Mapping[str, Any], contradiction_id: str, *, resolution_basis: Mapping[str, Any]) -> dict[str, Any]:
    validate_session(session)
    if not isinstance(resolution_basis, Mapping):
        raise _fail("MIDS_TYPED_RESOLUTION_BASIS_REQUIRED", contradiction_id=contradiction_id)
    basis_type = str(resolution_basis.get("type") or "")
    if basis_type != "USER_DECISION":
        raise _fail(
            "MIDS_EXTERNAL_RESOLUTION_REQUIRES_AUTHORITY_ADAPTER",
            contradiction_id=contradiction_id, basis_type=basis_type,
        )
    provenance = _user_provenance(resolution_basis.get("provenance"), "contradiction.resolution_basis.provenance")
    basis_ref = _core._text(resolution_basis.get("result_ref"), "contradiction.resolution_basis.result_ref")
    result = _core.resolve_contradiction(session, contradiction_id, resolution_basis=resolution_basis)
    _append_transition(
        result, target_kind="CONTRADICTION", target_id=contradiction_id,
        from_status="OPEN", to_status="RESOLVED", basis_type="USER_DECISION",
        basis_ref=basis_ref, provenance=provenance,
    )
    validate_session(result)
    return result


def validate_handoff_ready(session: Mapping[str, Any]) -> dict[str, Any]:
    validate_session(session)
    return _core.validate_handoff_ready(session)


def compile_spec_candidate(session: Mapping[str, Any]) -> dict[str, Any]:
    validate_session(session)
    spec = copy.deepcopy(_core.compile_spec_candidate(session))
    spec["mids_transition_log"] = copy.deepcopy(session[_TRANSITIONS])
    spec["revoked_decisions"] = copy.deepcopy(session[_REVOKED])
    return spec
