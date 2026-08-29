from pathlib import Path

import yaml

from learning_retriever import DirectorLearningRuntime
from learning_retriever.feature_compiler import compile_director_features


REPO_ROOT = Path(__file__).resolve().parents[3]


NEGATIVE_DYNASTY_FORMS = (
    "讲述王朝圣女跪下祈祷的历史。",
    "史书记载王朝圣女跪拜仪式。",
    "描写前朝圣女跪下祈祷。",
    "介绍本朝圣女跪拜礼仪。",
    "讲解这个朝代圣女跪下祈祷的传统。",
)

POSITIVE_DIRECTION_FORMS = (
    "群众朝她跪下。",
    "群众随后朝她跪下。",
    "随后朝她跪下。",
    "卫兵向门口跪拜。",
    "信徒们朝圣女跪拜。",
)


def test_dynasty_lexemes_with_kneeling_verbs_do_not_create_target_spatial_semantics():
    runtime = DirectorLearningRuntime(REPO_ROOT)
    for index, description in enumerate(NEGATIVE_DYNASTY_FORMS):
        compiled = compile_director_features(description, strict=False)
        assert "kneeling_to_target" not in compiled.relation_type, description
        assert "facing_to_target" not in compiled.relation_type, description
        assert "locatable_target" not in compiled.spatial_action_features, description
        result = runtime.retrieve(description, task_id=f"DIRECTION-NEG-{index}", top_k=5)
        assert "TARGET_ORIENTED_SPATIAL_BINDING" not in result["canonical_runtime_receipt"]["hard_routes"], description
        assert "TARGET_ORIENTED_SPATIAL_BINDING" not in result["retrieval_receipt"]["hard_routes"], description


def test_bounded_bare_direction_syntax_still_maps_kneeling_to_target():
    runtime = DirectorLearningRuntime(REPO_ROOT)
    for index, description in enumerate(POSITIVE_DIRECTION_FORMS):
        compiled = compile_director_features(description)
        assert "kneeling_to_target" in compiled.relation_type, description
        assert "locatable_target" in compiled.spatial_action_features, description
        result = runtime.retrieve(description, task_id=f"DIRECTION-POS-{index}", top_k=5)
        assert "TARGET_ORIENTED_SPATIAL_BINDING" in result["canonical_runtime_receipt"]["hard_routes"], description


def test_existing_body_orientation_positive_remains_unchanged():
    compiled = compile_director_features("角色身体朝圣女，保持视线与身体方向一致。")
    assert "facing_to_target" in compiled.relation_type
    assert "body_orientation" in compiled.spatial_action_features


def test_route_authority_still_owns_target_oriented_mapping():
    routes = yaml.safe_load((REPO_ROOT / "10_运行时/director_route_index.yaml").read_text(encoding="utf-8"))
    route = next(item for item in routes["routes"] if item["id"] == "TARGET_ORIENTED_SPATIAL_BINDING")
    assert "kneeling_to_target" in route["machine_triggers"]["any_of"]["relation_type"]
