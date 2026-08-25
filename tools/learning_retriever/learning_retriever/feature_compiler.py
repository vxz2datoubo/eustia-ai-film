"""Director task feature compiler for Learning Smart Recall V1.1.

This module does not store learning knowledge. It only normalizes a director
request into retrieval features consumed by the existing learning retriever.
Canonical learning payloads remain in referenced learning cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DirectorFeatures:
    dramatic_function: list[str] = field(default_factory=list)
    relation_type: list[str] = field(default_factory=list)
    spatial_action_features: list[str] = field(default_factory=list)
    failure_mechanism: list[str] = field(default_factory=list)


def _contains_any(text: str, values: tuple[str, ...]) -> bool:
    return any(value in text for value in values)


def compile_director_features(task: str) -> DirectorFeatures:
    """Compile natural language director intent into mechanism features.

    The compiler deliberately uses small deterministic semantics. It routes
    retrieval; it is not an authority and does not infer new canon.
    """
    text = task.lower()
    dramatic: list[str] = []
    relation: list[str] = []
    spatial: list[str] = []
    failure: list[str] = []

    if _contains_any(text, ("群众", "人群", "百姓", "信徒", "围观")):
        dramatic += ["crowd_reaction", "social_behavior"]
        relation += ["crowd_to_institution"]
        spatial += ["crowd_attention_shift", "heterogeneous_microreaction"]

    if _contains_any(text, ("解释", "世界观", "历史", "背景说明", "旁白")):
        dramatic += ["worldbuilding_exposition"]
        failure += ["exposition_stall"]
        relation += ["speaker_to_listener"]

    if _contains_any(text, ("下跪", "面向", "看向", "追逐", "逃跑", "目标")):
        dramatic += ["target_oriented_action"]
        spatial += [
            "locatable_target",
            "gaze_direction",
            "body_orientation",
            "blocking",
        ]
        relation += ["gaze_to_target", "facing_to_target"]
        failure += ["gaze_target_spatial_binding_fail"]

    if _contains_any(text, ("对白", "台词", "gal", "长句")):
        dramatic += ["dialogue_adaptation"]
        failure += ["written_sentence_shape_leak"]
        relation += ["speaker_to_listener"]

    if _contains_any(text, ("动作不对", "穿帮", "连续性", "保持一致", "空间")):
        spatial += ["continuity_inheritance"]
        failure += ["canonical_world_state_violation"]

    return DirectorFeatures(
        dramatic_function=sorted(set(dramatic)),
        relation_type=sorted(set(relation)),
        spatial_action_features=sorted(set(spatial)),
        failure_mechanism=sorted(set(failure)),
    )
