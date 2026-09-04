"""Shared bounded predicate grammar for Director Feature Compiler.

This module is deliberately lexical and authority-neutral. It does not decide
who is a canonical character, create route IDs, or infer story truth. It owns one
small grammar that both the legacy-core adapter and the public safety facade can
consume, preventing target-prefix drift between those layers.
"""
from __future__ import annotations

import re
from collections.abc import Iterable


TARGET_DETERMINER_PREFIXES = (
    "那位", "这位", "一位", "那名", "这名", "一名", "那个", "这个", "一个",
    "那扇", "这扇", "一扇", "那座", "这座", "一座",
)

TARGET_LOCATION_PREFIXES = (
    "高台上的", "高台上", "台上的", "台上", "门口的", "门口",
    "远处的", "远处", "前方的", "前方", "正前方的", "正前方",
    "后方的", "后方", "身后的", "身后", "左侧的", "左侧",
    "右侧的", "右侧", "附近的", "附近",
)

# These residuals appear when a longer action is segmented by the legacy parser,
# e.g. ``目光朝`` + ``向圣女``. They are bounded syntax, never arbitrary prefix.
TARGET_DIRECTION_RESIDUAL_PREFIXES = ("向", "着")

TARGET_PREFIX_TOKENS = tuple(
    dict.fromkeys(
        TARGET_LOCATION_PREFIXES
        + TARGET_DETERMINER_PREFIXES
        + TARGET_DIRECTION_RESIDUAL_PREFIXES
    )
)


def _normalize(value: str) -> str:
    return value.strip().replace(" ", "")


def consume_bounded_target_prefix(value: str) -> tuple[str, bool]:
    """Consume only the finite shared target-prefix grammar from string start.

    Returns ``(residual, consumed_any)``. Unknown material is left intact, so an
    explicit next subject such as ``且凯姆`` can never be mistaken for a target
    prefix by this helper.
    """

    residual = _normalize(value)
    ordered = tuple(sorted(set(TARGET_PREFIX_TOKENS), key=len, reverse=True))
    consumed = False
    changed = True
    while residual and changed:
        changed = False
        for token in ordered:
            if residual.startswith(token):
                residual = residual[len(token):]
                consumed = changed = True
                break
    return residual, consumed


def target_starts_after_bounded_prefix(value: str, target_terms: Iterable[str]) -> bool:
    """Return True iff a target head starts after only shared bounded prefixes."""

    residual, _ = consume_bounded_target_prefix(value)
    targets = tuple(
        sorted({str(term).strip().replace(" ", "") for term in target_terms if str(term).strip()},
               key=len, reverse=True)
    )
    return bool(residual and any(residual.startswith(target) for target in targets))


def normalize_post_action_target_prefixes(
    text: str,
    *,
    action_terms: Iterable[str],
    target_terms: Iterable[str],
) -> tuple[str, bool]:
    """Normalize bounded post-action target prefixes before legacy-core parsing.

    Example: ``菲奥奈面向高台上的圣女`` becomes ``菲奥奈面向圣女`` for the
    frozen core, while the public facade still validates the original text with
    this same grammar. Unknown prefixes are untouched.
    """

    actions = tuple(sorted({str(x) for x in action_terms if str(x)}, key=len, reverse=True))
    targets = tuple(
        sorted({str(x).strip().replace(" ", "") for x in target_terms if str(x).strip()},
               key=len, reverse=True)
    )
    prefixes = tuple(sorted(set(TARGET_PREFIX_TOKENS), key=len, reverse=True))
    if not text or not actions or not targets or not prefixes:
        return text, False

    action_alt = "|".join(re.escape(x) for x in actions)
    prefix_alt = "|".join(re.escape(x) for x in prefixes)
    target_alt = "|".join(re.escape(x) for x in targets)
    pattern = re.compile(
        rf"(?P<action>{action_alt})(?P<prefix>(?:{prefix_alt})+)(?P<target>{target_alt})"
    )
    normalized, count = pattern.subn(lambda m: f"{m.group('action')}{m.group('target')}", text)
    return normalized, bool(count)
