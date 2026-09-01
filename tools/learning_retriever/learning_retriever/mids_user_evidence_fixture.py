"""Immutable pilot stand-in for upstream USER interaction evidence.

This is deliberately separate from MIDS discovery state.  MIDS may resolve receipts
from this frozen fixture but has no registration/mint API.  Production promotion
requires replacing this fixture with the real upstream interaction/evidence authority.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class UserEvidenceReceipt:
    receipt_id: str
    purpose: str
    subject_ref: str
    statement_digest: str | None = None
    result_ref: str | None = None
    issuer: str = "PILOT_UPSTREAM_USER_INTERACTION_AUTHORITY"


def _digest(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _r(receipt_id: str, purpose: str, subject_ref: str, *, statement: str | None = None,
       result_ref: str | None = None) -> UserEvidenceReceipt:
    return UserEvidenceReceipt(
        receipt_id=receipt_id,
        purpose=purpose,
        subject_ref=subject_ref,
        statement_digest=_digest(statement) if statement is not None else None,
        result_ref=result_ref,
    )


_RECEIPTS = {
    # Primary discovery unittest fixtures.
    "UE-MAIN-RAW": _r("UE-MAIN-RAW", "SESSION_INPUT", "RAW_USER_INTENT", statement="我大概想要这种感觉，但不知道具体应该怎么做"),
    "UE-MAIN-INTENT-KAIM": _r("UE-MAIN-INTENT-KAIM", "MATERIAL_DIRECTOR_INTENT", "MATERIAL_DIRECTOR_INTENT", statement="观众应看到凯姆熟练解决横向移动问题，笑点来自意外而不是他的无能。"),
    "UE-MAIN-DECISION-COMEDY": _r("UE-MAIN-DECISION-COMEDY", "USER_EXPLICIT_DECISION", "D-COMEDY", statement="凯姆保持熟练、干冷，不能拍成笨拙小丑。"),
    "UE-MAIN-CONFIRM-T1": _r("UE-MAIN-CONFIRM-T1", "CONFIRM_TACIT_CANDIDATE", "T1"),
    "UE-MAIN-ACCEPT-WHITE": _r("UE-MAIN-ACCEPT-WHITE", "ACCEPT_AI_PROPOSAL", "P-WHITE-MODEL"),
    "UE-MAIN-REJECT-CLOWN": _r("UE-MAIN-REJECT-CLOWN", "REJECT_AI_PROPOSAL", "P-CLOWN"),
    "UE-MAIN-INTENT-SHORT": _r("UE-MAIN-INTENT-SHORT", "MATERIAL_DIRECTOR_INTENT", "MATERIAL_DIRECTOR_INTENT", statement="让凯姆保持能力感"),
    "UE-MAIN-DECISION-D1-SHORT": _r("UE-MAIN-DECISION-D1-SHORT", "USER_EXPLICIT_DECISION", "D1", statement="不拍成小丑"),
    "UE-CROWD-RAW": _r("UE-CROWD-RAW", "SESSION_INPUT", "RAW_USER_INTENT", statement="群众看到圣女后跪拜，我还没决定具体怎么拍"),
    "UE-CROWD-INTENT": _r("UE-CROWD-INTENT", "MATERIAL_DIRECTOR_INTENT", "MATERIAL_DIRECTOR_INTENT", statement="群众看到圣女后跪拜，并明确面向圣女。"),
    "UE-CROWD-DECISION": _r("UE-CROWD-DECISION", "USER_EXPLICIT_DECISION", "D-CROWD-TARGET", statement="群众的跪拜目标是圣女。"),

    # Transition-authority fixtures.
    "UE-TRANS-RAW": _r("UE-TRANS-RAW", "SESSION_INPUT", "RAW_USER_INTENT", statement="继续这个镜头，但还有几个关键问题没想清楚"),
    "UE-TRANS-INTENT": _r("UE-TRANS-INTENT", "MATERIAL_DIRECTOR_INTENT", "MATERIAL_DIRECTOR_INTENT", statement="凯姆保持熟练，笑点来自意外。"),
    "UE-TRANS-D1": _r("UE-TRANS-D1", "USER_EXPLICIT_DECISION", "D1", statement="不能拍成笨拙小丑。"),
    "UE-TRANS-REJECT-P1": _r("UE-TRANS-REJECT-P1", "REJECT_AI_PROPOSAL", "P1"),
    "UE-TRANS-ACCEPT-P2": _r("UE-TRANS-ACCEPT-P2", "ACCEPT_AI_PROPOSAL", "P2"),
    "UE-TRANS-REJECT-P2": _r("UE-TRANS-REJECT-P2", "REJECT_AI_PROPOSAL", "P2"),
    "UE-TRANS-REVOKE-P2": _r("UE-TRANS-REVOKE-P2", "REVOKE_AI_PROPOSAL", "P2"),
    "UE-TRANS-RESOLVE-U3": _r("UE-TRANS-RESOLVE-U3", "RESOLVE_UNKNOWN", "U3", result_ref="user-choice"),
    "UE-TRANS-RESOLVE-C3": _r("UE-TRANS-RESOLVE-C3", "RESOLVE_CONTRADICTION", "C3", result_ref="priority-choice"),

    # Handoff-guard fixtures.
    "UE-GUARD-RAW": _r("UE-GUARD-RAW", "SESSION_INPUT", "RAW_USER_INTENT", statement="群众出现强烈宗教反应"),
    "UE-GUARD-INTENT": _r("UE-GUARD-INTENT", "MATERIAL_DIRECTOR_INTENT", "MATERIAL_DIRECTOR_INTENT", statement="群众看到圣女后转身面向圣女并跪拜。"),
    "UE-GUARD-D1": _r("UE-GUARD-D1", "USER_EXPLICIT_DECISION", "D1", statement="群众跪拜的目标明确是圣女。"),
    "UE-GUARD-REJECT-D1": _r("UE-GUARD-REJECT-D1", "REJECT_AI_PROPOSAL", "D1"),
    "UE-GUARD-ACCEPT-PREV": _r("UE-GUARD-ACCEPT-PREV", "ACCEPT_AI_PROPOSAL", "P-REV"),
    "UE-GUARD-REJECT-PREV": _r("UE-GUARD-REJECT-PREV", "REJECT_AI_PROPOSAL", "P-REV"),
    "UE-GUARD-REVOKE-PREV": _r("UE-GUARD-REVOKE-PREV", "REVOKE_AI_PROPOSAL", "P-REV"),
    "UE-GUARD-RESOLVE-UUSER": _r("UE-GUARD-RESOLVE-UUSER", "RESOLVE_UNKNOWN", "U-USER", result_ref="user-decision-1"),
    "UE-GUARD-RESOLVE-C1": _r("UE-GUARD-RESOLVE-C1", "RESOLVE_CONTRADICTION", "C1", result_ref="priority"),
}

TRUSTED_USER_EVIDENCE = MappingProxyType(_RECEIPTS)


def resolve_user_evidence(receipt_id: str, *, purpose: str, subject_ref: str,
                          statement: str | None = None, result_ref: str | None = None) -> UserEvidenceReceipt:
    receipt = TRUSTED_USER_EVIDENCE.get(str(receipt_id or "").strip())
    if receipt is None:
        raise LookupError("USER_EVIDENCE_RECEIPT_NOT_TRUSTED")
    if receipt.issuer != "PILOT_UPSTREAM_USER_INTERACTION_AUTHORITY":
        raise LookupError("USER_EVIDENCE_ISSUER_INVALID")
    if receipt.purpose != purpose:
        raise LookupError("USER_EVIDENCE_PURPOSE_MISMATCH")
    if receipt.subject_ref != str(subject_ref):
        raise LookupError("USER_EVIDENCE_SUBJECT_MISMATCH")
    if receipt.statement_digest is not None:
        if statement is None or _digest(statement) != receipt.statement_digest:
            raise LookupError("USER_EVIDENCE_STATEMENT_MISMATCH")
    if receipt.result_ref is not None and receipt.result_ref != str(result_ref or ""):
        raise LookupError("USER_EVIDENCE_RESULT_REF_MISMATCH")
    return receipt
