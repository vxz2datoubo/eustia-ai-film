"""Public Post-Final-Delta authority facade.

The historical cohort validator is retained as a private projection core. Public
callers must not feed serialized Final-Delta results into that projection because
caller-shaped COMPARABLE/RESOLVED fields could otherwise look like trusted
repair evidence. Production callers must use ``post_final_delta_source_bound``
so each source package is re-executed through the governed Final-Delta runtime.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ._post_final_delta_core_v3 import (
    STRUCTURAL_GATE_CODES,
    PostFinalDeltaValidationError,
)


def assess_post_final_delta_validation(
    raw: Mapping[str, Any], *, project_root: str | Path
) -> dict[str, Any]:
    """Reject serialized Final-Delta authority at the public module boundary.

    ``raw`` is intentionally not inspected for internal consistency. A caller
    cannot earn authority by constructing a self-consistent serialized result.
    Use ``assess_source_bound_post_final_delta`` with ``final_delta_inputs``.
    """

    del raw, project_root
    raise PostFinalDeltaValidationError(
        "POST_FD_AUTHORITY_VIOLATION",
        "serialized Final-Delta projection is internal-only; use source-bound Final-Delta reexecution",
    )
