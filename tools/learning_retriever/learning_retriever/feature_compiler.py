"""Director task feature compiler for Learning Smart Recall V1.1.

This module is a deterministic query-normalization layer. It does not store
learning knowledge, change maturity, or become a new authority. It compiles
surface director language into retrieval features consumed by the existing
LearningRetriever and traces those features to canonical SOAC / EventGraphIR /
BlockingIR / VisibleIR semantics.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .route_resolver import RouteResolutionError, resolve_hard_routes


FEATURE_KEYS = (
    "dramatic_function",
    "relation_type",
    "spatial_action_features",
    "failure_mechanism",
)

SOAC_SCHEMA_PATH = Path("10_运行时/screen_observable_audible_ir_schema.yaml")


class FeatureCompilationError(ValueError):
    """Raised when a natural-language director task cannot be compiled safely."""


def _contains_any(text: str, values: tuple[str, ...]) -> bool:
    return any(value in text for value in values)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _merge(existing: Any, compiled: list[str]) -> list[str]:
    if existing is None:
        current: list[str] = []
    elif isinstance(existing, (list, tuple, set)):
        current = [str(value) for value in existing]
    else:
        current = [str(existing)]
    return _dedupe(current + compiled)


@dataclass(frozen=True)
class DirectorFeatures:
    dramatic_function: list[str] = field(default_factory=list)
    relation_type: list[str] = field(default_factory=list)
    spatial_action_features: list[str] = field(default_factory=list)
    failure_mechanism: list[str] = field(default_factory=list)
    semantic_trace: list[str] = field(default_factory=list)
    matched_rules: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, list[str]]:
        return {key: list(getattr(self, key)) for key in FEATURE_KEYS}

    @property
    def recognized(self) -> bool:
        return any(getattr(self, key) for key in FEATURE_KEYS)


def compile_director_features(task: str, *, strict: bool = True) -> DirectorFeatures:
    """Compile director language into retrieval-only mechanism features.

    Mechanism features require relational evidence. Surface nouns or verbs alone
    are not promoted into causal/director mechanisms.
    """
    if not isinstance(task, str) or not task.strip():
        raise FeatureCompilationError("EMPTY_DIRECTOR_TASK")

    text = " ".join(task.casefold().split())
    dramatic: list[str] = []
    relation: list[str] = []
    spatial: list[str] = []
    failure: list[str] = []
    semantic_trace: list[str] = []
    matched_rules: list[str] = []

    def add(target: list[str], *values: str) -> None:
        target.extend(value for value in values if value)

    def trace(rule: str, *paths: str) -> None:
        matched_rules.append(rule)
        semantic_trace.extend(paths)

    # Shared action vocabulary. Target-oriented semantics are added only when a
    # story-material target/source relation is present.
    gaze_terms = ("看向", "望向", "盯着", "注视", "视线朝", "目光朝", "观察")
    facing_terms = ("面向", "朝向", "转向", "身体朝", "正对")
    kneel_terms = ("下跪", "跪向", "跪着朝")
    pursuit_terms = ("追逐", "追击", "追赶", "追捕", "追杀")
    escape_terms = ("逃离", "逃跑", "逃开", "撤离", "远离", "躲避", "摆脱")
    escape_source_terms = ("逃离", "逃开", "远离", "躲避", "摆脱")
    occlusion_terms = ("遮挡", "挡住", "挡在", "遮住")
    camera_actor_terms = ("摄影机", "摄像机", "镜头面向", "机位面向", "camera")
    human_actor_terms = (
        "人物", "角色", "男孩", "女孩", "男人", "女人", "群众", "人群", "信徒", "卫兵", "凯姆", "圣女", "逃犯"
    )
    target_entity_terms = (
        "目标", "圣女", "教会", "敌人", "对手", "逃犯", "追兵", "同伴", "陌生人", "凯姆",
        "人物", "角色", "人群", "群众", "门口", "大门", "门", "窗口", "窗户", "舞台", "出口",
    )
    explicit_target = _contains_any(text, target_entity_terms)
    camera_only_orientation = _contains_any(text, camera_actor_terms) and not _contains_any(text, human_actor_terms)

    crowd_terms = ("群众", "人群", "百姓", "信徒", "灾民", "居民", "民众", "围观者")
    institution_terms = (
        "教会", "圣女", "政府", "统治者", "王室", "官员", "军队", "组织", "救济", "施粥", "布道", "权威",
    )
    crowd_relation_cues = (
        "看向", "望向", "注视", "观察", "等待救济", "等待施粥", "聆听", "欢呼", "沉默", "嘲笑",
        "反应", "态度", "跪向", "下跪", "转向", "聚焦",
    )
    crowd_has_relation = (
        _contains_any(text, crowd_terms)
        and _contains_any(text, crowd_relation_cues)
        and (_contains_any(text, institution_terms) or explicit_target)
    )
    if crowd_has_relation:
        add(dramatic, "crowd_reaction", "social_behavior")
        add(spatial, "crowd_attention_shift", "heterogeneous_microreaction")
        if _contains_any(text, institution_terms):
            add(relation, "crowd_to_institution")
        if _contains_any(text, ("态度", "反应", "违和", "喜剧", "嘲笑", "乱动", "乱晃", "不合理")):
            add(failure, "motive_tone_mismatch")
        trace(
            "crowd_social_response",
            "PerformanceIR.motive_to_motion_envelope",
            "EventGraphIR.narrative_function",
            "BlockingIR.relative_positions",
        )

    exposition_terms = (
        "解释", "世界观", "历史", "背景说明", "旁白", "起源", "传说", "设定说明", "说明这段", "交代背景",
    )
    if _contains_any(text, exposition_terms):
        add(dramatic, "worldbuilding_exposition")
        if _contains_any(text, ("历史", "起源", "传说", "过去时代", "旧时代")):
            add(relation, "speaker_to_history")
        else:
            add(relation, "speaker_to_listener")
        if _contains_any(text, ("拖慢", "停滞", "冗长", "啰嗦", "卡住", "节奏慢", "信息段")):
            add(failure, "exposition_stall")
        trace(
            "exposition",
            "ShotPlanIR.dramatic_function",
            "EventGraphIR.narrative_function",
            "EventGraphIR.reveal_effect",
        )

    dialogue_terms = ("对白", "台词", "galgame", "gal ", "长句", "口语化", "说话太长", "文字游戏")
    if _contains_any(text, dialogue_terms):
        add(dramatic, "dialogue_adaptation")
        add(relation, "speaker_to_listener")
        if _contains_any(text, ("长句", "galgame", "文字游戏", "书面", "说不出口", "口语化")):
            add(failure, "written_sentence_shape_leak")
        trace(
            "dialogue_adaptation",
            "AudibleIR.dialogue_fields",
            "PerformanceIR.breath",
            "PerformanceIR.pause",
        )

    has_gaze = _contains_any(text, gaze_terms)
    has_facing = _contains_any(text, facing_terms)
    has_kneel = _contains_any(text, kneel_terms)
    has_pursuit = _contains_any(text, pursuit_terms)
    has_escape = _contains_any(text, escape_terms)
    has_occlusion = _contains_any(text, occlusion_terms)

    # Pursuit/escape can exist without a known target. Keep the action observable,
    # but do not fabricate a locatable target or target relation.
    if has_pursuit:
        add(dramatic, "pursuit")
        add(spatial, "pursuit")
        trace("pursuit_action", "EventGraphIR.action", "BlockingIR.movement_paths")
    if has_escape:
        add(dramatic, "escape")
        add(spatial, "escape")
        trace("escape_action", "EventGraphIR.action", "BlockingIR.approach_or_retreat")

    target_relation_present = False
    if explicit_target and not camera_only_orientation:
        if has_gaze:
            target_relation_present = True
            add(relation, "gaze_to_target")
            add(spatial, "gaze_direction")
            add(failure, "gaze_target_spatial_binding_fail")
        if has_facing:
            target_relation_present = True
            add(relation, "facing_to_target")
            add(spatial, "body_orientation")
            add(failure, "body_orientation_target_fail")
        if has_kneel:
            target_relation_present = True
            add(relation, "kneeling_to_target")
            add(spatial, "kneeling_to_target", "body_orientation")
            add(failure, "body_orientation_target_fail")
        if has_pursuit:
            target_relation_present = True
            add(relation, "pursuit_to_target")
            add(spatial, "body_orientation")
        if has_escape and _contains_any(text, escape_source_terms):
            target_relation_present = True
            add(relation, "escape_from_target")
            add(spatial, "body_orientation")
        if has_occlusion:
            target_relation_present = True
            add(dramatic, "blocking")
            add(relation, "occlusion_to_target")
            add(spatial, "blocking", "occlusion")

    if target_relation_present:
        add(dramatic, "target_oriented_action")
        add(spatial, "locatable_target")
        trace(
            "target_oriented_spatial_binding",
            "EventGraphIR.action",
            "EventGraphIR.target",
            "BlockingIR.orientations",
            "BlockingIR.movement_paths",
            "BlockingIR.occlusion",
            "VisibleIR.body_orientation",
            "VisibleIR.gaze_target",
        )

    protection_terms = ("保护", "护住", "掩护", "护送", "守护", "挡在身前", "挡在前面")
    protection_target_terms = ("同伴", "陌生人", "她", "他", "孩子", "伤员", "平民", "队友", "蒂娅")
    if _contains_any(text, protection_terms) and _contains_any(text, protection_target_terms):
        add(dramatic, "protective_intervention")
        add(relation, "protector_dependant")
        add(failure, "protection_under_pressure")
        if _contains_any(text, ("挡在", "掩护", "护住")):
            add(spatial, "blocking", "occlusion")
        trace(
            "protective_intervention",
            "EventGraphIR.agent",
            "EventGraphIR.action",
            "EventGraphIR.target",
            "BlockingIR.relative_positions",
            "BlockingIR.occlusion",
        )

    constrained_terms = (
        "狭窄", "街巷", "走廊", "巷道", "通道", "封锁", "堵住", "堵死", "死路", "无法脱身", "无路可逃",
    )
    if (has_pursuit or has_escape) and _contains_any(text, constrained_terms):
        add(dramatic, "pursuit", "blocking")
        add(spatial, "constrained_space", "pursuit_blocking", "blocking")
        trace(
            "constrained_pursuit_blocking",
            "BlockingIR.relative_positions",
            "BlockingIR.movement_paths",
            "BlockingIR.approach_or_retreat",
            "BlockingIR.final_positions",
            "VisibleIR.relative_position",
        )

    prior_terms = ("过去", "旧决定", "旧选择", "此前", "先前", "曾经")
    choice_terms = ("选择", "决定", "决策", "承诺", "所作所为")
    consequence_terms = ("代价", "后果", "危险", "反噬", "牵连", "拖入", "导致", "付出")
    if _contains_any(text, prior_terms) and _contains_any(text, choice_terms) and _contains_any(text, consequence_terms):
        add(dramatic, "consequence_reveal")
        add(relation, "choice_to_consequence")
        add(failure, "consequence_of_prior_choice")
        trace(
            "prior_choice_consequence",
            "EventGraphIR.temporal_relation.CAUSES",
            "EventGraphIR.state_change",
            "EventGraphIR.result",
            "EventGraphIR.reveal_effect",
        )

    contact_terms = ("攀爬", "爬墙", "踩", "抓住", "抓着", "接触", "落脚", "支撑", "撞上", "碰到", "落地")
    if _contains_any(text, contact_terms):
        add(dramatic, "contact_causality")
        add(spatial, "support_point", "sequential_contact")
        add(failure, "contact_binding_fail")
        trace(
            "physical_contact_binding",
            "EventGraphIR.support_or_contact",
            "BlockingIR.prop_interaction",
            "VisibleIR.support_or_contact",
            "VisibleIR.environmental_response",
        )

    if _contains_any(text, ("先后顺序", "事件顺序", "先再", "先…再", "顺序不对", "动作顺序")):
        add(dramatic, "event_order")
        add(failure, "event_order_fail")
        trace("event_order", "EventGraphIR.temporal_relation", "EventGraphIR.precondition", "EventGraphIR.result")

    if _contains_any(text, ("动作不对", "穿帮", "连续性", "保持一致", "世界状态", "背景状态", "前后不一致")):
        add(relation, "continuity_inheritance")
        add(spatial, "continuity_inheritance")
        add(failure, "canonical_world_state_violation")
        trace(
            "continuity_world_state",
            "WorldStateIR.world_invariants",
            "TransitionContract.inherited_state",
            "VisibleIR.canonical_background_evidence",
        )

    result = DirectorFeatures(
        dramatic_function=_dedupe(dramatic),
        relation_type=_dedupe(relation),
        spatial_action_features=_dedupe(spatial),
        failure_mechanism=_dedupe(failure),
        semantic_trace=_dedupe(semantic_trace),
        matched_rules=_dedupe(matched_rules),
    )
    if strict and not result.recognized:
        raise FeatureCompilationError("NO_RECOGNIZED_DIRECTOR_FEATURES")
    return result


def compile_retrieval_task(
    description: str,
    *,
    task_id: str = "UNSPECIFIED_TASK",
    base_task: dict[str, Any] | None = None,
    route_data: dict[str, Any] | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """Compile natural language, then resolve hard routes from route authority.

    Natural-language retrieval fails closed when director_route_index data is not
    supplied. This prevents callers from silently skipping the canonical hard
    route stage.
    """
    features = compile_director_features(description, strict=strict)
    task = dict(base_task or {})
    task["task_id"] = str(task.get("task_id") or task_id)
    for key, compiled in features.as_dict().items():
        task[key] = _merge(task.get(key), compiled)
    try:
        task["hard_routes"] = resolve_hard_routes(task, route_data, description=description)
    except RouteResolutionError as exc:
        raise FeatureCompilationError(str(exc)) from exc
    task["feature_compiler_receipt"] = {
        "component": "DIRECTOR_FEATURE_COMPILER_V1_1",
        "status": "PASS" if features.recognized else "FAIL",
        "input_fingerprint": hashlib.sha256(description.encode("utf-8")).hexdigest()[:16],
        "compiled_feature_keys": [key for key in FEATURE_KEYS if getattr(features, key)],
        "matched_rules": list(features.matched_rules),
        "semantic_trace": list(features.semantic_trace),
        "route_resolution": "director_route_index",
        "hard_routes": list(task["hard_routes"]),
        "authority_boundary": "retrieval_query_only",
    }
    return task


def validate_semantic_dependencies(project_root: str | Path) -> list[str]:
    """Validate that compiler assumptions still bind to the canonical SOAC IR."""
    root = Path(project_root)
    path = root / SOAC_SCHEMA_PATH
    if not path.exists():
        return [f"missing semantic dependency: {SOAC_SCHEMA_PATH.as_posix()}"]
    schema = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    errors: list[str] = []

    director_method = str((schema.get("authority_and_interfaces") or {}).get("director_method") or "")
    if "SOAC-001" not in director_method:
        errors.append("screen observable/audible IR no longer binds director_method to SOAC-001")

    layers = schema.get("ir_layers") or {}
    required_fields = {
        "EventGraphIR": {
            "event_fields": {
                "agent", "action", "target", "support_or_contact", "precondition", "temporal_relation",
                "state_change", "result", "reveal_effect", "narrative_function",
            }
        },
        "BlockingIR": {
            "fields": {
                "relative_positions", "orientations", "movement_paths", "approach_or_retreat", "occlusion",
                "prop_interaction", "final_positions",
            }
        },
        "VisibleIR": {
            "entity_fields": {"relative_position", "body_orientation", "gaze_target", "current_action", "support_or_contact"},
            "environment_fields": {"environmental_response", "canonical_background_evidence"},
        },
    }
    for layer_name, field_groups in required_fields.items():
        layer = layers.get(layer_name)
        if not isinstance(layer, dict):
            errors.append(f"missing semantic layer: {layer_name}")
            continue
        for field_name, expected in field_groups.items():
            observed = set(layer.get(field_name) or [])
            missing = sorted(expected - observed)
            if missing:
                errors.append(f"{layer_name}.{field_name} missing: {', '.join(missing)}")
    return errors
