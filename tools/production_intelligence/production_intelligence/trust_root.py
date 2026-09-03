"""Governed source-root binding for Production Intelligence trust-bearing routes.

The Production Intelligence candidate may validate arbitrary fixture roots in isolated
contract tests, but it may not mint or consume a trusted coordination receipt from a
caller-selected project tree. Trust-bearing runtime paths are bound to the repository
root that contains the executing production_intelligence package itself.
"""
from __future__ import annotations

from pathlib import Path

from .contracts import ProductionIntelligenceError


def governed_project_root() -> Path:
    """Return the repository root containing this executing governed source package."""
    return Path(__file__).resolve().parents[3]


def require_governed_project_root(project_root: str | Path) -> Path:
    """Fail closed if a trust-bearing call attempts to switch authority universes."""
    expected = governed_project_root().resolve()
    observed = Path(project_root).resolve()
    if observed != expected:
        raise ProductionIntelligenceError(
            "TRUSTED_ADAPTER_PROJECT_ROOT_FORBIDDEN",
            details={
                "governed_root": str(expected),
                "caller_root": str(observed),
                "caller_selected_authority_root": False,
            },
        )
    return expected
