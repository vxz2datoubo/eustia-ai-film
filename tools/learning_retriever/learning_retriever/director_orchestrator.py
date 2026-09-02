"""Bounded Director Runtime Orchestrator P0.

Creative directing judgment remains AI-owned and method authority remains in
``01_AI电影系统/AI电影系统.md``. This runtime is mechanical: it binds a creative
decision packet to the existing canonical directing/learning runtime, validates
SOAC-shaped state/entity/transition invariants, reuses the existing
CinematicIntent contract, and emits a non-executable minimum-sufficient
execution candidate.

The public entrypoint never accepts caller-supplied Active Work Item or learning
receipts. It instantiates ``DirectorLearningRuntime`` inside each compile call so
there is no replaceable public runtime attribute that can mint trusted receipts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .cinematic_intent import (
    CinematicIntentContractError,
    compile_cinematic_intent_contract,
)
from .runtime import DirectorLearningRuntime


class DirectorRuntimeError(ValueError):
    """Fail-closed Director Runtime contract error."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details = dict(details or {})


_REQUIRED_TOP_LEVEL = {
    "packet_id",
    "scene_diagnosis",
    "director_intent",
    "world_state",
    "events",
    "blocking",
    "performance",
    "cinematic_intent",
    "shot_plan",
    "transition",
    "constraint_autonomy",
    "provenance",
}
_FORBIDDEN_TOP_LEVEL = {
    "work_item_id",
    "active_work_item_resolution",
    "canonical_runtime_receipt",
    "feature_compiler_receipt",
    "hard_routes",
    "story_override",
    "map_override",
    "asset_override",
    "continuity_override",
    "authority_verified",
    "execution_authorized",
}
_SCENE_FIELDS = {
    "dramatic_purpose",
    "audience_knowledge_before",
    "audience_knowledge_after",
    "material_problem",
}
_INTENT_FIELDS = {
    "audience_effect",
    "character_goal",
    "subtext",
    "success_condition",
}
_ENTITY_FIELDS = {"kind", "position", "state"}
_ENTITY_KINDS = {"character", "object", "environment_anchor", "group"}
_TARGET_KINDS = {"ENTITY", "ABSTRACT", "NONE"}
_EVENT_FIELDS = {
    "event_id",
    "agent",
    "action",
    "target",
    "target_kind",
    "instrument",
    "support_or_contact",
    "precondition",
    "result",
    "reaction_trigger",
    "narrative_function",
}
_BLOCKING_FIELDS = {"initial_positions", "movement_paths", "final_positions", "support_contacts"}
_PERFORMANCE_FIELDS = {"objective", "subtext", "observable_behavior"}
_SHOT_FIELDS = {
    "shot_id",
    "dramatic_function",
    "entry_state",
    "events",
    "exit_state",
    "necessity",
    "camera_proposal",
}
_CAMERA_PROPOSAL_ALLOWED = {
    "authority_status",
    "shot_size",
    "orientation",
    "motion",
    "composition",
    "camera_reason",
}
_CAMERA_AUTHORITY_FIELDS = {
    "camera_physical_position",
    "lens_intent",
    "camera_anchor",
    "locked_camera",
    "camera_lock",
}
_TRANSITION_FIELDS = {
    "inherited_entities",
    "changed_entities",
    "explicit_exits_or_removals",
    "next_entry_state",
}
_CONSTRAINT_FIELDS = {
    "locked_constraints_preserved",
    "hard_invariants",
    "guided_choices",
    "free_model_space",
    "final_state",
}
_PROVENANCE_LAYERS = {
    "scene_diagnosis",
    "director_intent",
    "world_state",
    "events",
    "blocking",
    "performance",
    "cinematic_intent",
    "shot_plan",
    "transition",
    "constraint_autonomy",
}


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DirectorRuntimeError("DIRECTOR_PACKET_SCHEMA_INVALID", f"{field} must be a mapping")
    return dict(value)


