from pathlib import Path


def load(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def save(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_exact(text: str, old: str, new: str, *, path: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"anchor missing in {path}: {old[:120]!r}")
    return text.replace(old, new, 1)


def insert_after(text: str, anchor: str, addition: str, *, path: str) -> str:
    if addition.strip() in text:
        return text
    if anchor not in text:
        raise RuntimeError(f"anchor missing in {path}: {anchor!r}")
    return text.replace(anchor, anchor + addition, 1)


# 1. Restore an existing PROJECT_INDEX effective-source line accidentally lost in the draft delta.
path = "PROJECT_INDEX.yaml"
text = load(path)
text = insert_after(
    text,
    "  11_验收/legacy_authority_regression_cases.yaml: github_verified\n",
    "  11_验收/canonical_migration_integrity_audit.md: github_verified\n",
    path=path,
)
save(path, text)

# 2. Wire the dedicated evidence/regression files into minimum targeted read sets.
path = "10_运行时/read_sets.yaml"
text = load(path)
text = insert_after(
    text,
    "      evidence: 官方资料与证据索引#only_if_research_or_tool_uncertain\n",
    "      cinematic_visual_grammar_evidence: Cinematic Visual Grammar外部研究与融合证据#when_cinematic_visual_grammar_route_source_boundary_or_candidate_revalidation_is_relevant\n"
    "      cinematic_visual_grammar_regression: cinematic_visual_grammar_regression_cases#when_cinematic_visual_grammar_targeted_eval_or_regression_is_relevant\n",
    path=path,
)
text = insert_after(
    text,
    "      soac_runtime: screen_observable_audible_ir_schema#when_story_to_shot_compilation_observable_audible_diagnosis_reverse_evaluation_or_compiler_test\n",
    "      cinematic_visual_grammar_evidence: Cinematic Visual Grammar外部研究与融合证据#when_cinematic_visual_grammar_research_source_boundary_or_candidate_revalidation_is_under_review\n"
    "      cinematic_visual_grammar_regression: cinematic_visual_grammar_regression_cases#when_cinematic_visual_grammar_protocol_or_transfer_behavior_is_evaluated\n",
    path=path,
)
save(path, text)

# 3. Give write_routes explicit unique destinations for this evidence and targeted regression family.
path = "10_运行时/write_routes.yaml"
text = load(path)
text = insert_after(
    text,
    "  official_research_evidence: 09_资料证据/官方资料与证据索引.md\n",
    "  cinematic_visual_grammar_research_evidence: 09_资料证据/Cinematic Visual Grammar外部研究与融合证据.md\n"
    "  cinematic_visual_grammar_regression_case: 11_验收/cinematic_visual_grammar_regression_cases.yaml\n",
    path=path,
)
save(path, text)

# 4. Correct the SOAC evidence pointer to the newly registered evidence source.
path = "10_运行时/screen_observable_audible_ir_schema.yaml"
text = load(path)
text = replace_exact(
    text,
    "  research_evidence: 09_资料证据/官方资料与证据索引.md#CINEMATIC-VISUAL-GRAMMAR-RESEARCH-001\n",
    "  research_evidence: 09_资料证据/Cinematic Visual Grammar外部研究与融合证据.md\n",
    path=path,
)
save(path, text)

# 5. Register the new method in the existing DirectorSkills invocation list instead of leaving it as an orphan chapter.
path = "01_AI电影系统/AI电影系统.md"
text = load(path)
text = replace_exact(
    text,
    "### S25-14 至 S25-22 Candidate 调用入口",
    "### S25-14 至 S25-23 Candidate 调用入口",
    path=path,
)
text = insert_after(
    text,
    "- `S25-22 / SOAC-001`：完整导演、剧情转镜头、可见/可听诊断、AI 执行编译或反向验收需要从 canonical facts 形成可检查的世界、事件、调度、镜头、Visible/Audible 与 transition 合同时调用；先读 runtime schema，再按需定向调用既有技能。\n",
    "- `S25-23 / CINEMATIC-VISUAL-GRAMMAR-001`：当 `CINEMATIC_VISUAL_GRAMMAR` 命中时，在 Blocking 成立后用 CinematicIntentIR 处理观看立场、关系压力、注意流、综合色来源、视觉密度、成像动机、参考信号职责和反套路检查；只把当前生成单位会改变像素、声音、摄影机、剪辑或参考控制的字段下发。\n",
    path=path,
)
save(path, text)

# 6. Tighten natural-language semantics: generic camera/composition discussion may invoke visual design,
#    but must not fabricate a relation-pressure relation unless pressure/viewer-position evidence exists.
path = "tools/learning_retriever/learning_retriever/feature_compiler.py"
text = load(path)
old = '''    composition_terms = (\n        "构图", "机位", "空间压力", "关系压力", "观看立场", "摄影机为什么", "画面关系", "负空间", "前景遮挡",\n    )\n    composition_problem_terms = (\n        "构图没有理由", "构图没理由", "机位没有理由", "机位没理由", "构图漂亮但没意思", "像摆拍", "人物和空间没关系",\n        "没有空间压力", "没有关系压力", "随机构图", "套构图模板",\n    )\n    if _contains_any(text, composition_terms) or _contains_any(text, composition_problem_terms):\n        add(dramatic, "cinematic_visual_design")\n        add(relation, "relation_pressure")\n        add(spatial, "motivated_composition")\n        if _contains_any(text, composition_problem_terms):\n            add(failure, "composition_without_pressure")\n        trace(\n            "relation_pressure_composition",\n            "BlockingIR.power_center",\n            "CinematicIntentIR.relation_pressure",\n            "CinematicIntentIR.composition",\n        )\n'''
new = '''    composition_terms = (\n        "构图", "机位", "摄影机位置", "镜头构图", "摄影机为什么", "负空间", "前景遮挡",\n    )\n    relation_pressure_terms = ("空间压力", "关系压力", "观看立场", "画面关系", "人物和空间")\n    composition_problem_terms = (\n        "构图没有理由", "构图没理由", "机位没有理由", "机位没理由", "构图漂亮但没意思", "像摆拍", "人物和空间没关系",\n        "没有空间压力", "没有关系压力", "随机构图", "套构图模板",\n    )\n    if (\n        _contains_any(text, composition_terms)\n        or _contains_any(text, relation_pressure_terms)\n        or _contains_any(text, composition_problem_terms)\n    ):\n        add(dramatic, "cinematic_visual_design")\n        add(spatial, "motivated_composition")\n        if _contains_any(text, relation_pressure_terms) or _contains_any(text, composition_problem_terms):\n            add(relation, "relation_pressure")\n        if _contains_any(text, composition_problem_terms):\n            add(failure, "composition_without_pressure")\n        trace(\n            "relation_pressure_composition",\n            "BlockingIR.power_center",\n            "CinematicIntentIR.relation_pressure",\n            "CinematicIntentIR.composition",\n        )\n'''
text = replace_exact(text, old, new, path=path)
save(path, text)

# 7. Extend the machine regression suite with a positive guard for ordinary camera language.
path = "11_验收/cinematic_visual_grammar_regression_cases.yaml"
text = load(path)
anchor = '''  - id: REG-CAPTURE-SUBSTRATE-POSITIVE-001\n'''
case = '''  - id: REG-COMPOSITION-CAMERA-POSITIVE-001\n    input: "固定机位拍摄，保持现有构图。"\n    expected_present:\n      dramatic_function: cinematic_visual_design\n      spatial_action_feature: motivated_composition\n    expected_absent:\n      relation_type: relation_pressure\n      failure_mechanism: composition_without_pressure\n    expected_route: CINEMATIC_VISUAL_GRAMMAR\n\n'''
if "REG-COMPOSITION-CAMERA-POSITIVE-001" not in text:
    if anchor not in text:
        raise RuntimeError(f"anchor missing in {path}: {anchor!r}")
    text = text.replace(anchor, case + anchor, 1)
save(path, text)

print("cinematic visual grammar finalizer completed")
