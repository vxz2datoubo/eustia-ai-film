"""Public Active Work Item API.

Implementation lives in the fixed-GitHub trust-root module so local Git cannot
become an authority surface.
"""

from ._active_work_item_remote import (
    ActiveWorkItemResolutionError,
    CANONICAL_BRANCH,
    CANONICAL_REPOSITORY,
    CONTINUITY_PATH,
    PROJECT_INDEX_PATH,
    WorkItemResolution,
    apply_constraint_ledger,
    build_work_item_context_packet,
    is_continuation_request,
    load_active_work_item_state,
    resolve_work_item,
    validate_output_work_item,
    validate_state_transition,
    validate_work_item_context_packet,
)

__all__ = [
    "ActiveWorkItemResolutionError",
    "CANONICAL_BRANCH",
    "CANONICAL_REPOSITORY",
    "CONTINUITY_PATH",
    "PROJECT_INDEX_PATH",
    "WorkItemResolution",
    "apply_constraint_ledger",
    "build_work_item_context_packet",
    "is_continuation_request",
    "load_active_work_item_state",
    "resolve_work_item",
    "validate_output_work_item",
    "validate_state_transition",
    "validate_work_item_context_packet",
]
