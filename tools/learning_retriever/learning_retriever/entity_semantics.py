"""Bounded semantic evidence helpers for Director Feature Compiler.

This module does not own character truth. Project character identity is read only
through the character database path registered by PROJECT_INDEX; open-vocabulary
human-role morphology remains query-normalization evidence, not a second entity
authority.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
import re

import yaml


CHARACTER_DB_DOCUMENT_ID = "EUSTIA-CHARACTER-PERFORMANCE-LIBRARY"


class EntitySemanticError(ValueError):
    """Raised when canonical character typing cannot be read safely."""


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
# names come from the canonical character table instead of this utility.
IRREGULAR_HUMAN_ROLE_TERMS = (
    "贵族",
    "医生",
    "祭司",
    "警察",
)

# Open category endings that strongly indicate place/structure/object semantics.
# This is a secondary negative boundary only. A canonical character identity,
# when present, takes precedence over generic morphology.
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

PRONOUN_AGENT_TERMS = (
    "他",
    "她",
    "他们",
    "她们",
)


def load_canonical_character_terms(project_root: str | Path) -> tuple[str, ...]:
    """Read formal character names/aliases through PROJECT_INDEX only.

    The loader intentionally extracts identity tokens from the canonical role
    table and nothing else. It cannot create or mutate character truth.
    """
    root = Path(project_root).resolve()
    index_path = root / "PROJECT_INDEX.yaml"
    if not index_path.is_file():
        raise EntitySemanticError("PROJECT_INDEX_REQUIRED_FOR_ENTITY_SEMANTICS")

    try:
        index = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # pragma: no cover - surfaced as bounded runtime error
        raise EntitySemanticError("PROJECT_INDEX_ENTITY_SEMANTICS_PARSE_FAILED") from exc

    relative = str((index.get("canonical") or {}).get("character_db") or "").strip()
    if not relative:
        raise EntitySemanticError("CANONICAL_CHARACTER_DB_NOT_REGISTERED")

    character_path = (root / relative).resolve()
    try:
        character_path.relative_to(root)
    except ValueError as exc:
        raise EntitySemanticError("CANONICAL_CHARACTER_DB_PATH_ESCAPES_PROJECT") from exc
    if not character_path.is_file():
        raise EntitySemanticError("CANONICAL_CHARACTER_DB_MISSING")

    content = character_path.read_text(encoding="utf-8")
    if f"document_id: {CHARACTER_DB_DOCUMENT_ID}" not in content:
        raise EntitySemanticError("CANONICAL_CHARACTER_DB_IDENTITY_MISMATCH")

    marker = "# 2. 角色总表"
    if marker not in content:
        raise EntitySemanticError("CANONICAL_CHARACTER_TABLE_MISSING")
    section = content.split(marker, 1)[1]
    if "# 3." in section:
        section = section.split("# 3.", 1)[0]

    terms: set[str] = set()
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("| CHARACTER-EUSTIA-"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        formal_name = cells[1].strip()
        aliases = cells[2].strip()
        if formal_name:
            terms.add(formal_name)
        if aliases and aliases != "无":
            for alias in re.split(r"[、，,;/]+", aliases):
                alias = alias.strip()
                if alias and alias != "无":
                    terms.add(alias)

    if not terms:
        raise EntitySemanticError("CANONICAL_CHARACTER_TABLE_EMPTY")
    return tuple(sorted(terms, key=lambda value: (-len(value), value)))


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
    if not normalized:
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
    # Explicit/canonical character identity outranks generic noun morphology.
    if any(normalized.endswith(term) for term in actor_terms):
        return True
    if _is_non_agent_head(normalized):
        return False
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
    """Return True only with bounded positive evidence of an animate agent.

    Positive evidence is limited to canonical/known character identity,
    pronouns, or productive human-role semantics. An embodied verb such as
    `转身` is an action predicate, not identity proof by itself; therefore novel
    objects cannot become characters merely by being placed before that verb.
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

    return any(
        _has_positive_human_semantics(
            candidate,
            known_actor_terms=known_actor_terms,
        )
        for candidate in reversed(actor_candidates)
    )
