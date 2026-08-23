from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FINAL_CI = r'''name: Learning Smart Recall

on:
  pull_request:
    paths:
      - '10_运行时/learning_recall_index.yaml'
      - '10_运行时/learning_application_gate.yaml'
      - '10_运行时/director_route_index.yaml'
      - '10_运行时/read_sets.yaml'
      - '10_运行时/write_routes.yaml'
      - '08_系统学习/**'
      - '11_验收/learning_application_gate_regression_cases.yaml'
      - '11_验收/golden_prompt_cases.yaml'
      - 'tools/learning_retriever/**'
      - '.github/workflows/learning-recall.yml'
  push:
    paths:
      - '10_运行时/learning_recall_index.yaml'
      - '10_运行时/learning_application_gate.yaml'
      - '10_运行时/director_route_index.yaml'
      - '10_运行时/read_sets.yaml'
      - '10_运行时/write_routes.yaml'
      - '08_系统学习/**'
      - '11_验收/learning_application_gate_regression_cases.yaml'
      - '11_验收/golden_prompt_cases.yaml'
      - 'tools/learning_retriever/**'
      - '.github/workflows/learning-recall.yml'

jobs:
  learning-recall:
    name: ${{ matrix.os }}-py313-smart-recall-regression
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    defaults:
      run:
        working-directory: tools/learning_retriever
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: python -m pip install -r requirements.txt
      - name: Parse project YAML
        run: python -c "from pathlib import Path; import yaml; [yaml.safe_load(p.read_text(encoding='utf-8')) for p in Path('../..').rglob('*.yaml')]; print('YAML_PARSE=PASS')"
      - name: Validate compact recall index
        run: python -m learning_retriever.cli --project-root ../.. --validate-index
      - name: Run retrieval regression
        run: python -m unittest discover -s tests -v
'''


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"anchor not found in {path}: {old[:120]!r}")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def insert_before_once(path: Path, anchor: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if block.strip() in text:
        return
    if anchor not in text:
        raise RuntimeError(f"insert anchor not found in {path}: {anchor[:120]!r}")
    text = text.replace(anchor, block + anchor, 1)
    path.write_text(text, encoding="utf-8")


def append_once(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n" + block.strip() + "\n", encoding="utf-8")


def write_final_ci() -> None:
    p = ROOT / ".github/workflows/learning-recall.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(FINAL_CI, encoding="utf-8")


def patch_project_index() -> None:
    p = ROOT / "PROJECT_INDEX.yaml"
    replace_once(
        p,
        "  director_learning_application_gate_required: true\n",
        "  director_learning_application_gate_required: true\n  director_learning_smart_recall_required: true\n",
    )
    replace_once(
        p,
        "  learning_application_gate: 10_运行时/learning_application_gate.yaml\n",
        "  learning_application_gate: 10_运行时/learning_application_gate.yaml\n  learning_recall_index: 10_运行时/learning_recall_index.yaml\n",
    )
    replace_once(
        p,
        "  10_运行时/learning_application_gate.yaml: github_verified\n",
        "  10_运行时/learning_application_gate.yaml: github_verified\n  10_运行时/learning_recall_index.yaml: github_verified\n",
    )


def patch_read_sets() -> None:
    p = ROOT / "10_运行时/read_sets.yaml"
    replace_once(
        p,
        "      - learning_application_gate#pre_directing_gate+pre_output_gate\n",
        "      - learning_application_gate#pre_directing_gate+pre_output_gate\n      - learning_recall_index#compact_router_metadata_only\n",
    )
    replace_once(
        p,
        "  directing_learning_application_gate_required: true\n",
        "  directing_learning_application_gate_required: true\n  directing_learning_smart_recall_required: true\n  learning_recall_top_k_expansion_only: true\n",
    )


def patch_route_index() -> None:
    p = ROOT / "10_运行时/director_route_index.yaml"
    block = '''  - id: TARGET_ORIENTED_SPATIAL_BINDING
    symptoms:
      - gaze target relation
      - 视线看向明确目标
      - 面向明确目标
      - 朝目标下跪
      - kneeling-to-target
      - pursuit target relation
      - 追逐目标
      - escape from target
      - 逃离目标
      - blocking 与目标空间关系
      - occlusion 与目标空间关系
      - camera-side 与目标冲突
      - action-end orientation 错误
      - 人物看向或身体朝向与剧情目标位置不一致
      - 参考图展示构图与剧情目标朝向冲突
    maturity: candidate
    mandatory_reads:
      - 08_系统学习/导演反馈学习案例.yaml#CROWD-GAZE-BODY-CAMERA-BINDING-001
    mandatory_scans:
      - target_world_position
      - gaze_target
      - body_orientation
      - kneeling_to_target
      - pursuit_escape_vector
      - blocking_and_occlusion
      - camera_side
      - action_end_orientation
      - reference_composition_conflict
    candidate_axes:
      - explicit_target_orientation_contract
      - rear_or_three_quarter_rear_camera_when_target_is_ahead
      - target_side_camera_only_when_story_relation_supports_it
      - preserve_target_facing_through_action
      - explicit_orientation_change_event
      - reference_composition_override_when_story_relation_is_material

'''
    insert_before_once(p, "  - id: SPACE_CONTINUITY_RISK\n", block)


def patch_learning_gate() -> None:
    p = ROOT / "10_运行时/learning_application_gate.yaml"
    replace_once(p, 'schema_version: "1.0"\n', 'schema_version: "1.1"\n')
    replace_once(
        p,
        '  evidence_index: "09_资料证据/学习应用与冲突裁决证据索引.md"\n',
        '  evidence_index: "09_资料证据/学习应用与冲突裁决证据索引.md"\n  learning_recall_index: "10_运行时/learning_recall_index.yaml"\n  learning_retriever: "tools/learning_retriever/"\n',
    )
    replace_once(
        p,
        "  media_claim_without_actual_media_inspection_forbidden: true\n",
        "  media_claim_without_actual_media_inspection_forbidden: true\n  compact_index_before_full_learning_library: true\n  embedding_candidate_expansion_cannot_bypass_gates: true\n  mandatory_route_recall_missing_is_gate_failure: true\n  retrieval_receipt_required_before_pre_output_pass: true\n",
    )
    old_steps = '''  steps:
    - "读取当前 work item / 剧情 / 连续性 / 相关角色场景与模型版本"
    - "召回与当前导演功能、症状、模型版本和失败模式相关的学习、Golden Cases、真实生成反馈与回归"
    - "把召回内容按 L0-L5、scope、maturity、model/version、failure conditions 分类"
    - "剔除已过期的 EPISODIC_WORK_ITEM / SCENE_LOCAL 表面限制，保留仍在当前 scope 内的 LOCK"
    - "同时检索反例、冲突、superseded、deprecated、needs_revalidation 记录，禁止只召回支持证据"
    - "运行 conflict_model，形成 ApplicableLearningSet"
    - "若存在 material unresolved conflict，先向用户提出最小必要问题；否则继续导演"
'''
    new_steps = '''  steps:
    - "Task feature extraction：从当前 work item / 剧情 / 连续性 / 角色 / 场景 / 模型版本中提取 dramatic_function、failure_mechanism、relation_type、spatial/action、scene/character context、model/version、aliases 与 camera/performance/sound 特征"
    - "Hard route：先运行 director_route_index；命中 mandatory_reads 的学习案例必须进入 mandatory recall，不得被 Top-K、表面相似度或 embedding 候选挤掉"
    - "Semantic recall：先读 compact learning_recall_index，只用路由元数据按机制优先加权召回，不全文加载学习库"
    - "Scope / maturity / model / conflict filter：剔除过期 EPISODIC_WORK_ITEM / SCENE_LOCAL、deprecated、版本不匹配经验；candidate 只作候选/假设；同时保留反例与冲突"
    - "ApplicableLearningSet：把通过过滤的 hard invariants、live locks、director intents、causal mechanisms、contextual policies、model lessons、failure modes、counterexamples 与 open hypotheses 分类"
    - "Top-K expansion：只展开命中的 Top-K canonical case 正文；完整知识 authority 仍在原 canonical，不复制进 recall index"
    - "Prompt compilation：现有 AI电影系统只使用 ApplicableLearningSet 与命中的 canonical payload 编译执行稿"
    - "Retrieval receipt：记录 hard routes、mandatory cases、score components、selected refs、excluded reasons、filters、conflicts、Top-K 与 mandatory_recall_satisfied"
    - "Pre-output gate：receipt 不完整、mandatory recall missing 或 material unresolved conflict 时必须 FAIL 并自修订/最小必要提问，不得交付已知坏稿"
'''
    replace_once(p, old_steps, new_steps)
    smart_runtime = '''smart_recall_runtime:
  id: LEARNING-SMART-RECALL-V1
  index: 10_运行时/learning_recall_index.yaml
  executable: tools/learning_retriever/
  index_role: compact_derived_router_metadata_only
  authority_rule: "recall index 只保存路由元数据；完整学习规则、证据、边界与成熟度仍以 authority_ref 指向的 canonical case 为准"
  fixed_flow:
    - task_feature_extraction
    - hard_route
    - semantic_recall
    - scope_maturity_model_conflict_filter
    - ApplicableLearningSet
    - prompt_compilation
    - retrieval_receipt
    - pre_output_gate
  ranking_priority:
    - hard_canonical
    - failure_mechanism
    - dramatic_function
    - spatial_action_relation
    - character_mechanism
    - model_version
    - camera_performance_sound
    - surface_similarity
  top_k_policy:
    compact_index_first: true
    expand_full_case_only_after_selection: true
    full_learning_library_context_injection_default: false
  embedding_future_policy:
    may_expand_candidate_pool: true
    may_bypass_authority_scope_maturity_model_conflict_gates: false
    may_satisfy_missing_mandatory_recall: false
  fail_closed:
    - mandatory_route_case_missing
    - dangling_authority_ref
    - unresolved_material_conflict
    - incomplete_retrieval_receipt

'''
    insert_before_once(p, "pre_output_gate:\n", smart_runtime)
    replace_once(
        p,
        '    - "若结论依赖用户提供的真实媒体，media_evidence_analysis_gate 是否已经满足"\n',
        '    - "若结论依赖用户提供的真实媒体，media_evidence_analysis_gate 是否已经满足"\n    - "Learning Smart Recall retrieval receipt 是否完整，且所有 hard-route mandatory recall 均已命中并展开所需 canonical case"\n',
    )


def patch_write_routes() -> None:
    p = ROOT / "10_运行时/write_routes.yaml"
    replace_once(
        p,
        "  director_feedback_learning_case: 08_系统学习/导演反馈学习案例.yaml\n",
        "  director_feedback_learning_case: 08_系统学习/导演反馈学习案例.yaml\n  learning_recall_index: 10_运行时/learning_recall_index.yaml\n",
    )
    replace_once(
        p,
        "canonical_learning_gate:\n  principle: maturity_controls_promotion_not_registration\n",
        "canonical_learning_gate:\n  principle: maturity_controls_promotion_not_registration\n  recall_index_is_derived_router_metadata_not_authority: true\n",
    )


def patch_regressions() -> None:
    p = ROOT / "11_验收/learning_application_gate_regression_cases.yaml"
    block = '''
  - id: LAG-REG-015-SMART-RECALL-POSITIVE-TARGET-BINDING
    title: "明确目标的视线/身体/下跪/机位关系必须召回空间绑定案例"
    setup:
      hard_route: TARGET_ORIENTED_SPATIAL_BINDING
      task_features:
        dramatic_function: [worship]
        relation_type: [kneeling_to_target]
        spatial_action_features: [target_world_position, gaze_direction, body_orientation, camera_side, action_end_orientation]
    must_retrieve:
      learning_case: CROWD-GAZE-BODY-CAMERA-BINDING-001
    expected:
      mandatory_recall_satisfied: true
      receipt_complete: true

  - id: LAG-REG-016-SMART-RECALL-NEGATIVE-TARGET-BINDING
    title: "只有抽象抬头且没有可定位剧情目标时不得机械召回目标绑定规则"
    setup:
      task_features: [abstract_upward_gaze, no_locatable_target]
      surface_words: [仰头, 看上方]
    expected:
      CROWD_GAZE_BODY_CAMERA_BINDING_forced: false
      negative_retrieval_example_applied: true

  - id: LAG-REG-017-SMART-RECALL-FALSE-POSITIVE-SURFACE
    title: "表面同为群众/广场不得压过机制不匹配"
    setup:
      surface_similarity: [群众, 广场, 圣女]
      actual_function: unrelated_background_establishing
      failure_mechanism: none_target_oriented
    expected:
      surface_only_case_must_not_outrank_mechanism_match: true

  - id: LAG-REG-018-SMART-RECALL-FALSE-NEGATIVE-ALIAS
    title: "不使用原案例字面词仍应通过关系别名命中"
    setup:
      aliases: [朝目标下跪]
      relation_type: [kneeling_to_target]
      spatial_action_features: [action_end_orientation]
    must_retrieve:
      learning_case: CROWD-GAZE-BODY-CAMERA-BINDING-001
    expected:
      false_negative: false

  - id: LAG-REG-019-SMART-RECALL-EXPIRED-SCENE-LOCAL
    title: "旧 scene-local 表面经验离开作用域后必须过滤"
    setup:
      lesson_scope: SCENE_LOCAL
      lesson_scene: OLD-SCENE
      current_scene: NEW-SCENE
    expected:
      injected_as_applicable_lock: false
      exclusion_reason: expired_scene_local_scope

  - id: LAG-REG-020-SMART-RECALL-MODEL-MISMATCH
    title: "C-DANCE 2.5 exclusive 模型行为不得直接注入其他模型"
    setup:
      lesson: CD25-KAIM-WINDOW-AB-20260815
      lesson_model: Seedance 2.5
      current_model: MiniMax H3
    expected:
      applied_as_model_lesson: false
      exclusion_reason: model_version_mismatch

  - id: LAG-REG-021-SMART-RECALL-CONFLICT-FAIL-CLOSED
    title: "命中 material unresolved learning conflict 必须 fail closed"
    setup:
      conflict_type: TRUE_CONTRADICTION
      material: true
      resolved: false
    expected:
      retrieval_status: FAIL
      prompt_compilation_allowed: false
      arbitrary_latest_wins: false

  - id: LAG-REG-022-SMART-RECALL-MANDATORY-MISSING-FAIL
    title: "hard route mandatory case 缺失或悬空不得继续导演"
    setup:
      hard_route: TARGET_ORIENTED_SPATIAL_BINDING
      mandatory_case: CROWD-GAZE-BODY-CAMERA-BINDING-001
      simulated_index_state: missing_or_dangling
    expected:
      retrieval_status: FAIL
      mandatory_recall_satisfied: false
      prompt_compilation_allowed: false
      pre_output_gate_must_fail: true
'''
    append_once(p, "LAG-REG-015-SMART-RECALL-POSITIVE-TARGET-BINDING", block)


def main() -> None:
    patch_project_index()
    patch_read_sets()
    patch_route_index()
    patch_learning_gate()
    patch_write_routes()
    patch_regressions()
    write_final_ci()
    bootstrap_workflow = ROOT / ".github/workflows/learning-recall-bootstrap.yml"
    if bootstrap_workflow.exists():
        bootstrap_workflow.unlink()
    this_file = Path(__file__)
    if this_file.exists():
        this_file.unlink()


if __name__ == "__main__":
    main()
