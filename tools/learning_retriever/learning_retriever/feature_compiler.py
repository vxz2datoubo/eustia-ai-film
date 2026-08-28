"""Director task feature compiler for Learning Smart Recall V1.1.

This module is a deterministic query-normalization layer. It does not store
learning knowledge, change maturity, or become a new authority. It compiles
surface director language into retrieval features consumed by the existing
LearningRetriever and traces those features to canonical SOAC / EventGraphIR /
BlockingIR / VisibleIR / CinematicIntentIR semantics.
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
    are not promoted into causal/director mechanisms. Cinematic vocabulary is
    likewise bounded: style/capture/reference nouns may describe a valid intent,
    while failure tokens require explicit problem evidence.
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

    def clause_after(action: str, *, max_chars: int = 24) -> str:
        hit = text.find(action)
        if hit < 0:
            return ""
        tail = text[hit + len(action): hit + len(action) + max_chars]
        for separator in ("，", "。", "；", "！", "？", ",", ";", "!", "?"):
            tail = tail.split(separator, 1)[0]
        return tail

    def action_has_object(actions: tuple[str, ...], objects: tuple[str, ...]) -> bool:
        for action in actions:
            tail = clause_after(action)
            if tail and _contains_any(tail, objects):
                return True
        return False

    def first_action_object_match(
        actions: tuple[str, ...], objects: tuple[str, ...], *, max_chars: int = 32
    ) -> dict[str, Any] | None:
        """Return the earliest bounded action->object match with absolute positions."""
        object_candidates = sorted(set(objects), key=len, reverse=True)
        matches: list[dict[str, Any]] = []
        for action in actions:
            search_from = 0
            while True:
                hit = text.find(action, search_from)
                if hit < 0:
                    break
                tail_start = hit + len(action)
                tail = text[tail_start: tail_start + max_chars]
                for separator in ("，", "。", "；", "！", "？", ",", ";", "!", "?"):
                    tail = tail.split(separator, 1)[0]
                object_hits: list[tuple[int, int, str]] = []
                for obj in object_candidates:
                    object_offset = tail.find(obj)
                    if object_offset >= 0:
                        object_hits.append((object_offset, -len(obj), obj))
                if object_hits:
                    object_offset, _, obj = min(object_hits)
                    object_pos = tail_start + object_offset
                    matches.append(
                        {
                            "action": action,
                            "action_pos": hit,
                            "object": obj,
                            "object_pos": object_pos,
                            "object_end": object_pos + len(obj),
                        }
                    )
                search_from = hit + len(action)
        if not matches:
            return None
        return min(matches, key=lambda item: (item["action_pos"], item["object_pos"]))

    def nearest_actor_before(position: int, actors: tuple[str, ...], *, max_chars: int = 18) -> str | None:
        prefix_start = max(0, position - max_chars)
        prefix = text[prefix_start:position]
        candidates: list[tuple[int, str]] = []
        for actor in actors:
            hit = prefix.rfind(actor)
            if hit >= 0:
                candidates.append((hit, actor))
        if not candidates:
            return None
        return max(candidates, key=lambda item: item[0])[1]

    def first_action_after(actions: tuple[str, ...], position: int) -> tuple[str, int] | None:
        matches = [(action, text.find(action, position)) for action in actions]
        matches = [(action, hit) for action, hit in matches if hit >= 0]
        if not matches:
            return None
        return min(matches, key=lambda item: item[1])

    def same_agent_continuation_is_proven(
        source_actor: str | None,
        between: str,
        *,
        temporal_terms: tuple[str, ...],
        continuation_adverbs: tuple[str, ...],
        target_followup_terms: tuple[str, ...],
    ) -> bool:
        """Verify the complete inter-event chain before carrying the prior target.

        Every punctuation-delimited segment between perception target and ritual
        action is checked. A segment may contain only bounded temporal/adverbial
        glue, an explicit repetition of the source actor, or (in the first
        segment only) a bounded predicate that still belongs to the already
        identified perception target. Any other lexical material represents an
        unproven event-agent transition and fails closed.
        """
        if not source_actor:
            return False

        separators = ("，", "。", "；", "！", "？", ",", ";", "!", "?")
        segments = [between]
        for separator in separators:
            split_segments: list[str] = []
            for segment in segments:
                split_segments.extend(segment.split(separator))
            segments = split_segments

        base_allowed = tuple(sorted(set(temporal_terms + continuation_adverbs), key=len, reverse=True))
        first_segment_allowed = tuple(
            sorted(set(base_allowed + target_followup_terms), key=len, reverse=True)
        )

        for index, segment in enumerate(segments):
            residual = segment.strip()
            if not residual:
                continue

            source_actor_removed = False
            allowed = first_segment_allowed if index == 0 else base_allowed
            while residual:
                stripped = residual.lstrip()
                if not source_actor_removed and stripped.startswith(source_actor):
                    residual = stripped[len(source_actor):]
                    source_actor_removed = True
                    continue

                matched = False
                for token in allowed:
                    if stripped.startswith(token):
                        residual = stripped[len(token):]
                        matched = True
                        break
                if not matched:
                    return False

        return True

    def camera_is_action_agent(actions: tuple[str, ...], camera_terms: tuple[str, ...]) -> bool:
        for action in actions:
            hit = text.find(action)
            if hit < 0:
                continue
            prefix = text[max(0, hit - 10):hit]
            if _contains_any(prefix, camera_terms):
                return True
        return False

    gaze_terms = ("看向", "望向", "盯着", "注视", "视线朝", "目光朝", "观察")
    perception_terms = ("看到", "看见", "见到")
    facing_terms = ("面向", "朝向", "转向", "身体朝", "正对")
    ritual_kneel_terms = ("跪拜", "拜下", "拜倒", "伏地跪拜")
    kneel_terms = ("下跪", "跪向", "跪着朝") + ritual_kneel_terms
    pursuit_terms = ("追逐", "追击", "追赶", "追捕", "追杀")
    escape_terms = ("逃离", "逃跑", "逃开", "撤离", "远离", "躲避", "摆脱")
    escape_source_terms = ("逃离", "逃开", "远离", "躲避", "摆脱")
    occlusion_terms = ("遮挡", "挡住", "挡在", "遮住")
    camera_actor_terms = ("摄影机", "摄像机", "镜头", "机位", "camera")
    actor_terms = (
        "群众", "人群", "百姓", "信徒", "灾民", "居民", "民众", "围观者", "人物", "角色", "男孩", "女孩",
        "男人", "女人", "卫兵", "凯姆", "蒂娅", "圣女",
    )
    target_object_terms = (
        "目标", "圣女", "教会", "敌人", "对手", "逃犯", "追兵", "同伴", "陌生人", "凯姆", "蒂娅",
        "她", "他", "孩子", "伤员", "平民", "队友", "门口", "大门", "门", "窗口", "窗户", "舞台", "出口",
    )
    temporal_carry_terms = ("后", "之后", "随后", "随即", "便", "于是", "立刻", "马上", "接着", "继而")
    continuation_adverb_terms = ("纷纷", "共同", "一起", "一同", "全都", "都")
    target_followup_terms = ("现身", "出现", "降临", "到来")
    alternate_kneel_reason_terms = (
        "爆炸", "冲击", "碎石", "坍塌", "枪声", "攻击", "躲避", "避险", "摔倒", "绊倒", "受伤", "失去平衡",
    )

    has_gaze = _contains_any(text, gaze_terms)
    has_perception = _contains_any(text, perception_terms)
    has_facing = _contains_any(text, facing_terms)
    has_kneel = _contains_any(text, kneel_terms)
    has_pursuit = _contains_any(text, pursuit_terms)
    has_escape = _contains_any(text, escape_terms)
    has_occlusion = _contains_any(text, occlusion_terms)

    gaze_camera_agent = camera_is_action_agent(gaze_terms, camera_actor_terms)
    perception_camera_agent = camera_is_action_agent(perception_terms, camera_actor_terms)
    facing_camera_agent = camera_is_action_agent(facing_terms, camera_actor_terms)
    direct_gaze_target_evidence = has_gaze and not gaze_camera_agent and action_has_object(gaze_terms, target_object_terms)
    perception_target_match = (
        first_action_object_match(perception_terms, target_object_terms)
        if has_perception and not perception_camera_agent
        else None
    )
    perception_target_evidence = perception_target_match is not None
    gaze_target_evidence = direct_gaze_target_evidence or perception_target_evidence
    facing_target_evidence = has_facing and not facing_camera_agent and action_has_object(facing_terms, target_object_terms)

    ritual_target_carry = False
    if perception_target_match:
        ritual_match = first_action_after(ritual_kneel_terms, perception_target_match["object_end"])
        if ritual_match:
            _, ritual_pos = ritual_match
            source_actor = nearest_actor_before(perception_target_match["action_pos"], actor_terms)
            between = text[perception_target_match["object_end"]:ritual_pos]
            agent_continuity_proven = same_agent_continuation_is_proven(
                source_actor,
                between,
                temporal_terms=temporal_carry_terms,
                continuation_adverbs=continuation_adverb_terms,
                target_followup_terms=target_followup_terms,
            )
            competing_target = any(
                target in between
                for target in target_object_terms
                if target != perception_target_match["object"]
            )
            ritual_target_carry = bool(
                source_actor
                and agent_continuity_proven
                and _contains_any(between, temporal_carry_terms)
                and not competing_target
                and not _contains_any(between, alternate_kneel_reason_terms)
            )
            if ritual_target_carry:
                trace(
                    "bounded_cross_event_target_carry",
                    "EventGraphIR.agent",
                    "EventGraphIR.target",
                    "EventGraphIR.temporal_relation",
                    "BlockingIR.orientations",
                )

    direct_kneel_target_evidence = has_kneel and action_has_object(kneel_terms, target_object_terms)
    kneel_target_evidence = has_kneel and (
        direct_kneel_target_evidence or facing_target_evidence or ritual_target_carry
    )
    pursuit_target_evidence = has_pursuit and action_has_object(pursuit_terms, target_object_terms)
    escape_source_evidence = has_escape and action_has_object(escape_source_terms, target_object_terms)
    occlusion_target_evidence = has_occlusion and action_has_object(occlusion_terms, target_object_terms)

    if (has_gaze and not gaze_camera_agent) or (has_perception and not perception_camera_agent):
        add(spatial, "gaze_direction")
        trace("observable_gaze_direction", "VisibleIR.gaze_target", "BlockingIR.orientations")
    if has_facing and not facing_camera_agent:
        add(spatial, "body_orientation")
        trace("observable_body_orientation", "VisibleIR.body_orientation", "BlockingIR.orientations")

    crowd_terms = ("群众", "人群", "百姓", "信徒", "灾民", "居民", "民众", "围观者")
    institution_terms = (
        "教会", "圣女", "政府", "统治者", "王室", "官员", "军队", "组织", "救济", "施粥", "布道", "权威",
    )
    crowd_relation_cues = (
        "看向", "望向", "注视", "观察", "看到", "看见", "见到", "等待救济", "等待施粥", "聆听", "欢呼", "沉默",
        "嘲笑", "反应", "态度", "跪向", "下跪", "跪拜", "拜下", "拜倒", "转向", "聚焦",
    )
    crowd_has_relation = (
        _contains_any(text, crowd_terms)
        and _contains_any(text, crowd_relation_cues)
        and (
            _contains_any(text, institution_terms)
            or gaze_target_evidence
            or facing_target_evidence
            or kneel_target_evidence
        )
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

    generic_cinematic_terms = (
        "电影感", "高级感", "cinematic", "masterpiece", "史诗感", "大片感", "dramatic lighting", "电影级",
    )
    generic_cinematic_problem_terms = (
        "堆质量词", "只会堆", "像广告", "广告感", "像cg", "cg感", "像游戏", "游戏感", "油腻", "没有叙事理由",
        "没叙事理由", "只像壁纸", "只是滤镜", "空泛电影感",
    )
    if _contains_any(text, generic_cinematic_terms) or _contains_any(text, generic_cinematic_problem_terms):
        add(dramatic, "cinematic_visual_design")
        if _contains_any(text, generic_cinematic_problem_terms):
            add(failure, "generic_cinematic_style_stacking")
        trace(
            "cinematic_visual_design",
            "CinematicIntentIR.unresolved_state",
            "CinematicIntentIR.composition",
            "CinematicIntentIR.visual_density",
        )

    unresolved_state_terms = (
        "未解决状态", "不可解决状态", "人物只是站着", "只是摆拍", "画面没有事件", "没有故事钩子", "没有剧情缺口",
        "只有情绪没有动作", "只有氛围没有事件",
    )
    if _contains_any(text, unresolved_state_terms):
        add(dramatic, "cinematic_visual_design")
        add(relation, "viewer_to_screen_information")
        trace("unresolved_state_visualization", "CinematicIntentIR.unresolved_state", "ShotPlanIR.dramatic_function")

    composition_terms = (
        "构图", "机位", "摄影机位置", "镜头构图", "摄影机为什么", "负空间", "前景遮挡",
    )
    relation_pressure_terms = ("空间压力", "关系压力", "观看立场", "画面关系", "人物和空间")
    composition_problem_terms = (
        "构图没有理由", "构图没理由", "机位没有理由", "机位没理由", "构图漂亮但没意思", "像摆拍", "人物和空间没关系",
        "没有空间压力", "没有关系压力", "随机构图", "套构图模板",
    )
    if (
        _contains_any(text, composition_terms)
        or _contains_any(text, relation_pressure_terms)
        or _contains_any(text, composition_problem_terms)
    ):
        add(dramatic, "cinematic_visual_design")
        add(spatial, "motivated_composition")
        if _contains_any(text, relation_pressure_terms) or _contains_any(text, composition_problem_terms):
            add(relation, "relation_pressure")
        if _contains_any(text, composition_problem_terms):
            add(failure, "composition_without_pressure")
        trace(
            "relation_pressure_composition",
            "BlockingIR.power_center",
            "CinematicIntentIR.relation_pressure",
            "CinematicIntentIR.composition",
        )

    attention_terms = (
        "视线流量", "注意流", "注意力", "观众第一眼", "观众看哪里", "看哪里", "注意落点", "视线入口", "视线落点",
        "注意力交接", "attention handoff", "cutaway", "切回来", "空位揭示", "寻找原位置",
    )
    attention_problem_terms = (
        "视线乱", "注意力乱", "视线断", "注意力断", "没有落点", "没落点", "不知道看哪里", "切回来找不到", "注意力跑掉",
        "揭示没有冲击", "空位不明显",
    )
    if _contains_any(text, attention_terms) or _contains_any(text, attention_problem_terms):
        add(dramatic, "attention_design")
        add(relation, "viewer_to_screen_information")
        add(spatial, "attention_path")
        if _contains_any(text, attention_problem_terms):
            add(failure, "attention_flow_break")
        trace(
            "attentional_flow",
            "CinematicIntentIR.attention_flow",
            "CinematicIntentIR.attention_handoff",
            "TransitionContract.attention_handoff",
        )

    color_terms = ("色彩", "调色", "综合色", "色温", "颜色来源", "色彩命题", "光色", "强调色", "色域")
    color_problem_terms = (
        "像滤镜", "像统一滤镜", "统一滤镜", "滤镜感", "直接染色", "统一染色", "全局滤镜", "颜色没有来源", "色彩没有来源", "调色太滤镜",
    )
    if _contains_any(text, color_terms) or _contains_any(text, color_problem_terms):
        add(dramatic, "look_design")
        add(spatial, "motivated_light_color")
        if _contains_any(text, color_problem_terms):
            add(failure, "color_as_filter")
        trace(
            "color_thesis",
            "WorldStateIR.light_sources",
            "CinematicIntentIR.color_intent",
            "VisibleIR.lighting_evidence",
            "VisibleIR.material_evidence",
        )

    density_problem_terms = (
        "太脏", "画面脏", "纹理太多", "高频纹理", "噪点太多", "细节太多", "信息太满", "画面太满", "到处都很锐",
        "全画面锐利", "细节抢戏", "纹理抢戏", "过度锐化", "高频脏噪点",
    )
    density_terms = ("视觉密度", "信息密度", "细节预算", "高光预算", "视觉层级", "主次层级")
    if _contains_any(text, density_terms) or _contains_any(text, density_problem_terms):
        add(dramatic, "visual_hierarchy")
        add(spatial, "detail_hierarchy")
        if _contains_any(text, density_problem_terms):
            add(failure, "visual_density_overload")
        trace(
            "visual_density_budget",
            "CinematicIntentIR.visual_density",
            "VisibleIR.visual_hierarchy_evidence",
        )

    reference_terms = ("参考图", "参考素材", "动作参考", "构图参考", "风格参考", "白模", "clay", "previs")
    reference_problem_terms = (
        "参考图污染", "参考素材污染", "纹理污染", "带入错误纹理", "带入材质", "带入光线", "带入风格", "参考图太脏",
        "动作参考太脏", "白模避免污染", "参考图抢权重", "参考图影响画质",
    )
    if _contains_any(text, reference_terms) or _contains_any(text, reference_problem_terms):
        add(dramatic, "reference_control")
        add(relation, "reference_to_generation")
        add(spatial, "reference_responsibility_split")
        if _contains_any(text, reference_problem_terms):
            add(failure, "reference_appearance_contamination")
        trace(
            "reference_signal_decoupling",
            "CinematicIntentIR.reference_signal_roles",
            "VisibleIR.reference_leak_evidence",
            "ModelAdapter.reference_signal_rule",
        )

    template_problem_terms = (
        "镜头都一样", "构图都一样", "总是同一种构图", "总是同一个机位", "重复机位", "套模板", "模板化构图", "构图套路",
        "每次都一样", "镜头套路化",
    )
    if _contains_any(text, template_problem_terms):
        add(dramatic, "shot_variation")
        add(failure, "template_composition_repetition")
        trace(
            "anti_template_composition",
            "CinematicIntentIR.anti_template_signature",
            "ShotPlanIR.sequence_function_signature",
            "ShotPlanIR.prior_function_overlap",
        )

    capture_terms = (
        "35mm", "16mm", "65mm", "胶片", "kodak", "柯达", "minidv", "mini dv", "监控画面", "旧广播", "转拍", "鱼眼",
        "成像介质", "capture substrate",
    )
    capture_problem_terms = (
        "乱加胶片", "为了电影感加胶片", "为了电影感用35mm", "没有成像理由", "没成像理由", "成像介质没理由", "只是为了高级感",
        "无动机鱼眼", "无理由监控",
    )
    if _contains_any(text, capture_terms):
        add(dramatic, "look_design")
        add(spatial, "capture_substrate")
        if _contains_any(text, capture_problem_terms):
            add(failure, "unmotivated_capture_style")
        trace("motivated_capture_substrate", "CinematicIntentIR.capture_intent", "VisibleIR.camera_fields")
    elif _contains_any(text, capture_problem_terms):
        add(dramatic, "look_design")
        add(spatial, "capture_substrate")
        add(failure, "unmotivated_capture_style")
        trace("motivated_capture_substrate", "CinematicIntentIR.capture_intent", "VisibleIR.camera_fields")

    if has_pursuit:
        add(dramatic, "pursuit")
        add(spatial, "pursuit")
        trace("pursuit_action", "EventGraphIR.action", "BlockingIR.movement_paths")
    if has_escape:
        add(dramatic, "escape")
        add(spatial, "escape")
        trace("escape_action", "EventGraphIR.action", "BlockingIR.approach_or_retreat")

    target_relation_present = False
    if gaze_target_evidence:
        target_relation_present = True
        add(relation, "gaze_to_target")
        add(failure, "gaze_target_spatial_binding_fail")
    if facing_target_evidence:
        target_relation_present = True
        add(relation, "facing_to_target")
        add(failure, "body_orientation_target_fail")
    if kneel_target_evidence:
        target_relation_present = True
        add(relation, "kneeling_to_target")
        add(spatial, "kneeling_to_target", "body_orientation")
        add(failure, "body_orientation_target_fail")
    if pursuit_target_evidence:
        target_relation_present = True
        add(relation, "pursuit_to_target")
        add(spatial, "body_orientation")
    if escape_source_evidence:
        target_relation_present = True
        add(relation, "escape_from_target")
        add(spatial, "body_orientation")
    if occlusion_target_evidence:
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
        "CinematicIntentIR": {
            "fields": {
                "unresolved_state", "viewer_position", "relation_pressure", "attention_flow", "composition",
                "color_intent", "capture_intent", "visual_density", "reference_signal_roles",
                "anti_template_signature", "attention_handoff",
            }
        },
        "VisibleIR": {
            "entity_fields": {"relative_position", "body_orientation", "gaze_target", "current_action", "support_or_contact"},
            "environment_fields": {
                "environmental_response", "canonical_background_evidence", "visual_hierarchy_evidence", "reference_leak_evidence",
            },
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
