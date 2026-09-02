"""Immutable pilot stand-in for upstream USER interaction evidence.

MIDS consumes this fixture but has no registration/mint API.  Receipt resolution is
bound to session context, purpose, subject and (when applicable) exact statement/result.
Production promotion must replace this fixture with the real upstream interaction authority.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class UserEvidenceReceipt:
    receipt_id: str
    context_digest: str
    purpose: str
    subject_ref: str
    statement_digest: str | None = None
    result_ref: str | None = None
    issuer: str = "PILOT_UPSTREAM_USER_INTERACTION_AUTHORITY"


def _digest(text: str) -> str:
    return hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()


def _r(receipt_id: str, context: str, purpose: str, subject_ref: str, *,
       statement: str | None = None, result_ref: str | None = None) -> UserEvidenceReceipt:
    return UserEvidenceReceipt(
        receipt_id=receipt_id,
        context_digest=_digest(context),
        purpose=purpose,
        subject_ref=subject_ref,
        statement_digest=_digest(statement) if statement is not None else None,
        result_ref=result_ref,
    )


MAIN = "我大概想要这种感觉，但不知道具体应该怎么做"
UNBOUND = "想设计一个还没确定的新镜头"
TRANS = "继续这个镜头，但还有几个关键问题没想清楚"
GUARD = "群众出现强烈宗教反应"
CROWD = "群众看到圣女后跪拜，我还没决定具体怎么拍"

# A tuple rather than a mutable registry. Repeated test aliases are separate exact
# context bindings; knowing one alias does not authorize another session/subject/purpose.
TRUSTED_USER_EVIDENCE = (
    _r("turn-user-1", MAIN, "SESSION_INPUT", "RAW_USER_INTENT", statement=MAIN),
    _r("turn-user-1", UNBOUND, "SESSION_INPUT", "RAW_USER_INTENT", statement=UNBOUND),
    _r("intent", MAIN, "MATERIAL_DIRECTOR_INTENT", "MATERIAL_DIRECTOR_INTENT", statement="观众应看到凯姆熟练解决横向移动问题，笑点来自意外而不是他的无能。"),
    _r("decision", MAIN, "USER_EXPLICIT_DECISION", "D-COMEDY", statement="凯姆保持熟练、干冷，不能拍成笨拙小丑。"),
    _r("confirm-t1", MAIN, "CONFIRM_TACIT_CANDIDATE", "T1"),
    _r("accept-p", MAIN, "ACCEPT_AI_PROPOSAL", "P-WHITE-MODEL"),
    _r("reject", MAIN, "REJECT_AI_PROPOSAL", "P-CLOWN"),
    _r("turn-user-1", MAIN, "MATERIAL_DIRECTOR_INTENT", "MATERIAL_DIRECTOR_INTENT", statement="让凯姆保持能力感"),
    _r("turn-user-1", MAIN, "USER_EXPLICIT_DECISION", "D1", statement="不拍成小丑"),

    _r("crowd-intent", CROWD, "SESSION_INPUT", "RAW_USER_INTENT", statement=CROWD),
    _r("crowd-intent-confirmed", CROWD, "MATERIAL_DIRECTOR_INTENT", "MATERIAL_DIRECTOR_INTENT", statement="群众看到圣女后跪拜，并明确面向圣女。"),
    _r("crowd-target", CROWD, "USER_EXPLICIT_DECISION", "D-CROWD-TARGET", statement="群众的跪拜目标是圣女。"),

    _r("raw", TRANS, "SESSION_INPUT", "RAW_USER_INTENT", statement=TRANS),
    _r("intent", TRANS, "MATERIAL_DIRECTOR_INTENT", "MATERIAL_DIRECTOR_INTENT", statement="凯姆保持熟练，笑点来自意外。"),
    _r("d1", TRANS, "USER_EXPLICIT_DECISION", "D1", statement="不能拍成笨拙小丑。"),
    _r("reject", TRANS, "REJECT_AI_PROPOSAL", "P1"),
    _r("accept", TRANS, "ACCEPT_AI_PROPOSAL", "P2"),
    _r("reject", TRANS, "REJECT_AI_PROPOSAL", "P2"),
    _r("revoke", TRANS, "REVOKE_AI_PROPOSAL", "P2"),
    _r("user-choice", TRANS, "RESOLVE_UNKNOWN", "U3", result_ref="user-choice"),
    _r("priority-choice", TRANS, "RESOLVE_CONTRADICTION", "C3", result_ref="priority-choice"),
    # Legitimate bases used to prove direct status mutation still needs a transition.
    _r("forged-user-basis", TRANS, "RESOLVE_UNKNOWN", "U1", result_ref="forged-user-basis"),
    _r("forged", TRANS, "RESOLVE_CONTRADICTION", "C1", result_ref="forged"),

    _r("raw", GUARD, "SESSION_INPUT", "RAW_USER_INTENT", statement=GUARD),
    _r("intent", GUARD, "MATERIAL_DIRECTOR_INTENT", "MATERIAL_DIRECTOR_INTENT", statement="群众看到圣女后转身面向圣女并跪拜。"),
    _r("decision", GUARD, "USER_EXPLICIT_DECISION", "D1", statement="群众跪拜的目标明确是圣女。"),
    _r("reject-collision", GUARD, "REJECT_AI_PROPOSAL", "D1"),
    _r("reject", GUARD, "REJECT_AI_PROPOSAL", "D1"),
    _r("accept", GUARD, "ACCEPT_AI_PROPOSAL", "P-REV"),
    _r("reject", GUARD, "REJECT_AI_PROPOSAL", "P-REV"),
    _r("revoke", GUARD, "REVOKE_AI_PROPOSAL", "P-REV"),
    _r("user-decision-1", GUARD, "RESOLVE_UNKNOWN", "U-USER", result_ref="user-decision-1"),
    _r("priority", GUARD, "RESOLVE_CONTRADICTION", "C1", result_ref="priority"),
)


def resolve_user_evidence(receipt_id: str, *, context_text: str, purpose: str, subject_ref: str,
                          statement: str | None = None, result_ref: str | None = None) -> UserEvidenceReceipt:
    normalized_id = str(receipt_id or "").strip()
    candidates = [receipt for receipt in TRUSTED_USER_EVIDENCE if receipt.receipt_id == normalized_id]
    if not candidates:
        raise LookupError("USER_EVIDENCE_RECEIPT_NOT_TRUSTED")
    context_digest = _digest(context_text)
    statement_digest = _digest(statement) if statement is not None else None
    for receipt in candidates:
        if receipt.issuer != "PILOT_UPSTREAM_USER_INTERACTION_AUTHORITY":
            continue
        if receipt.context_digest != context_digest:
            continue
        if receipt.purpose != purpose or receipt.subject_ref != str(subject_ref):
            continue
        if receipt.statement_digest is not None and receipt.statement_digest != statement_digest:
            continue
        if receipt.result_ref is not None and receipt.result_ref != str(result_ref or ""):
            continue
        return receipt
    raise LookupError("USER_EVIDENCE_BINDING_MISMATCH")
