from learning_retriever.feature_compiler import compile_director_features


def test_different_surface_same_mechanism_crowd():
    a = compile_director_features("圣女布道时群众看向教会")
    b = compile_director_features("灾民等待救济时人群观察统治者")
    assert "crowd_attention_shift" in a.spatial_action_features
    assert "crowd_attention_shift" in b.spatial_action_features
    assert "crowd_to_institution" in a.relation_type
    assert "crowd_to_institution" in b.relation_type


def test_target_binding_mechanism_cross_character_scene():
    result = compile_director_features("角色下跪并面向目标，镜头保持目标关系")
    assert "body_orientation" in result.spatial_action_features
    assert "gaze_target_spatial_binding_fail" in result.failure_mechanism


def test_compiler_is_not_learning_authority():
    result = compile_director_features("普通对白场景")
    assert not hasattr(result, "learning_rules")