def _list(value: Any, *, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise DirectorRuntimeError("DIRECTOR_PACKET_SCHEMA_INVALID", f"{field} must be a list")
    return list(value)


def _text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DirectorRuntimeError("DIRECTOR_PACKET_SCHEMA_INVALID", f"{field} must be non-empty text")
    return value.strip()


def _strict(raw: Mapping[str, Any], *, allowed: set[str], required: set[str], field: str) -> None:
    unknown = set(raw) - allowed
    missing = required - set(raw)
    if unknown or missing:
        raise DirectorRuntimeError(
            "DIRECTOR_PACKET_SCHEMA_INVALID",
            f"{field} unknown={sorted(unknown)} missing={sorted(missing)}",
        )


def _text_list(value: Any, *, field: str) -> list[str]:
    items = _list(value, field=field)
    return [_text(item, field=f"{field}[]") for item in items]


def _validate_provenance(packet: Mapping[str, Any]) -> dict[str, Any]:
    provenance = _mapping(packet.get("provenance"), field="provenance")
    unknown = set(provenance) - _PROVENANCE_LAYERS
    missing = _PROVENANCE_LAYERS - set(provenance)
    if unknown:
        raise DirectorRuntimeError(
            "DIRECTOR_PACKET_SCHEMA_INVALID",
            f"provenance references unknown layers: {sorted(unknown)}",
        )
    if missing:
        raise DirectorRuntimeError(
            "DIRECTOR_PACKET_MISSING_PROVENANCE",
            f"missing provenance for layers: {sorted(missing)}",
        )
    for layer in sorted(_PROVENANCE_LAYERS):
        value = provenance[layer]
        if isinstance(value, str):
            if not value.strip():
                raise DirectorRuntimeError(
                    "DIRECTOR_PACKET_MISSING_PROVENANCE", f"empty provenance for {layer}"
                )
        elif isinstance(value, Mapping):
            if not value:
                raise DirectorRuntimeError(
                    "DIRECTOR_PACKET_MISSING_PROVENANCE", f"empty provenance for {layer}"
                )
        else:
            raise DirectorRuntimeError(
                "DIRECTOR_PACKET_MISSING_PROVENANCE",
                f"provenance for {layer} must be text or mapping",
            )
    return provenance


def _validate_scene_and_intent(packet: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    scene = _mapping(packet.get("scene_diagnosis"), field="scene_diagnosis")
    _strict(scene, allowed=_SCENE_FIELDS, required=_SCENE_FIELDS, field="scene_diagnosis")
    for key in sorted(_SCENE_FIELDS):
        _text(scene[key], field=f"scene_diagnosis.{key}")

    intent = _mapping(packet.get("director_intent"), field="director_intent")
    _strict(intent, allowed=_INTENT_FIELDS, required=_INTENT_FIELDS, field="director_intent")
    for key in sorted(_INTENT_FIELDS):
        _text(intent[key], field=f"director_intent.{key}")
    return scene, intent


def _validate_entity(entity_id: str, raw: Any, *, field: str) -> dict[str, Any]:
    entity = _mapping(raw, field=field)
    _strict(entity, allowed=_ENTITY_FIELDS, required=_ENTITY_FIELDS, field=field)
    kind = _text(entity["kind"], field=f"{field}.kind")
    if kind not in _ENTITY_KINDS:
        raise DirectorRuntimeError(
            "DIRECTOR_WORLD_ENTITY_INVALID",
            f"{entity_id} has unsupported kind {kind!r}",
        )
    if entity["position"] is None or entity["state"] is None:
        raise DirectorRuntimeError(
            "DIRECTOR_WORLD_ENTITY_INVALID",
            f"{entity_id} position/state cannot be null",
        )
    return entity


def _validate_world_state(
    packet: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], set[str]]:
    world = _mapping(packet.get("world_state"), field="world_state")
    required = {"entry", "exit", "explicit_exits_or_removals", "state_changes"}
    _strict(world, allowed=required, required=required, field="world_state")

    def state(name: str) -> tuple[dict[str, Any], set[str]]:
        raw_state = _mapping(world[name], field=f"world_state.{name}")
        _strict(
            raw_state,
            allowed={"entities", "invariants"},
            required={"entities", "invariants"},
            field=f"world_state.{name}",
        )
        entities_raw = _mapping(raw_state["entities"], field=f"world_state.{name}.entities")
        invariants = set(_text_list(raw_state["invariants"], field=f"world_state.{name}.invariants"))
        entities = {
            str(entity_id): _validate_entity(
                str(entity_id), value, field=f"world_state.{name}.entities.{entity_id}"
            )
            for entity_id, value in entities_raw.items()
        }
        return entities, invariants

    entry_entities, entry_invariants = state("entry")
    exit_entities, exit_invariants = state("exit")
    if not entry_entities:
        raise DirectorRuntimeError(
            "DIRECTOR_WORLD_ENTITY_INVALID", "world_state.entry.entities cannot be empty"
        )

    # P0 is intentionally conservative. Entry of brand-new entities will gain a
    # dedicated explicit-entry contract in a later slice; implicit appearance is
    # rejected now rather than silently creating world truth.
    new_entities = set(exit_entities) - set(entry_entities)
    if new_entities:
        raise DirectorRuntimeError(
            "DIRECTOR_WORLD_ENTITY_INVALID",
            f"P0 does not permit implicit new world entities: {sorted(new_entities)}",
        )

    explicit_exits = set(
        _text_list(world["explicit_exits_or_removals"], field="world_state.explicit_exits_or_removals")
    )
    unknown_exits = explicit_exits - set(entry_entities)
    if unknown_exits:
        raise DirectorRuntimeError(
            "DIRECTOR_WORLD_ENTITY_INVALID",
            f"explicit exits reference unknown entry entities: {sorted(unknown_exits)}",
        )

    dropped = set(entry_entities) - set(exit_entities) - explicit_exits
    if dropped:
        raise DirectorRuntimeError(
            "DIRECTOR_WORLD_ENTITY_DROPPED",
            f"live entities disappeared without explicit exit/removal: {sorted(dropped)}",
        )
    retained_exits = explicit_exits & set(exit_entities)
    if retained_exits:
        raise DirectorRuntimeError(
            "DIRECTOR_WORLD_ENTITY_INVALID",
            f"explicitly exited entities remain in exit state: {sorted(retained_exits)}",
        )

    # Until a later explicit invariant-change contract exists, current world
    # invariants must survive the unit exactly. Prompt omission cannot retire one.
    if entry_invariants != exit_invariants:
        raise DirectorRuntimeError(
            "DIRECTOR_WORLD_INVARIANT_DROPPED",
            "world invariants changed without an explicit invariant-change contract",
            details={
                "entry_only": sorted(entry_invariants - exit_invariants),
                "exit_only": sorted(exit_invariants - entry_invariants),
            },
        )

    _text_list(world["state_changes"], field="world_state.state_changes")
    return entry_entities, exit_entities, explicit_exits


def _validate_events(
    packet: Mapping[str, Any], *, entity_ids: set[str]
) -> tuple[list[dict[str, Any]], set[str]]:
    events = _list(packet.get("events"), field="events")
    if not events:
        raise DirectorRuntimeError("DIRECTOR_PACKET_SCHEMA_INVALID", "events cannot be empty")

    compiled: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    for index, item in enumerate(events):
        event = _mapping(item, field=f"events[{index}]")
        _strict(event, allowed=_EVENT_FIELDS, required={"event_id", "agent", "action", "result"}, field=f"events[{index}]")
        for key in ("event_id", "agent", "action", "result"):
            _text(event[key], field=f"events[{index}].{key}")
        event_id = str(event["event_id"])
        if event_id in event_ids:
            raise DirectorRuntimeError("DIRECTOR_PACKET_SCHEMA_INVALID", f"duplicate event_id {event_id!r}")
        event_ids.add(event_id)

        agent = str(event["agent"])
        if agent not in entity_ids:
            raise DirectorRuntimeError(
                "DIRECTOR_EVENT_ENTITY_UNBOUND", f"event {event_id} agent {agent!r} is unbound"
            )

        target = event.get("target")
        target_kind = str(event.get("target_kind") or ("NONE" if target in (None, "") else "")).upper()
        if target_kind not in _TARGET_KINDS:
            raise DirectorRuntimeError(
                "DIRECTOR_PACKET_SCHEMA_INVALID",
                f"event {event_id} target_kind must be one of {sorted(_TARGET_KINDS)}",
            )
        if target_kind == "ENTITY":
            target_id = _text(target, field=f"events[{index}].target")
            if target_id not in entity_ids:
                raise DirectorRuntimeError(
                    "DIRECTOR_EVENT_ENTITY_UNBOUND", f"event {event_id} target {target_id!r} is unbound"
                )
        elif target_kind == "NONE" and target not in (None, ""):
            raise DirectorRuntimeError(
                "DIRECTOR_PACKET_SCHEMA_INVALID", f"event {event_id} has target while target_kind=NONE"
            )

        instrument = event.get("instrument")
        if instrument not in (None, ""):
            instrument_id = _text(instrument, field=f"events[{index}].instrument")
            if instrument_id not in entity_ids:
                raise DirectorRuntimeError(
                    "DIRECTOR_EVENT_ENTITY_UNBOUND",
                    f"event {event_id} instrument {instrument_id!r} is unbound",
                )

        contacts = event.get("support_or_contact")
        if contacts not in (None, ""):
            values = contacts if isinstance(contacts, list) else [contacts]
            for contact in values:
                contact_id = _text(contact, field=f"events[{index}].support_or_contact")
                if contact_id not in entity_ids:
                    raise DirectorRuntimeError(
                        "DIRECTOR_EVENT_ENTITY_UNBOUND",
                        f"event {event_id} support/contact {contact_id!r} is unbound",
                    )
        compiled.append(event)
    return compiled, event_ids


def _validate_blocking(
    packet: Mapping[str, Any],
    *,
    entry_entities: Mapping[str, Mapping[str, Any]],
    exit_entities: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    blocking = _mapping(packet.get("blocking"), field="blocking")
    _strict(blocking, allowed=_BLOCKING_FIELDS, required=_BLOCKING_FIELDS, field="blocking")
    entity_ids = set(entry_entities) | set(exit_entities)

    maps = {
        key: _mapping(blocking[key], field=f"blocking.{key}")
        for key in sorted(_BLOCKING_FIELDS)
    }
    for key, value in maps.items():
        unknown_owners = set(value) - entity_ids
        if unknown_owners:
            raise DirectorRuntimeError(
                "DIRECTOR_BLOCKING_ENTITY_UNBOUND",
                f"blocking.{key} references unknown entities: {sorted(unknown_owners)}",
            )

    # Support/contact is a relation, so validating only the owner key is not
    # enough. Every referenced counterpart must also exist in the world state.
    for owner, contacts in maps["support_contacts"].items():
        values = contacts if isinstance(contacts, list) else [contacts]
        for contact in values:
            contact_id = _text(contact, field=f"blocking.support_contacts.{owner}")
            if contact_id not in entity_ids:
                raise DirectorRuntimeError(
                    "DIRECTOR_BLOCKING_ENTITY_UNBOUND",
                    f"blocking support/contact target {contact_id!r} is unbound",
                )

    for entity_id, position in maps["initial_positions"].items():
        declared = entry_entities.get(str(entity_id), {}).get("position")
        if isinstance(declared, str) and isinstance(position, str) and declared.strip() != position.strip():
            raise DirectorRuntimeError(
                "DIRECTOR_PACKET_SCHEMA_INVALID",
                f"blocking initial position for {entity_id} contradicts world entry state",
            )
    for entity_id, position in maps["final_positions"].items():
        declared = exit_entities.get(str(entity_id), {}).get("position")
        if isinstance(declared, str) and isinstance(position, str) and declared.strip() != position.strip():
            raise DirectorRuntimeError(
                "DIRECTOR_PACKET_SCHEMA_INVALID",
                f"blocking final position for {entity_id} contradicts world exit state",
            )
    return blocking


def _validate_performance(
    packet: Mapping[str, Any], *, entry_entities: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    performance = _mapping(packet.get("performance"), field="performance")
    for actor_id, value in performance.items():
        entity = entry_entities.get(str(actor_id))
        if not entity or entity.get("kind") != "character":
            raise DirectorRuntimeError(
                "DIRECTOR_PERFORMANCE_ACTOR_UNBOUND",
                f"performance actor {actor_id!r} is not a declared character entity",
            )
        actor = _mapping(value, field=f"performance.{actor_id}")
        _strict(actor, allowed=_PERFORMANCE_FIELDS, required=_PERFORMANCE_FIELDS, field=f"performance.{actor_id}")
        _text(actor["objective"], field=f"performance.{actor_id}.objective")
        _text(actor["subtext"], field=f"performance.{actor_id}.subtext")
        behavior = actor["observable_behavior"]
        if isinstance(behavior, list):
            if not behavior:
                raise DirectorRuntimeError(
                    "DIRECTOR_PACKET_SCHEMA_INVALID",
                    f"performance.{actor_id}.observable_behavior cannot be empty",
                )
            for index, item in enumerate(behavior):
                _text(item, field=f"performance.{actor_id}.observable_behavior[{index}]")
        else:
            _text(behavior, field=f"performance.{actor_id}.observable_behavior")
    return performance


def _validate_shot_plan(packet: Mapping[str, Any], *, event_ids: set[str]) -> list[dict[str, Any]]:
    shots = _list(packet.get("shot_plan"), field="shot_plan")
    if not shots:
        raise DirectorRuntimeError("DIRECTOR_PACKET_SCHEMA_INVALID", "shot_plan cannot be empty")

    compiled: list[dict[str, Any]] = []
    shot_ids: set[str] = set()
    required = _SHOT_FIELDS - {"camera_proposal"}
    for index, item in enumerate(shots):
        shot = _mapping(item, field=f"shot_plan[{index}]")
        _strict(shot, allowed=_SHOT_FIELDS, required=required, field=f"shot_plan[{index}]")
        for key in ("shot_id", "dramatic_function", "entry_state", "exit_state", "necessity"):
            _text(shot[key], field=f"shot_plan[{index}].{key}")
        shot_id = str(shot["shot_id"])
        if shot_id in shot_ids:
            raise DirectorRuntimeError("DIRECTOR_PACKET_SCHEMA_INVALID", f"duplicate shot_id {shot_id!r}")
        shot_ids.add(shot_id)

        refs = _text_list(shot["events"], field=f"shot_plan[{index}].events")
        if not refs:
            raise DirectorRuntimeError(
                "DIRECTOR_PACKET_SCHEMA_INVALID", f"shot {shot_id} must reference at least one event"
            )
        unknown_refs = set(refs) - event_ids
        if unknown_refs:
            raise DirectorRuntimeError(
                "DIRECTOR_SHOT_EVENT_UNBOUND",
                f"shot {shot_id} references unknown events: {sorted(unknown_refs)}",
            )

        camera_raw = shot.get("camera_proposal")
        if camera_raw not in (None, {}):
            camera = _mapping(camera_raw, field=f"shot_plan[{index}].camera_proposal")
            authority_attempt = set(camera) & _CAMERA_AUTHORITY_FIELDS
            if authority_attempt:
                raise DirectorRuntimeError(
                    "DIRECTOR_CAMERA_AUTHORITY_MINT_ATTEMPT",
                    f"camera proposal tries to mint authority: {sorted(authority_attempt)}",
                )
            _strict(
                camera,
                allowed=_CAMERA_PROPOSAL_ALLOWED,
                required={"authority_status"},
                field=f"shot_plan[{index}].camera_proposal",
            )
            if camera["authority_status"] != "PROPOSAL_ONLY":
                raise DirectorRuntimeError(
                    "DIRECTOR_CAMERA_AUTHORITY_MINT_ATTEMPT",
                    "camera_proposal.authority_status must be PROPOSAL_ONLY",
                )
        compiled.append(shot)
    return compiled


def _validate_transition(
    packet: Mapping[str, Any],
    *,
    entry_ids: set[str],
    exit_ids: set[str],
    explicit_exits: set[str],
) -> dict[str, Any]:
    transition = _mapping(packet.get("transition"), field="transition")
    _strict(transition, allowed=_TRANSITION_FIELDS, required=_TRANSITION_FIELDS, field="transition")

    inherited = set(_text_list(transition["inherited_entities"], field="transition.inherited_entities"))
    changed = set(_text_list(transition["changed_entities"], field="transition.changed_entities"))
    transition_exits = set(
        _text_list(transition["explicit_exits_or_removals"], field="transition.explicit_exits_or_removals")
    )
    if transition_exits != explicit_exits:
        raise DirectorRuntimeError(
            "DIRECTOR_TRANSITION_STATE_MISMATCH",
            "transition explicit exits/removals do not match world_state",
        )

    overlap = (inherited & changed) | (inherited & transition_exits) | (changed & transition_exits)
    if overlap:
        raise DirectorRuntimeError(
            "DIRECTOR_TRANSITION_STATE_MISMATCH",
            f"transition entity classes overlap: {sorted(overlap)}",
        )

    classified = inherited | changed | transition_exits
    if classified != entry_ids:
        raise DirectorRuntimeError(
            "DIRECTOR_TRANSITION_STATE_MISMATCH",
            "every entry entity must be classified exactly once as inherited, changed, or exited",
            details={
                "missing": sorted(entry_ids - classified),
                "unknown": sorted(classified - entry_ids),
            },
        )

    next_entry = _mapping(transition["next_entry_state"], field="transition.next_entry_state")
    _strict(next_entry, allowed={"entities"}, required={"entities"}, field="transition.next_entry_state")
    next_ids = set(_text_list(next_entry["entities"], field="transition.next_entry_state.entities"))
    if next_ids != exit_ids:
        raise DirectorRuntimeError(
            "DIRECTOR_TRANSITION_STATE_MISMATCH",
            f"next entry entities {sorted(next_ids)} do not match world exit entities {sorted(exit_ids)}",
        )
    return transition


def _validate_constraints(packet: Mapping[str, Any], *, canonical_locked: list[str]) -> dict[str, Any]:
    contract = _mapping(packet.get("constraint_autonomy"), field="constraint_autonomy")
    _strict(contract, allowed=_CONSTRAINT_FIELDS, required=_CONSTRAINT_FIELDS, field="constraint_autonomy")

    preserved = set(
        _text_list(
            contract["locked_constraints_preserved"],
            field="constraint_autonomy.locked_constraints_preserved",
        )
    )
    missing = set(canonical_locked) - preserved
    if missing:
        raise DirectorRuntimeError(
            "DIRECTOR_LOCKED_CONSTRAINT_DROPPED",
            f"canonical locked constraints were omitted: {sorted(missing)}",
        )

    hard_invariants = _text_list(contract["hard_invariants"], field="constraint_autonomy.hard_invariants")
    if canonical_locked and not hard_invariants:
        raise DirectorRuntimeError(
            "DIRECTOR_LOCKED_CONSTRAINT_DROPPED",
            "bound work item has locked constraints but execution candidate has no hard invariants",
        )
    _text_list(contract["guided_choices"], field="constraint_autonomy.guided_choices")
    _text_list(contract["free_model_space"], field="constraint_autonomy.free_model_space")
    _text(contract["final_state"], field="constraint_autonomy.final_state")
    return contract


def _canonical_context(retrieval: Mapping[str, Any]) -> tuple[str | None, list[str], dict[str, Any]]:
    receipt = _mapping(retrieval.get("canonical_runtime_receipt"), field="canonical_runtime_receipt")
    resolution = _mapping(
        receipt.get("active_work_item_resolution"),
        field="canonical_runtime_receipt.active_work_item_resolution",
    )
    work_item_id = resolution.get("resolved_work_item_id")
    if work_item_id is not None:
        work_item_id = _text(work_item_id, field="resolved_work_item_id")

    locked: list[str] = []
    context = receipt.get("work_item_context_packet")
    if context is not None:
        context_map = _mapping(context, field="canonical_runtime_receipt.work_item_context_packet")
        constraints = _mapping(
            context_map.get("constraints") or {}, field="work_item_context_packet.constraints"
        )
        locked = [
            _text(value, field="work_item_context_packet.constraints.locked[]")
            for value in list(constraints.get("locked") or [])
        ]
    return work_item_id, locked, receipt


def _render_execution_candidate(
    *,
    scene: Mapping[str, Any],
    intent: Mapping[str, Any],
    events: list[Mapping[str, Any]],
    blocking: Mapping[str, Any],
    performance: Mapping[str, Any],
    cinematic_overlay: Mapping[str, Any],
    shots: list[Mapping[str, Any]],
    constraints: Mapping[str, Any],
) -> dict[str, Any]:
    event_lines = [
        f"{event['event_id']}: {event['agent']} {event['action']} -> {event['result']}"
        for event in events
    ]
    performance_lines = [
        f"{actor}: {value['objective']} | {value['observable_behavior']}"
        for actor, value in performance.items()
    ]
    shot_lines = [
        f"{shot['shot_id']}: {shot['dramatic_function']} | events={','.join(map(str, shot['events']))}"
        for shot in shots
    ]
    lines = [
        f"镜头/段落目的：{scene['dramatic_purpose']}",
        f"观众认知变化：{scene['audience_knowledge_before']} -> {scene['audience_knowledge_after']}",
        f"导演意图：{intent['audience_effect']}",
        f"人物目标：{intent['character_goal']}",
        "事件顺序：" + "；".join(event_lines),
        "场面调度：" + str(dict(blocking)),
        "表演：" + "；".join(performance_lines),
    ]
    if cinematic_overlay:
        lines.append("当前物化电影意图：" + str(dict(cinematic_overlay)))
    lines.extend(
        [
            "镜头方案：" + "；".join(shot_lines),
            "硬不变量：" + "；".join(map(str, constraints["hard_invariants"])),
            f"最终状态：{constraints['final_state']}",
        ]
    )
    return {
        "schema": "GENERIC_DIRECTOR_EXECUTION_CANDIDATE/v1",
        "text": "\n".join(lines),
        "hard_invariant_refs": list(constraints["locked_constraints_preserved"]),
        "execution_authorized": False,
        "deliverable": False,
    }


class DirectorRuntimeOrchestrator:
    """Public trust-bound P0 orchestrator."""

    def __init__(self, project_root: str | Path) -> None:
        self._project_root = Path(project_root)

    def compile(
        self,
        description: str,
        creative_packet: Mapping[str, Any],
        *,
        task_id: str = "DIRECTOR_RUNTIME_P0",
        top_k: int | None = None,
    ) -> dict[str, Any]:
        _text(description, field="description")
        packet = _mapping(creative_packet, field="creative_packet")

        authority_attempt = set(packet) & _FORBIDDEN_TOP_LEVEL
        if authority_attempt:
            raise DirectorRuntimeError(
                "DIRECTOR_PACKET_AUTHORITY_VIOLATION",
                f"creative packet cannot supply authority fields: {sorted(authority_attempt)}",
            )
        unknown = set(packet) - _REQUIRED_TOP_LEVEL
        missing = _REQUIRED_TOP_LEVEL - set(packet)
        if unknown or missing:
            raise DirectorRuntimeError(
                "DIRECTOR_PACKET_SCHEMA_INVALID",
                f"creative packet unknown={sorted(unknown)} missing={sorted(missing)}",
            )
        _text(packet["packet_id"], field="packet_id")
        provenance = _validate_provenance(packet)

        # Trust root is constructed inside the call. There is intentionally no
        # public runtime/callback/receipt injection surface on this orchestrator.
        retrieval = DirectorLearningRuntime(self._project_root).retrieve(
            description,
            task_id=task_id,
            top_k=top_k,
            expand=True,
        )
        work_item_id, canonical_locked, canonical_receipt = _canonical_context(retrieval)

        scene, intent = _validate_scene_and_intent(packet)
        entry_entities, exit_entities, explicit_exits = _validate_world_state(packet)
        all_entity_ids = set(entry_entities) | set(exit_entities)
        events, event_ids = _validate_events(packet, entity_ids=all_entity_ids)
        blocking = _validate_blocking(
            packet,
            entry_entities=entry_entities,
            exit_entities=exit_entities,
        )
        performance = _validate_performance(packet, entry_entities=entry_entities)

        try:
            cinematic = compile_cinematic_intent_contract(
                _mapping(packet["cinematic_intent"], field="cinematic_intent"),
                project_root=self._project_root,
            )
        except CinematicIntentContractError as exc:
            raise DirectorRuntimeError(
                "DIRECTOR_CINEMATIC_INTENT_REJECTED",
                exc.message,
                details={"upstream_code": exc.code},
            ) from exc
        if cinematic.get("status") == "FAIL":
            raise DirectorRuntimeError(
                "DIRECTOR_CINEMATIC_INTENT_REJECTED",
                "existing CinematicIntent contract returned FAIL",
                details={"diagnostics": cinematic.get("diagnostics")},
            )

        shots = _validate_shot_plan(packet, event_ids=event_ids)
        transition = _validate_transition(
            packet,
            entry_ids=set(entry_entities),
            exit_ids=set(exit_entities),
            explicit_exits=explicit_exits,
        )
        constraints = _validate_constraints(packet, canonical_locked=canonical_locked)

        execution_candidate = _render_execution_candidate(
            scene=scene,
            intent=intent,
            events=events,
            blocking=blocking,
            performance=performance,
            cinematic_overlay=dict(cinematic.get("execution_overlay") or {}),
            shots=shots,
            constraints=constraints,
        )

        return {
            "schema": "DIRECTOR_RUNTIME_CANDIDATE/v1",
            "status": "CANDIDATE_READY",
            "packet_id": packet["packet_id"],
            "work_item_binding": {
                "work_item_id": work_item_id,
                "binding_status": "TRUSTED_EXISTING" if work_item_id else "NEW_UNBOUND_CANDIDATE",
                "caller_supplied_authority_accepted": False,
            },
            "runtime_flow": [
                "DirectorLearningRuntime.retrieve",
                "active_work_item_resolution",
                "director_feature_compiler",
                "hard_route",
                "semantic_recall",
                "creative_decision_contract",
                "world_state_persistence",
                "event_graph_binding",
                "blocking_performance_binding",
                "existing_cinematic_intent_contract",
                "shot_plan_binding",
                "transition_contract",
                "constraint_autonomy_contract",
                "minimum_execution_candidate",
            ],
            "learning_context": {
                "hard_routes": list(canonical_receipt.get("hard_routes") or []),
                "feature_compiler_receipt": dict(
                    canonical_receipt.get("feature_compiler_receipt") or {}
                ),
                "full_serialized_recall_receipt_accepted_from_caller": False,
            },
            "director_ir": {
                "scene_diagnosis": scene,
                "director_intent": intent,
                "world_state": packet["world_state"],
                "events": events,
                "blocking": blocking,
                "performance": performance,
                "cinematic_intent": cinematic,
                "shot_plan": shots,
                "transition": transition,
                "constraint_autonomy": constraints,
                "provenance": provenance,
            },
            "minimum_execution_prompt_candidate": execution_candidate,
            "execution_authorized": False,
            "deliverable": False,
            "downstream_gate_required": True,
            "downstream_gate_note": (
                "A canonical pre-output/execution gate must approve the same work-item-bound "
                "context before any real model execution. This P0 cannot grant execution authority."
            ),
            "authority_mutation_allowed": False,
        }
