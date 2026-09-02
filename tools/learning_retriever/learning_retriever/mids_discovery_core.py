"""Bounded Mixed-Initiative Discovery & Specification (MIDS) candidate runtime.

Coordination-only: no free-text director parsing, hard-route selection, canonical
writes, work-item resolution, model execution, or learning-maturity authority.
This module enforces provenance, legal discovery-state transitions, question budget,
reject/revoke boundaries, handoff readiness, and replay metrics.
"""
from __future__ import annotations

import copy
from typing import Any, Iterable, Mapping, Sequence

EPIS_CLASSES = {
    "USER_EXPLICIT_CONFIRMED",
    "USER_TACIT_CANDIDATE",
    "AI_DISCOVERABLE_OPTION",
    "EXPERT_BLIND_ZONE",
}
SESSION_STATES = {
    "DISCOVERING", "DIVERGING", "CONVERGING", "SPEC_CANDIDATE",
    "READY_FOR_HANDOFF", "DEFERRED",
}
DECISION_STATUSES = {"CONFIRMED", "INFERRED", "PROPOSED", "ACCEPTED", "REJECTED", "REVOKED"}
UNKNOWN_MATERIALITIES = {"LOW", "MEDIUM", "HIGH", "MATERIAL"}
UNKNOWN_STATUSES = {"OPEN", "DEFERRED_ASSUMPTION", "RESOLVED"}
CONTRADICTION_STATUSES = {"OPEN", "RESOLVED"}
RESOLUTION_BASIS_TYPES = {"USER_DECISION", "RESEARCH_EVIDENCE", "UNKNOWN_REGISTRY_RECEIPT"}
QUESTION_SCORE_FIELDS = (
    "decision_impact", "uncertainty_reduction", "dependency_centrality",
    "irreversibility", "novelty_potential", "cognitive_load", "interruption_cost",
)
QUESTION_HARD_MAX = 3


class MIDSDiscoveryError(ValueError):
    def __init__(self, code: str, *, details: Mapping[str, Any] | None = None) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(code)


def _fail(code: str, **details: Any) -> MIDSDiscoveryError:
    return MIDSDiscoveryError(code, details=details or None)


def _text(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise _fail("MIDS_REQUIRED_TEXT_MISSING", field=field)
    return result


def _list(value: Any, field: str) -> list[Any]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise _fail("MIDS_LIST_REQUIRED", field=field)
    return value


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _fail("MIDS_MAPPING_REQUIRED", field=field)
    return value


def _provenance(value: Any, field: str) -> list[dict[str, str]]:
    items = _list(value, field)
    if not items:
        raise _fail("MIDS_PROVENANCE_REQUIRED", field=field)
    out = []
    for index, raw in enumerate(items):
        item = _mapping(raw, f"{field}[{index}]")
        out.append({
            "source": _text(item.get("source"), f"{field}[{index}].source"),
            "ref": _text(item.get("ref"), f"{field}[{index}].ref"),
        })
    return out


def _user_provenance(value: Any, field: str) -> list[dict[str, str]]:
    provenance = _provenance(value, field)
    if not any(item["source"] == "USER" for item in provenance):
        raise _fail("MIDS_USER_PROVENANCE_REQUIRED", field=field)
    return provenance


def _confidence(value: Any) -> str:
    result = str(value or "").strip().upper()
    if result not in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}:
        raise _fail("MIDS_CONFIDENCE_INVALID", value=value)
    return result


