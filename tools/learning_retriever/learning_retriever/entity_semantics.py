"""Bounded semantic evidence helpers for Director Feature Compiler.

This module does not own character truth. Canonical project character identity is
read only through PROJECT_INDEX -> canonical.character_db inside the governed
repository checkout. Open human roles are positive query-normalization evidence,
not a second character database and not permission to infer arbitrary CJK nouns
as people.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path
import re

import yaml


CHARACTER_DB_DOCUMENT_ID = "EUSTIA-CHARACTER-PERFORMANCE-LIBRARY"
EXPECTED_PROJECT_ID = "EUSTIA_AI_FILM"


class EntitySemanticError(ValueError):
    """Raised when canonical character typing cannot be read safely."""


# Deliberately bounded human-role heads. We do not use productive suffixes such
# as 人/士/师/员 as identity proof because compounds such as 稻草人/雪人/假人
# would otherwise mint actor truth. This vocabulary is retrieval-normalization
# evidence only; formal named identities still come from the canonical table.
HUMAN_ROLE_HEADS = (
    "贵族", "骑士", "医生", "调查员", "工程师", "研究者", "祭司", "警察",
    "士兵", "军官", "守卫", "护卫", "卫兵", "侍卫", "佣兵", "猎人",
    "商人", "摊贩", "店主", "工匠", "农民", "渔民", "居民", "平民",
    "信徒", "修女", "神父", "学者", "教师", "护士", "船员", "水手",
    "仆人", "女仆", "侍者", "犯人", "囚犯", "伤员", "病人", "孩子",
    "男孩", "女孩", "男人", "女人", "妇人", "老人", "青年", "少女",
    "少年", "百姓", "民众", "群众", "灾民", "围观者", "同伴", "队友",
    "追兵", "逃犯", "陌生人",
)

PRONOUN_AGENT_TERMS = ("他", "她", "他们", "她们")

# High-confidence non-agent compounds that specifically attack the old productive
# suffix defect. These are not a universal object ontology; they are a fail-closed
# boundary for forms that superficially resemble human nouns.
NON_AGENT_COMPOUNDS = (
    "稻草人", "假人", "雪人", "纸人", "木偶人", "机器人", "人偶", "木偶",
    "玩偶", "雕像", "石像", "蜡像", "傀儡", "人体模型",
)

NON_AGENT_SEMANTIC_SUFFIXES = (
    "楼", "塔", "堂", "殿", "堡", "宫", "像", "门", "窗", "墙", "路", "道",
    "街", "巷", "桥", "厅", "室", "房", "屋", "场", "景", "山", "河", "海",
    "树", "车", "船", "桌", "椅", "灯", "旗", "柱", "井", "池", "棚", "碑",
    "坛", "偶", "模型",
)

DYNASTY_WORLD_PREFIXES = ("王朝", "前朝", "本朝", "朝代")
FAKE_OR_OBJECT_ROLE_PREFIXES = ("稻草", "木偶", "纸", "雪", "蜡", "石", "玩具", "假")


def load_canonical_character_terms(project_root: str | Path) -> tuple[str, ...]:
    """Read formal character names/aliases through PROJECT_INDEX only."""

    root = Path(project_root).resolve()
    index_path = root / "PROJECT_INDEX.yaml"
    if not index_path.is_file():
        raise EntitySemanticError("PROJECT_INDEX_REQUIRED_FOR_ENTITY_SEMANTICS")

    try:
        index = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # pragma: no cover - bounded runtime error
        raise EntitySemanticError("PROJECT_INDEX_ENTITY_SEMANTICS_PARSE_FAILED") from exc

    if index.get("project_id") != EXPECTED_PROJECT_ID:
        raise EntitySemanticError("PROJECT_INDEX_ENTITY_SEMANTICS_IDENTITY_MISMATCH")

    relative = str((index.get("canonical") or {}).get("character_db") or "").strip()
    if not relative:
        raise EntitySemanticError("CANONICAL_CHARACTER_DB_NOT_REGISTERED")
    if (index.get("effective_sources") or {}).get(relative) != "github_verified":
        raise EntitySemanticError("CANONICAL_CHARACTER_DB_NOT_GITHUB_VERIFIED")

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


def _explicitly_non_agent(value: str) -> bool:
    normalized = value.strip().replace(" ", "")
    if not normalized:
        return True
    if normalized.endswith(NON_AGENT_COMPOUNDS):
        return True
    if normalized.endswith(NON_AGENT_SEMANTIC_SUFFIXES):
        return True
    return False


def _worldbuilding_prefix_blocks_actor(candidate: str, actor_term: str) -> bool:
    normalized = candidate.strip().replace(" ", "")
    if not normalized.endswith(actor_term):
        return False
    prefix = normalized[: -len(actor_term)] if actor_term else normalized
    return any(prefix.endswith(token) for token in DYNASTY_WORLD_PREFIXES)


def _fake_object_prefix_blocks_role(candidate: str, role: str) -> bool:
    normalized = candidate.strip().replace(" ", "")
    if not normalized.endswith(role):
        return False
    prefix = normalized[: -len(role)] if role else normalized
    return any(prefix.endswith(token) for token in FAKE_OR_OBJECT_ROLE_PREFIXES)


def _has_positive_human_semantics(value: str, *, known_actor_terms: Iterable[str]) -> bool:
    normalized = value.strip().replace(" ", "")
    if not normalized or _explicitly_non_agent(normalized):
        return False

    known = tuple(
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
    for term in known:
        if normalized.endswith(term):
            if _worldbuilding_prefix_blocks_actor(normalized, term):
                continue
            return True

    for role in sorted(HUMAN_ROLE_HEADS, key=len, reverse=True):
        if normalized.endswith(role) and not _fake_object_prefix_blocks_role(normalized, role):
            return True
    return False


def bounded_animate_agent_leader(
    value: str,
    *,
    action: str,
    known_actor_terms: Iterable[str],
    modifier_tail_validator: Callable[[str], bool],
    max_chars: int = 20,
) -> bool:
    """Return True only with bounded positive evidence of an animate agent.

    ``action`` is intentionally not used as identity proof. A turn/body verb may
    describe motion, but cannot convert an unknown object or prop into a person.
    """

    del action
    normalized = value.strip()
    if not _bounded_cjk(normalized, max_chars=max_chars):
        return False

    actor_candidates: list[str] = [normalized]
    for split_at in range(1, len(normalized)):
        leader = normalized[:split_at].strip()
        tail = normalized[split_at:].strip()
        if leader and modifier_tail_validator(tail):
            actor_candidates.append(leader)

    return any(
        _has_positive_human_semantics(candidate, known_actor_terms=known_actor_terms)
        for candidate in reversed(actor_candidates)
    )
