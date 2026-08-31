"""Bounded semantic evidence helpers for Director Feature Compiler.

This module is not an entity authority and does not infer project truth. It only
provides a fail-closed query-normalization predicate for cases where a surface
clause leader must be proven capable of embodied character action before the
compiler emits character-facing semantics.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable


# Productive Chinese person-role endings. These are semantic morphology, not
# project character names. They preserve transfer to unseen roles such as
# 调查员 / 工程师 / 研究者 / 骑士 without treating arbitrary CJK nouns as people.
PRODUCTIVE_HUMAN_ROLE_SUFFIXES = (
    "者",
    "员",
    "兵",
    "士",
    "师",
    "官",
    "民",
    "徒",
    "僧",
    "人",
    "男",
    "女",
    "孩",
    "妇",
    "夫",
    "客",
    "犯",
)

# Irregular/common person-role heads that are not reliably captured by the
# productive suffixes above. Keep this intentionally small; project character
# names belong in canonical character semantics, not in this utility.
IRREGULAR_HUMAN_ROLE_TERMS = (
    "贵族",
    "医生",
    "祭司",
    "警察",
)

# Open category endings that strongly indicate place/structure/object semantics.
# This blocks unseen nouns such as 钟楼 / 塔楼 / 教堂 / 雕像 without growing a
# literal noun blacklist for every future object.
NON_AGENT_SEMANTIC_SUFFIXES = (
    "楼",
    "塔",
    "堂",
    "殿",
    "堡",
    "宫",
    "像",
    "门",
    "窗",
    "墙",
    "路",
    "道",
    "街",
    "巷",
    "桥",
    "厅",
    "室",
    "房",
    "屋",
    "场",
    "景",
    "山",
    "河",
    "海",
    "树",
    "车",
    "船",
    "桌",
    "椅",
    "灯",
    "旗",
    "柱",
    "井",
    "池",
    "棚",
)

EMBODIED_ORIENTATION_TRANSITIONS = (
    "转身",
    "转过身",
    "回身",
)

PRONOUN_AGENT_TERMS = (
    "他",
    "她",
    "他们",
    "她们",
)


def _bounded_cjk(value: str, *, max_chars: int) -> bool:
    normalized = value.strip()
    return bool(
        normalized
        and len(normalized) <= max_chars
        and all(("\u4e00" <= char <= "\u9fff") or char.isspace() for char in normalized)
    )


def _is_non_agent_head(value: str) -> bool:
    normalized = value.strip().replace(" ", "")
    return bool(normalized and normalized.endswith(NON_AGENT_SEMANTIC_SUFFIXES))


def _has_positive_human_semantics(
    value: str,
    *,
    known_actor_terms: Iterable[str],
) -> bool:
    normalized = value.strip().replace(" ", "")
    if not normalized or _is_non_agent_head(normalized):
        return False

    actor_terms = tuple(
        sorted(
            {
                str(term).strip()
                for term in known_actor_terms
                if str(term).strip()
            }
            | set(PRONOUN_AGENT_TERMS),
            key=len,
            reverse=True,
        )
    )
    if any(normalized.endswith(term) for term in actor_terms):
        return True
    if any(normalized.endswith(term) for term in IRREGULAR_HUMAN_ROLE_TERMS):
        return True
    return normalized.endswith(PRODUCTIVE_HUMAN_ROLE_SUFFIXES)


def bounded_animate_agent_leader(
    value: str,
    *,
    action: str,
    known_actor_terms: Iterable[str],
    modifier_tail_validator: Callable[[str], bool],
    max_chars: int = 20,
) -> bool:
    """Return True only with bounded positive evidence of an embodied agent.

    Evidence order:
    1. known actor/pronoun or productive human-role semantics, optionally followed
       by a bounded manner/modifier tail;
    2. explicit embodied turn transition for an otherwise unseen bounded CJK
       subject, unless the subject has strong non-agent category morphology.

    A plain unknown noun before 面向/朝向 is therefore not sufficient evidence.
    """
    normalized = value.strip()
    if not _bounded_cjk(normalized, max_chars=max_chars):
        return False

    # Try the full leader plus prefixes whose remaining suffix is a bounded
    # modifier. This lets `礼拜堂中央年轻祭司十分郑重地` resolve the human
    # semantic head `祭司` without scene-prefix dictionaries.
    actor_candidates: list[str] = [normalized]
    for split_at in range(1, len(normalized)):
        leader = normalized[:split_at].strip()
        tail = normalized[split_at:].strip()
        if leader and modifier_tail_validator(tail):
            actor_candidates.append(leader)

    for candidate in reversed(actor_candidates):
        if _has_positive_human_semantics(
            candidate,
            known_actor_terms=known_actor_terms,
        ):
            return True

    embodied_transition = any(
        action.startswith(term)
        for term in EMBODIED_ORIENTATION_TRANSITIONS
    )
    if not embodied_transition:
        return False

    # A body-turn predicate is positive agent evidence for an unseen proper name
    # or role, but not for a clearly structural/object noun.
    for candidate in reversed(actor_candidates):
        compact = candidate.strip().replace(" ", "")
        if compact and not _is_non_agent_head(compact):
            return True
    return False