def _scale(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise _fail("MIDS_PRIORITY_SCALE_INVALID", field=field, value=value)
    try:
        score = int(value)
    except (TypeError, ValueError) as exc:
        raise _fail("MIDS_PRIORITY_SCALE_INVALID", field=field, value=value) from exc
    if not 0 <= score <= 3:
        raise _fail("MIDS_PRIORITY_SCALE_INVALID", field=field, value=value)
    return score


def _closed_keys(record: Mapping[str, Any], allowed: set[str], kind: str) -> None:
    extra = sorted(set(record) - allowed)
    if extra:
        raise _fail("MIDS_RECORD_SCHEMA_CLOSED", kind=kind, extra_fields=extra)


def validate_work_item_binding(binding: Mapping[str, Any]) -> None:
    mode = str(binding.get("mode") or "").strip()
    if mode == "TRUSTED_EXISTING":
        _text(binding.get("work_item_id"), "work_item_binding.work_item_id")
        basis = _text(binding.get("trust_basis"), "work_item_binding.trust_basis")
        if basis not in {
            "canonical_github_readback_verified_snapshot",
            "canonical_github_readback_historical_binding",
        }:
            raise _fail("MIDS_WORK_ITEM_TRUST_BASIS_INVALID", trust_basis=basis)
    elif mode == "NEW_UNBOUND":
        if str(binding.get("work_item_id") or "").strip():
            raise _fail("MIDS_UNBOUND_WORK_ITEM_CANNOT_CLAIM_CANONICAL_ID")
    else:
        raise _fail("MIDS_WORK_ITEM_BINDING_MODE_INVALID", mode=mode)


def validate_decision(record: Mapping[str, Any]) -> None:
    _text(record.get("decision_id"), "decision_id")
    _text(record.get("statement"), "statement")
    epistemic = str(record.get("epistemic_class") or "").strip()
    status = str(record.get("status") or "").strip()
    if epistemic not in EPIS_CLASSES:
        raise _fail("MIDS_EPISTEMIC_CLASS_INVALID", epistemic_class=epistemic)
    if status not in DECISION_STATUSES:
        raise _fail("MIDS_DECISION_STATUS_INVALID", status=status)
    _provenance(record.get("provenance"), "decision.provenance")

    if epistemic == "USER_EXPLICIT_CONFIRMED" and status != "CONFIRMED":
        raise _fail("MIDS_USER_EXPLICIT_MUST_BE_CONFIRMED")
    if epistemic == "USER_TACIT_CANDIDATE":
        _confidence(record.get("confidence"))
        if status not in {"INFERRED", "CONFIRMED", "REJECTED"}:
            raise _fail("MIDS_TACIT_STATUS_INVALID", status=status)
        if status == "CONFIRMED":
            _user_provenance(record.get("user_confirmation_provenance"), "decision.user_confirmation_provenance")
    if epistemic == "AI_DISCOVERABLE_OPTION":
        if status not in {"PROPOSED", "ACCEPTED", "REJECTED", "REVOKED"}:
            raise _fail("MIDS_AI_PROPOSAL_STATUS_INVALID", status=status)
        if status == "ACCEPTED":
            _user_provenance(record.get("user_acceptance_provenance"), "decision.user_acceptance_provenance")
        if status == "REJECTED":
            _user_provenance(record.get("user_rejection_provenance"), "decision.user_rejection_provenance")
        if status == "REVOKED":
            _user_provenance(record.get("user_revocation_provenance"), "decision.user_revocation_provenance")
            _text(record.get("revocation_reason"), "decision.revocation_reason")
    if epistemic == "EXPERT_BLIND_ZONE" and status == "CONFIRMED":
        raise _fail("MIDS_EXPERT_BLIND_ZONE_CANNOT_BECOME_USER_CONFIRMED_DIRECTLY")


def _validate_resolution_basis(value: Any, field: str) -> dict[str, Any]:
    basis = dict(_mapping(value, field))
    _closed_keys(basis, {"type", "provenance", "result_ref"}, "resolution_basis")
    basis_type = _text(basis.get("type"), f"{field}.type")
    if basis_type not in RESOLUTION_BASIS_TYPES:
        raise _fail("MIDS_RESOLUTION_BASIS_TYPE_INVALID", basis_type=basis_type)
    provenance = _provenance(basis.get("provenance"), f"{field}.provenance")
    if basis_type == "USER_DECISION":
        if not any(item["source"] == "USER" for item in provenance):
            raise _fail("MIDS_USER_RESOLUTION_REQUIRES_USER_PROVENANCE")
    else:
        allowed_sources = {"RESEARCH", "EVIDENCE", "UNKNOWN_REGISTRY"}
        if not any(item["source"] in allowed_sources for item in provenance):
            raise _fail("MIDS_EVIDENCE_RESOLUTION_SOURCE_INVALID", basis_type=basis_type)
    return {
        "type": basis_type,
        "provenance": provenance,
        "result_ref": _text(basis.get("result_ref"), f"{field}.result_ref"),
    }


def validate_unknown(record: Mapping[str, Any]) -> None:
    allowed = {
        "unknown_id", "question", "epistemic_class", "materiality", "status", "blocks_handoff",
        "user_facing_choice", "safe_default", "next_information_action", "resolution_basis",
        "defer_reason", "defer_provenance",
    }
    _closed_keys(record, allowed, "unknown")
    _text(record.get("unknown_id"), "unknown.unknown_id")
    _text(record.get("question"), "unknown.question")
    epistemic = _text(record.get("epistemic_class"), "unknown.epistemic_class")
    if epistemic not in EPIS_CLASSES:
        raise _fail("MIDS_EPISTEMIC_CLASS_INVALID", epistemic_class=epistemic)
    materiality = _text(record.get("materiality"), "unknown.materiality").upper()
    if materiality not in UNKNOWN_MATERIALITIES:
        raise _fail("MIDS_UNKNOWN_MATERIALITY_INVALID", materiality=materiality)
    status = _text(record.get("status"), "unknown.status").upper()
    if status not in UNKNOWN_STATUSES:
        raise _fail("MIDS_UNKNOWN_STATUS_INVALID", status=status)
    if not isinstance(record.get("blocks_handoff"), bool):
        raise _fail("MIDS_UNKNOWN_BLOCKS_HANDOFF_BOOL_REQUIRED")
    if epistemic == "EXPERT_BLIND_ZONE" and not (
        str(record.get("user_facing_choice") or "").strip()
        or str(record.get("next_information_action") or "").strip()
    ):
        raise _fail("MIDS_EXPERT_BLIND_ZONE_REQUIRES_TRANSLATION_OR_RESEARCH_ACTION")
    if status == "OPEN":
        if record.get("resolution_basis") is not None:
            raise _fail("MIDS_OPEN_UNKNOWN_CANNOT_HAVE_RESOLUTION_BASIS")
    elif status == "DEFERRED_ASSUMPTION":
        _text(record.get("safe_default"), "unknown.safe_default")
        _text(record.get("defer_reason"), "unknown.defer_reason")
        _provenance(record.get("defer_provenance"), "unknown.defer_provenance")
        if record.get("resolution_basis") is not None:
            raise _fail("MIDS_DEFERRED_UNKNOWN_CANNOT_CLAIM_RESOLVED")
    else:
        _validate_resolution_basis(record.get("resolution_basis"), "unknown.resolution_basis")


def validate_contradiction(record: Mapping[str, Any]) -> None:
    allowed = {"contradiction_id", "statement", "materiality", "status", "resolution_basis"}
    _closed_keys(record, allowed, "contradiction")
    _text(record.get("contradiction_id"), "contradiction.contradiction_id")
    _text(record.get("statement"), "contradiction.statement")
    materiality = _text(record.get("materiality"), "contradiction.materiality").upper()
    if materiality not in UNKNOWN_MATERIALITIES:
        raise _fail("MIDS_CONTRADICTION_MATERIALITY_INVALID", materiality=materiality)
    status = _text(record.get("status"), "contradiction.status").upper()
    if status not in CONTRADICTION_STATUSES:
        raise _fail("MIDS_CONTRADICTION_STATUS_INVALID", status=status)
    if status == "OPEN":
        if record.get("resolution_basis") is not None:
            raise _fail("MIDS_OPEN_CONTRADICTION_CANNOT_HAVE_RESOLUTION_BASIS")
    else:
        _validate_resolution_basis(record.get("resolution_basis"), "contradiction.resolution_basis")


def new_session(raw_user_intent: str, *, provenance: Sequence[Mapping[str, Any]],
                work_item_binding: Mapping[str, Any] | None = None,
                current_understanding: str = "") -> dict[str, Any]:
    session = {
        "schema": "MIDS_DISCOVERY_SESSION/v1", "mode": "SHADOW_CANDIDATE", "state": "DISCOVERING",
        "raw_user_intent": _text(raw_user_intent, "raw_user_intent"),
        "raw_user_intent_provenance": _provenance(list(provenance), "raw_user_intent_provenance"),
        "work_item_binding": copy.deepcopy(dict(work_item_binding or {"mode": "NEW_UNBOUND"})),
        "current_understanding": str(current_understanding or "").strip(), "material_director_intent": None,
        "confirmed_decisions": [], "inferred_preferences": [], "open_questions": [], "unknowns": [],
        "candidate_directions": [], "rejected_alternatives": [], "qoc": {"questions": [], "options": [], "criteria": []},
        "assumptions": [], "counterexamples": [], "non_goals": [], "success_criteria": [],
        "downstream_dependencies": [], "spec_delta_candidates": [], "examples": [], "decision_rationale": [],
        "contradictions": [], "canonical_known_keys": [],
    }
    validate_session(session)
    return session


def validate_session(session: Mapping[str, Any]) -> None:
    if session.get("schema") != "MIDS_DISCOVERY_SESSION/v1": raise _fail("MIDS_SESSION_SCHEMA_INVALID")
    if session.get("mode") != "SHADOW_CANDIDATE": raise _fail("MIDS_MODE_MUST_REMAIN_SHADOW_CANDIDATE")
    if str(session.get("state") or "") not in SESSION_STATES: raise _fail("MIDS_SESSION_STATE_INVALID")
    _text(session.get("raw_user_intent"), "raw_user_intent")
    _provenance(session.get("raw_user_intent_provenance"), "raw_user_intent_provenance")
    validate_work_item_binding(_mapping(session.get("work_item_binding"), "work_item_binding"))
    list_fields = ("confirmed_decisions", "inferred_preferences", "open_questions", "unknowns", "candidate_directions",
                   "rejected_alternatives", "assumptions", "counterexamples", "non_goals", "success_criteria",
                   "downstream_dependencies", "spec_delta_candidates", "examples", "decision_rationale",
                   "contradictions", "canonical_known_keys")
    for field in list_fields: _list(session.get(field), field)
    qoc = _mapping(session.get("qoc"), "qoc")
    for field in ("questions", "options", "criteria"): _list(qoc.get(field), f"qoc.{field}")
    for record in list(session["confirmed_decisions"]) + list(session["inferred_preferences"]) + list(session["candidate_directions"]):
        validate_decision(_mapping(record, "decision"))
    unknown_ids: set[str] = set()
    for record in session["unknowns"]:
        unknown = _mapping(record, "unknown")
        validate_unknown(unknown)
        unknown_id = _text(unknown.get("unknown_id"), "unknown.unknown_id")
        if unknown_id in unknown_ids:
            raise _fail("MIDS_UNKNOWN_ID_DUPLICATE", unknown_id=unknown_id)
        unknown_ids.add(unknown_id)
    for record in session["contradictions"]: validate_contradiction(_mapping(record, "contradiction"))


def _next(session: Mapping[str, Any]) -> dict[str, Any]:
    validate_session(session)
    return copy.deepcopy(dict(session))


def add_user_confirmed_decision(session: Mapping[str, Any], *, decision_id: str, statement: str,
                                provenance: Sequence[Mapping[str, Any]], rationale: str | None = None) -> dict[str, Any]:
    out = _next(session)
    record = {"decision_id": _text(decision_id, "decision_id"), "statement": _text(statement, "statement"),
              "epistemic_class": "USER_EXPLICIT_CONFIRMED", "status": "CONFIRMED",
              "provenance": _user_provenance(list(provenance), "decision.provenance")}
    validate_decision(record)
    if any(x.get("decision_id") == record["decision_id"] for x in out["confirmed_decisions"]):
        raise _fail("MIDS_DECISION_ID_DUPLICATE", decision_id=record["decision_id"])
    out["confirmed_decisions"].append(record)
    if rationale: out["decision_rationale"].append({"decision_id": record["decision_id"], "rationale": str(rationale).strip()})
    return out


def add_tacit_candidate(session: Mapping[str, Any], *, decision_id: str, statement: str, confidence: str,
                        provenance: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    out = _next(session)
    record = {"decision_id": _text(decision_id, "decision_id"), "statement": _text(statement, "statement"),
              "epistemic_class": "USER_TACIT_CANDIDATE", "status": "INFERRED", "confidence": _confidence(confidence),
              "provenance": _provenance(list(provenance), "decision.provenance")}
    validate_decision(record); out["inferred_preferences"].append(record); return out


def confirm_tacit_candidate(session: Mapping[str, Any], decision_id: str, *,
                            user_confirmation_provenance: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    out = _next(session)
    for record in out["inferred_preferences"]:
        if record.get("decision_id") == decision_id:
            if record.get("status") != "INFERRED": raise _fail("MIDS_TACIT_NOT_OPEN_FOR_CONFIRMATION", decision_id=decision_id)
            record["status"] = "CONFIRMED"
            record["user_confirmation_provenance"] = _user_provenance(list(user_confirmation_provenance), "decision.user_confirmation_provenance")
            validate_decision(record); out["confirmed_decisions"].append(copy.deepcopy(record)); return out
    raise _fail("MIDS_DECISION_NOT_FOUND", decision_id=decision_id)


def add_ai_proposal(session: Mapping[str, Any], *, proposal_id: str, statement: str, rationale: str, expected_effect: str,
                    risks: Sequence[str] = (), tradeoffs: Sequence[str] = (), criteria: Sequence[str] = (),
                    provenance: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    out = _next(session)
    record = {"decision_id": _text(proposal_id, "proposal_id"), "statement": _text(statement, "statement"),
              "epistemic_class": "AI_DISCOVERABLE_OPTION", "status": "PROPOSED",
              "provenance": _provenance(list(provenance or [{"source": "AI", "ref": proposal_id}]), "decision.provenance"),
              "rationale": _text(rationale, "rationale"), "expected_effect": _text(expected_effect, "expected_effect"),
              "risks": [str(x).strip() for x in risks if str(x).strip()],
              "tradeoffs": [str(x).strip() for x in tradeoffs if str(x).strip()],
              "criteria": [str(x).strip() for x in criteria if str(x).strip()]}
    validate_decision(record); out["candidate_directions"].append(record)
    out["qoc"]["options"].append({"option_id": record["decision_id"], "origin": "AI_PROPOSAL", "statement": record["statement"], "criteria": list(record["criteria"])})
    return out


def accept_ai_proposal(session: Mapping[str, Any], proposal_id: str, *, user_acceptance_provenance: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    out = _next(session)
    for record in out["candidate_directions"]:
        if record.get("decision_id") == proposal_id:
            if record.get("status") != "PROPOSED": raise _fail("MIDS_PROPOSAL_NOT_OPEN", proposal_id=proposal_id)
            record["status"] = "ACCEPTED"
            record["user_acceptance_provenance"] = _user_provenance(list(user_acceptance_provenance), "decision.user_acceptance_provenance")
            validate_decision(record); out["confirmed_decisions"].append(copy.deepcopy(record)); return out
    raise _fail("MIDS_PROPOSAL_NOT_FOUND", proposal_id=proposal_id)


def reject_alternative(session: Mapping[str, Any], alternative_id: str, *,
                       user_rejection_provenance: Sequence[Mapping[str, Any]], reason: str) -> dict[str, Any]:
    out = _next(session)
    provenance = _user_provenance(list(user_rejection_provenance), "decision.user_rejection_provenance")
    matches = [x for x in out["candidate_directions"] if x.get("decision_id") == alternative_id]
    if len(matches) != 1: raise _fail("MIDS_REJECTABLE_PROPOSAL_NOT_FOUND", alternative_id=alternative_id)
    record = matches[0]
    if record.get("status") != "PROPOSED":
        if record.get("status") == "ACCEPTED": raise _fail("MIDS_ACCEPTED_PROPOSAL_REQUIRES_REVOCATION", alternative_id=alternative_id)
        raise _fail("MIDS_PROPOSAL_NOT_OPEN", proposal_id=alternative_id)
    record["status"] = "REJECTED"; record["user_rejection_provenance"] = provenance; validate_decision(record)
    out["rejected_alternatives"].append({"alternative_id": alternative_id, "reason": _text(reason, "reason"), "provenance": provenance, "transition": "PROPOSED_TO_REJECTED"})
    return out


def revoke_accepted_ai_proposal(session: Mapping[str, Any], proposal_id: str, *,
                                user_revocation_provenance: Sequence[Mapping[str, Any]], reason: str) -> dict[str, Any]:
    out = _next(session)
    provenance = _user_provenance(list(user_revocation_provenance), "decision.user_revocation_provenance")
    matches = [x for x in out["candidate_directions"] if x.get("decision_id") == proposal_id]
    if len(matches) != 1: raise _fail("MIDS_PROPOSAL_NOT_FOUND", proposal_id=proposal_id)
    candidate = matches[0]
    if candidate.get("epistemic_class") != "AI_DISCOVERABLE_OPTION" or candidate.get("status") != "ACCEPTED":
        raise _fail("MIDS_PROPOSAL_NOT_ACCEPTED_FOR_REVOCATION", proposal_id=proposal_id)
    candidate["status"] = "REVOKED"; candidate["user_revocation_provenance"] = provenance; candidate["revocation_reason"] = _text(reason, "reason")
    changed = False
    for record in out["confirmed_decisions"]:
        if record.get("decision_id") == proposal_id and record.get("epistemic_class") == "AI_DISCOVERABLE_OPTION" and record.get("status") == "ACCEPTED":
            record["status"] = "REVOKED"; record["user_revocation_provenance"] = provenance; record["revocation_reason"] = candidate["revocation_reason"]; changed = True
    if not changed: raise _fail("MIDS_ACCEPTED_PROPOSAL_HISTORY_MISSING", proposal_id=proposal_id)
    validate_decision(candidate)
    for record in out["confirmed_decisions"]: validate_decision(record)
    out["rejected_alternatives"].append({"alternative_id": proposal_id, "reason": candidate["revocation_reason"], "provenance": provenance, "transition": "ACCEPTED_TO_REVOKED"})
    return out


def set_material_director_intent(session: Mapping[str, Any], statement: str, *, provenance: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    out = _next(session); prov = _user_provenance(list(provenance), "material_director_intent.provenance")
    out["material_director_intent"] = {"statement": _text(statement, "material_director_intent.statement"), "epistemic_class": "USER_EXPLICIT_CONFIRMED", "provenance": prov}
    return out


def _question_priority(candidate: Mapping[str, Any]) -> float:
    v = {field: _scale(candidate.get(field, 0), field) for field in QUESTION_SCORE_FIELDS}
    numerator = 2*v["decision_impact"] + 2*v["uncertainty_reduction"] + v["dependency_centrality"] + v["irreversibility"] + v["novelty_potential"]
    if candidate.get("blocks_handoff") is True: numerator += 4
    return numerator / (1 + v["cognitive_load"] + v["interruption_cost"])


def rank_questions(candidates: Sequence[Mapping[str, Any]], *, canonical_known_keys: Iterable[str] = (),
                   resolved_keys: Iterable[str] = (), max_questions: int = 3) -> dict[str, Any]:
    if not 1 <= max_questions <= QUESTION_HARD_MAX: raise _fail("MIDS_QUESTION_BUDGET_INVALID", max_questions=max_questions)
    known = {str(x).strip() for x in canonical_known_keys if str(x).strip()}; known.update(str(x).strip() for x in resolved_keys if str(x).strip())
    ranked, suppressed, seen = [], [], set()
    for raw in candidates:
        q = _mapping(raw, "question"); qid = _text(q.get("question_id"), "question.question_id")
        if qid in seen: raise _fail("MIDS_QUESTION_ID_DUPLICATE", question_id=qid)
        seen.add(qid)
        resolves = tuple(dict.fromkeys(str(x).strip() for x in _list(q.get("resolves_keys"), "question.resolves_keys") if str(x).strip()))
        if not resolves: raise _fail("MIDS_QUESTION_WITHOUT_MATERIAL_TARGET", question_id=qid)
        if q.get("material") is not True: suppressed.append({"question_id": qid, "reason": "NON_MATERIAL"}); continue
        unresolved = tuple(x for x in resolves if x not in known)
        if not unresolved: suppressed.append({"question_id": qid, "reason": "ALREADY_KNOWN_OR_RESOLVED"}); continue
        if q.get("requires_technical_jargon") is True: suppressed.append({"question_id": qid, "reason": "TECHNICAL_JARGON_SHOULD_BE_TRANSLATED"}); continue
        cognitive = _scale(q.get("cognitive_load", 0), "cognitive_load"); interruption = _scale(q.get("interruption_cost", 0), "interruption_cost")
        ranked.append({"question_id": qid, "text": _text(q.get("text"), "question.text"), "resolves_keys": list(unresolved),
                       "priority_score": round(_question_priority(q), 4), "rationale": _text(q.get("rationale"), "question.rationale"),
                       "cognitive_load": cognitive, "interruption_cost": interruption})
    ranked.sort(key=lambda x: (-x["priority_score"], x["cognitive_load"] + x["interruption_cost"], x["question_id"]))
    selected = ranked[:max_questions]
    suppressed.extend({"question_id": x["question_id"], "reason": "LOWER_INFORMATION_VALUE_THIS_ROUND"} for x in ranked[max_questions:])
    return {"schema": "MIDS_QUESTION_SELECTION_RECEIPT/v1", "selected": selected, "suppressed": suppressed,
            "question_budget": max_questions, "hard_max": QUESTION_HARD_MAX, "known_keys_considered": sorted(known)}


def add_unknown(session: Mapping[str, Any], *, unknown_id: str, question: str, epistemic_class: str, materiality: str,
                user_facing_choice: str | None = None, safe_default: str | None = None,
                next_information_action: str | None = None, blocks_handoff: bool = False) -> dict[str, Any]:
    out = _next(session); mat = str(materiality or "").strip().upper()
    if epistemic_class not in EPIS_CLASSES: raise _fail("MIDS_EPISTEMIC_CLASS_INVALID", epistemic_class=epistemic_class)
    if mat not in UNKNOWN_MATERIALITIES: raise _fail("MIDS_UNKNOWN_MATERIALITY_INVALID", materiality=materiality)
    normalized_unknown_id = _text(unknown_id, "unknown_id")
    if any(str(x.get("unknown_id") or "").strip() == normalized_unknown_id for x in out["unknowns"] if isinstance(x, Mapping)):
        raise _fail("MIDS_UNKNOWN_ID_DUPLICATE", unknown_id=normalized_unknown_id)
    record = {"unknown_id": normalized_unknown_id, "question": _text(question, "question"), "epistemic_class": epistemic_class,
              "materiality": mat, "status": "OPEN", "blocks_handoff": bool(blocks_handoff)}
    for key, value in {"user_facing_choice": user_facing_choice, "safe_default": safe_default, "next_information_action": next_information_action}.items():
        if value: record[key] = str(value).strip()
    validate_unknown(record); out["unknowns"].append(record); return out


def defer_unknown_as_assumption(session: Mapping[str, Any], unknown_id: str, *, safe_default: str, reason: str,
                                provenance: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    out = _next(session)
    for record in out["unknowns"]:
        if record.get("unknown_id") == unknown_id:
            if record.get("status") != "OPEN": raise _fail("MIDS_UNKNOWN_NOT_OPEN", unknown_id=unknown_id)
            record["status"] = "DEFERRED_ASSUMPTION"; record["safe_default"] = _text(safe_default, "safe_default")
            record["defer_reason"] = _text(reason, "defer_reason"); record["defer_provenance"] = _provenance(list(provenance), "unknown.defer_provenance")
            validate_unknown(record); return out
    raise _fail("MIDS_UNKNOWN_NOT_FOUND", unknown_id=unknown_id)


def resolve_unknown(session: Mapping[str, Any], unknown_id: str, *, resolution_basis: Mapping[str, Any] | None = None,
                    resolution_ref: str | None = None) -> dict[str, Any]:
    if resolution_ref is not None and resolution_basis is None:
        raise _fail("MIDS_TYPED_RESOLUTION_BASIS_REQUIRED", unknown_id=unknown_id)
    out = _next(session); basis = _validate_resolution_basis(resolution_basis, "unknown.resolution_basis")
    for record in out["unknowns"]:
        if record.get("unknown_id") == unknown_id:
            if record.get("status") != "OPEN": raise _fail("MIDS_UNKNOWN_NOT_OPEN", unknown_id=unknown_id)
            record["status"] = "RESOLVED"; record["resolution_basis"] = basis; validate_unknown(record); return out
    raise _fail("MIDS_UNKNOWN_NOT_FOUND", unknown_id=unknown_id)


def add_contradiction(session: Mapping[str, Any], *, contradiction_id: str, statement: str, materiality: str = "MATERIAL") -> dict[str, Any]:
    out = _next(session)
    record = {"contradiction_id": _text(contradiction_id, "contradiction_id"), "statement": _text(statement, "statement"),
              "materiality": str(materiality).strip().upper(), "status": "OPEN"}
    validate_contradiction(record); out["contradictions"].append(record); return out


def resolve_contradiction(session: Mapping[str, Any], contradiction_id: str, *, resolution_basis: Mapping[str, Any]) -> dict[str, Any]:
    out = _next(session); basis = _validate_resolution_basis(resolution_basis, "contradiction.resolution_basis")
    for record in out["contradictions"]:
        if record.get("contradiction_id") == contradiction_id:
            if record.get("status") != "OPEN": raise _fail("MIDS_CONTRADICTION_NOT_OPEN", contradiction_id=contradiction_id)
            record["status"] = "RESOLVED"; record["resolution_basis"] = basis; validate_contradiction(record); return out
    raise _fail("MIDS_CONTRADICTION_NOT_FOUND", contradiction_id=contradiction_id)


def _decision_origin_allowed(record: Mapping[str, Any]) -> bool:
    epistemic, status = record.get("epistemic_class"), record.get("status")
    if epistemic == "USER_EXPLICIT_CONFIRMED" and status == "CONFIRMED": return True
    if epistemic == "USER_TACIT_CANDIDATE" and status == "CONFIRMED": return bool(record.get("user_confirmation_provenance"))
    if epistemic == "AI_DISCOVERABLE_OPTION" and status == "ACCEPTED": return bool(record.get("user_acceptance_provenance"))
    return False


def _rejection_ids(session: Mapping[str, Any]) -> set[str]:
    return {str(x.get("alternative_id") or "").strip() for x in session.get("rejected_alternatives", []) if str(x.get("alternative_id") or "").strip()}


def validate_handoff_ready(session: Mapping[str, Any]) -> dict[str, Any]:
    validate_session(session); blockers = []; intent = session.get("material_director_intent")
    if not isinstance(intent, Mapping) or not str(intent.get("statement") or "").strip(): blockers.append("MATERIAL_DIRECTOR_INTENT_UNCONFIRMED")
    else:
        try: _user_provenance(intent.get("provenance"), "material_director_intent.provenance")
        except MIDSDiscoveryError: blockers.append("MATERIAL_DIRECTOR_INTENT_PROVENANCE_INVALID")
    if not any(_decision_origin_allowed(x) for x in session.get("confirmed_decisions", [])): blockers.append("NO_CONFIRMED_MATERIAL_DECISION")
    if not session.get("success_criteria"): blockers.append("SUCCESS_CRITERIA_MISSING")
    if not any(str(x.get("kind") or "").upper() == "POSITIVE" for x in session.get("examples", [])): blockers.append("POSITIVE_EXAMPLE_MISSING")
    if not session.get("counterexamples") and not session.get("non_goals"): blockers.append("COUNTEREXAMPLE_OR_NON_GOAL_MISSING")
    if not session.get("downstream_dependencies"): blockers.append("DOWNSTREAM_DEPENDENCY_MISSING")
    if any(
        str(x.get("status") or "").strip().upper() != "RESOLVED"
        and (
            x.get("blocks_handoff") is True
            or str(x.get("materiality") or "").strip().upper() in {"HIGH", "MATERIAL"}
        )
        for x in session.get("unknowns", [])
    ):
        blockers.append("MATERIAL_UNKNOWN_UNRESOLVED")
    if any(str(x.get("status") or "").strip().upper() != "RESOLVED" for x in session.get("contradictions", [])): blockers.append("MATERIAL_CONTRADICTION_UNRESOLVED")
    rejected = _rejection_ids(session)
    if any(x.get("decision_id") in rejected and _decision_origin_allowed(x) for x in session.get("confirmed_decisions", [])):
        blockers.append("REJECTED_ALTERNATIVE_LEAKED_INTO_CONFIRMED_STATE")
    binding = session["work_item_binding"]
    return {"schema": "MIDS_HANDOFF_READINESS/v1", "status": "READY_FOR_FEATURE_COMPILER" if not blockers else "DISCOVERY_REQUIRED",
            "ready": not blockers, "blockers": blockers, "work_item_binding_mode": binding.get("mode"),
            "work_item_id": binding.get("work_item_id"), "authority_boundary": "discovery_spec_candidate_not_director_or_canonical_authority"}


def compile_spec_candidate(session: Mapping[str, Any]) -> dict[str, Any]:
    readiness = validate_handoff_ready(session)
    if not readiness["ready"]: raise _fail("MIDS_HANDOFF_NOT_READY", blockers=readiness["blockers"])
    rejected = _rejection_ids(session)
    included = [copy.deepcopy(dict(x)) for x in session.get("confirmed_decisions", []) if x.get("decision_id") not in rejected and _decision_origin_allowed(x)]
    if any(x.get("epistemic_class") == "USER_TACIT_CANDIDATE" and not x.get("user_confirmation_provenance") for x in included):
        raise _fail("MIDS_INFERENCE_LEAKED_AS_CONFIRMED")
    intent = _mapping(session["material_director_intent"], "material_director_intent"); lines = [str(intent["statement"]).strip()]
    for record in included:
        statement = str(record.get("statement") or "").strip()
        if statement and statement not in lines: lines.append(statement)
    for item in session.get("success_criteria", []):
        text = str(item.get("statement") if isinstance(item, Mapping) else item).strip()
        if text: lines.append(f"验收：{text}")
    for item in session.get("non_goals", []):
        text = str(item.get("statement") if isinstance(item, Mapping) else item).strip()
        if text: lines.append(f"非目标：{text}")
    return {"schema": "MIDS_DISCOVERY_SPEC_CANDIDATE/v1", "status": "READY_FOR_FEATURE_COMPILER", "mode": "SHADOW_CANDIDATE",
            "work_item_binding": copy.deepcopy(session["work_item_binding"]), "director_intent_text": "；".join(lines),
            "confirmed_decisions": included, "success_criteria": copy.deepcopy(session.get("success_criteria", [])),
            "examples": copy.deepcopy(session.get("examples", [])), "counterexamples": copy.deepcopy(session.get("counterexamples", [])),
            "non_goals": copy.deepcopy(session.get("non_goals", [])), "downstream_dependencies": copy.deepcopy(session.get("downstream_dependencies", [])),
            "decision_rationale": copy.deepcopy(session.get("decision_rationale", [])), "rejected_alternative_ids": sorted(rejected),
            "excluded_tacit_candidates": [x.get("decision_id") for x in session.get("inferred_preferences", []) if x.get("status") != "CONFIRMED"],
            "authority_boundary": {"not_canonical_truth": True, "not_director_feature_receipt": True, "not_hard_route_receipt": True,
                                   "not_learning_maturity_authority": True, "must_enter_existing_director_feature_compiler_next": True}}


def score_replay(*, question_receipt: Mapping[str, Any], fixture: Mapping[str, Any], spec_candidate: Mapping[str, Any] | None = None,
                 offered_ai_proposals: int = 0, accepted_ai_proposals: int = 0, post_spec_material_rework_count: int = 0) -> dict[str, Any]:
    selected = list(question_receipt.get("selected") or []); hidden = {str(x) for x in fixture.get("hidden_critical_targets", [])}; canonical = {str(x) for x in fixture.get("canonical_known_keys", [])}
    discovered, redundant, useful, burden = set(), 0, 0, 0
    for question in selected:
        resolves = {str(x) for x in question.get("resolves_keys", [])}; hit = resolves.intersection(hidden); discovered.update(hit)
        useful += bool(hit); redundant += bool(resolves and resolves.issubset(canonical)); burden += int(question.get("cognitive_load") or 0) + int(question.get("interruption_cost") or 0)
    asked = len(selected); contradiction_leakage = authority_violation = 0; traceability = None
    if spec_candidate is not None:
        rejected = set(map(str, spec_candidate.get("rejected_alternative_ids", []))); included = list(spec_candidate.get("confirmed_decisions") or [])
        contradiction_leakage = sum(str(x.get("decision_id")) in rejected for x in included)
        authority_violation = sum(not (x.get("epistemic_class") == "USER_EXPLICIT_CONFIRMED" or (x.get("epistemic_class") == "USER_TACIT_CANDIDATE" and x.get("user_confirmation_provenance")) or (x.get("epistemic_class") == "AI_DISCOVERABLE_OPTION" and x.get("user_acceptance_provenance"))) for x in included)
        traceability = sum(bool(x.get("provenance")) for x in included) / len(included) if included else 1.0
    novel = accepted_ai_proposals / offered_ai_proposals if offered_ai_proposals else None
    return {"schema": "MIDS_REPLAY_EVAL_RESULT/v1", "fixture_id": fixture.get("case_id"),
            "useful_decisions_per_question": round(useful / asked, 4) if asked else 0.0,
            "critical_unknown_discovery": round(len(discovered) / len(hidden), 4) if hidden else 1.0,
            "redundant_question_rate": round(redundant / asked, 4) if asked else 0.0,
            "novel_direction_acceptance": None if novel is None else round(novel, 4), "contradiction_leakage": int(contradiction_leakage),
            "post_spec_rework": int(post_spec_material_rework_count), "user_interruption_cognitive_cost": {"questions": asked, "ordinal_burden_sum": burden},
            "authority_violation": int(authority_violation), "traceability_coverage": None if traceability is None else round(traceability, 4),
            "hidden_targets_discovered": sorted(discovered), "hidden_targets_total": len(hidden)}
