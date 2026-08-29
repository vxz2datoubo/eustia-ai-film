from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text, old, new, path):
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {count}: {old[:80]!r}")
    return text.replace(old, new, 1)


# 1) Canonical runtime entrypoint.
runtime_path = "tools/learning_retriever/learning_retriever/runtime.py"
runtime = '''"""Canonical natural-language directing entrypoint for Learning Smart Recall.

Continuation-style requests first pass the Active Work Item Resolution Gate.
After identity/freshness binding, flow continues as Director Feature Compiler ->
director_route_index hard route -> existing LearningRetriever semantic recall.
LearningRetriever remains retrieval authority and work-item resolution does not
become story, continuity, or learning authority.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .active_work_item import ActiveWorkItemResolutionError, resolve_work_item
from .feature_compiler import compile_retrieval_task
from .retriever import LearningRetriever


class DirectorLearningRuntime:
    """Bind directing requests to work-item identity and existing recall runtime."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.retriever = LearningRetriever(self.project_root)

    def retrieve(
        self,
        description: str,
        *,
        task_id: str = "UNSPECIFIED_TASK",
        base_task: dict[str, Any] | None = None,
        work_item_context: dict[str, Any] | None = None,
        top_k: int | None = None,
        expand: bool = False,
    ) -> dict[str, Any]:
        resolution = resolve_work_item(
            description,
            project_root=self.project_root,
            context=work_item_context,
        )

        merged_base = dict(base_task or {})
        if resolution.resolved_work_item_id:
            existing = str(merged_base.get("work_item_id") or "").strip()
            if existing and existing != resolution.resolved_work_item_id:
                raise ActiveWorkItemResolutionError(
                    "WORK_ITEM_INPUT_SCOPE_MISMATCH",
                    details={
                        "resolved_work_item_id": resolution.resolved_work_item_id,
                        "base_task_work_item_id": existing,
                    },
                )
            merged_base["work_item_id"] = resolution.resolved_work_item_id

        task = compile_retrieval_task(
            description,
            task_id=task_id,
            base_task=merged_base,
            route_data=self.retriever.routes,
            strict=True,
        )
        result = self.retriever.retrieve(task, top_k=top_k, expand=expand, fail_closed=True)
        result["canonical_runtime_receipt"] = {
            "entrypoint": "DirectorLearningRuntime.retrieve",
            "flow": [
                "active_work_item_resolution",
                "director_feature_compiler",
                "hard_route",
                "semantic_recall",
            ],
            "active_work_item_gate_invoked": True,
            "active_work_item_resolution": resolution.as_dict(),
            "compiler_invoked": True,
            "work_item_resolution_authority": "10_运行时/active_work_item_resolution_gate.yaml",
            "route_authority": "10_运行时/director_route_index.yaml",
            "retriever_authority": "tools/learning_retriever/learning_retriever/retriever.py",
            "hard_routes": list(task.get("hard_routes") or []),
            "feature_compiler_receipt": dict(task.get("feature_compiler_receipt") or {}),
        }
        return result
'''
write(runtime_path, runtime)

# 2) Package exports.
init_path = "tools/learning_retriever/learning_retriever/__init__.py"
init_text = '''from .active_work_item import (
    ActiveWorkItemResolutionError,
    WorkItemResolution,
    apply_constraint_ledger,
    is_continuation_request,
    load_active_work_item_state,
    resolve_work_item,
    validate_output_work_item,
    validate_state_transition,
)
from .feature_compiler import (
    DirectorFeatures,
    FeatureCompilationError,
    compile_director_features,
    compile_retrieval_task,
    validate_semantic_dependencies,
)
from .retriever import LearningRetriever, RetrievalGateError, validate_index
from .route_resolver import RouteResolutionError, resolve_hard_routes
from .runtime import DirectorLearningRuntime

__all__ = [
    "ActiveWorkItemResolutionError",
    "DirectorFeatures",
    "DirectorLearningRuntime",
    "FeatureCompilationError",
    "LearningRetriever",
    "RetrievalGateError",
    "RouteResolutionError",
    "WorkItemResolution",
    "apply_constraint_ledger",
    "compile_director_features",
    "compile_retrieval_task",
    "is_continuation_request",
    "load_active_work_item_state",
    "resolve_hard_routes",
    "resolve_work_item",
    "validate_index",
    "validate_output_work_item",
    "validate_semantic_dependencies",
    "validate_state_transition",
]
'''
write(init_path, init_text)

# 3) CLI: structured work-item context input and gate error stage.
cli_path = "tools/learning_retriever/learning_retriever/cli.py"
cli = read(cli_path)
cli = replace_once(
    cli,
    "from .feature_compiler import FeatureCompilationError, validate_semantic_dependencies\n",
    "from .active_work_item import ActiveWorkItemResolutionError\nfrom .feature_compiler import FeatureCompilationError, validate_semantic_dependencies\n",
    cli_path,
)
cli = replace_once(
    cli,
    '    parser.add_argument("--task-id", default="UNSPECIFIED_TASK")\n',
    '    parser.add_argument("--task-id", default="UNSPECIFIED_TASK")\n    parser.add_argument("--work-item-context", help="JSON orchestration receipt for continuation work-item freshness/explicit binding")\n',
    cli_path,
)
cli = replace_once(
    cli,
    "    try:\n        if args.description:\n",
    "    work_item_context = None\n    if args.work_item_context:\n        work_item_context = json.loads(Path(args.work_item_context).read_text(encoding=\"utf-8\"))\n\n    try:\n        if args.description:\n",
    cli_path,
)
cli = replace_once(
    cli,
    "                task_id=args.task_id,\n                top_k=args.top_k,\n",
    "                task_id=args.task_id,\n                work_item_context=work_item_context,\n                top_k=args.top_k,\n",
    cli_path,
)
cli = replace_once(
    cli,
    "                    base_task=raw_task,\n                    top_k=args.top_k,\n",
    "                    base_task=raw_task,\n                    work_item_context=work_item_context,\n                    top_k=args.top_k,\n",
    cli_path,
)
cli = replace_once(
    cli,
    "    except FeatureCompilationError as exc:\n",
    "    except ActiveWorkItemResolutionError as exc:\n        print(json.dumps({\"status\": \"FAIL\", \"stage\": \"active_work_item_resolution\", \"error\": exc.code, \"details\": exc.details}, ensure_ascii=False, indent=2))\n        return 2\n    except FeatureCompilationError as exc:\n",
    cli_path,
)
write(cli_path, cli)

# 4) Feature compiler contract: work-item gate precedes compiler.
path = "10_运行时/director_feature_compiler.yaml"
text = read(path)
text = replace_once(
    text,
    "  natural_language_flow:\n    - director_feature_compiler\n    - hard_route_from_director_route_index\n    - semantic_recall_from_learning_recall_index\n",
    "  precondition_gate: 10_运行时/active_work_item_resolution_gate.yaml\n  natural_language_flow:\n    - active_work_item_resolution_when_continuation_or_referent_binding_is_required\n    - director_feature_compiler\n    - hard_route_from_director_route_index\n    - semantic_recall_from_learning_recall_index\n",
    path,
)
text = replace_once(
    text,
    "  natural_language_bypass_forbidden: true\n",
    "  natural_language_bypass_forbidden: true\n  unresolved_continuation_must_not_enter_compiler: true\n",
    path,
)
write(path, text)

# 5) Read set: resolve identity before targeted canonical reads and feature compilation.
path = "10_运行时/read_sets.yaml"
text = read(path)
text = replace_once(
    text,
    "    always:\n      - PROJECT_INDEX.yaml\n      - AI电影系统#relevant_sections_only\n      - 当前改编剧本#hit_range\n      - 连续性与当前生产状态#relevant_work_item\n      - director_feature_compiler#runtime_binding+fail_closed\n",
    "    always:\n      - PROJECT_INDEX.yaml\n      - active_work_item_resolution_gate#continuation_detection+resolution+freshness_gate\n      - 连续性与当前生产状态#ACTIVE_WORK_ITEM_STATE_first\n      - AI电影系统#relevant_sections_only\n      - 当前改编剧本#resolved_work_item_hit_range\n      - 连续性与当前生产状态#resolved_work_item_details_only\n      - director_feature_compiler#runtime_binding+fail_closed\n",
    path,
)
if "directing_must_resolve_active_work_item_before_feature_compiler" not in text:
    marker = "rules:\n"
    if marker not in text:
        text += "\nrules:\n"
    text = text.replace(
        marker,
        marker + "  directing_must_resolve_active_work_item_before_feature_compiler: true\n  unresolved_continuation_must_fail_closed: true\n  active_work_item_pointer_cannot_override_story_map_asset_authority: true\n",
        1,
    )
write(path, text)

# 6) Source authority explicit runtime identity boundary.
path = "10_运行时/source_authority.yaml"
text = read(path)
text = replace_once(
    text,
    "  migration_cutover_requires_fetch_verify: true\n",
    "  migration_cutover_requires_fetch_verify: true\n  continuation_referent_must_be_resolved_before_directing: true\n  active_work_item_snapshot_is_current_production_projection_not_story_authority: true\n  source_issue_revision_trace_cannot_override_screenplay_map_asset_authority: true\n",
    path,
)
write(path, text)

# 7) Learning gate sequencing.
path = "10_运行时/learning_application_gate.yaml"
text = read(path)
text = replace_once(
    text,
    '  director_feature_compiler: "10_运行时/director_feature_compiler.yaml"\n',
    '  active_work_item_resolution_gate: "10_运行时/active_work_item_resolution_gate.yaml"\n  director_feature_compiler: "10_运行时/director_feature_compiler.yaml"\n',
    path,
)
text = replace_once(
    text,
    '  steps:\n    - "Director Feature Compiler：自然语言导演任务必须先经 PROJECT_INDEX 注册的 director_feature_compiler，编译 dramatic_function、failure_mechanism、relation_type、spatial/action；缺失 compiler 或无法安全编译时 fail closed"\n',
    '  steps:\n    - "Active Work Item Resolution：含上次/继续/那30秒/刚才/下一镜等 continuation 指代的任务，必须先解析 resolved_work_item_id 并验证 checkpoint freshness；未解析或 stale 时 fail closed，不得进入 Director Feature Compiler"\n    - "Director Feature Compiler：完成必要的 work-item identity binding 后，自然语言导演任务必须经 PROJECT_INDEX 注册的 director_feature_compiler，编译 dramatic_function、failure_mechanism、relation_type、spatial/action；缺失 compiler 或无法安全编译时 fail closed"\n',
    path,
)
write(path, text)

# 8) Write route: explicit checkpoint projection and receipt.
path = "10_运行时/write_routes.yaml"
text = read(path)
text = replace_once(
    text,
    "  revision_checkpoint_current_state: 07_连续性与生产状态/连续性与当前生产状态.md\n",
    "  revision_checkpoint_current_state: 07_连续性与生产状态/连续性与当前生产状态.md\n  active_work_item_current_state: 07_连续性与生产状态/连续性与当前生产状态.md#ACTIVE_WORK_ITEM_STATE\n",
    path,
)
if "active_work_item_checkpoint_transaction:" not in text:
    text += '''\n\nactive_work_item_checkpoint_transaction:\n  trigger: revision_checkpoint_or_work_item_switch\n  target: 07_连续性与生产状态/连续性与当前生产状态.md#ACTIVE_WORK_ITEM_STATE\n  protocol:\n    - fetch_current_continuity\n    - reconcile_source_revision_events\n    - apply_constraint_ledger\n    - update_active_work_item_snapshot\n    - commit_serially\n    - fetch_verify\n    - write_canonical_checkpoint_receipt_to_source_issue\n  idempotency_key: work_item_id+latest_applied_checkpoint_ref\n  failure_rule: do_not_report_checkpoint_canonicalized_until_readback_verified\n'''
write(path, text)

# 9) PROJECT_INDEX registry/policies.
path = "PROJECT_INDEX.yaml"
text = read(path)
text = replace_once(
    text,
    "  director_task_must_read_project_index_first: true\n",
    "  director_task_must_read_project_index_first: true\n  active_work_item_resolution_required_for_continuation_directing: true\n  unresolved_continuation_must_fail_closed_before_feature_compiler: true\n  active_work_item_snapshot_cannot_override_story_map_asset_authority: true\n",
    path,
)
text = replace_once(
    text,
    "  director_feature_compiler: 10_运行时/director_feature_compiler.yaml\n",
    "  active_work_item_resolution_gate: 10_运行时/active_work_item_resolution_gate.yaml\n  director_feature_compiler: 10_运行时/director_feature_compiler.yaml\n",
    path,
)
text = replace_once(
    text,
    "  high_dynamic_motion_prompt_evidence: 09_资料证据/AI视频高动态动作提示证据索引.md\n",
    "  high_dynamic_motion_prompt_evidence: 09_资料证据/AI视频高动态动作提示证据索引.md\n  active_work_item_resolution_evidence: 09_资料证据/活动工作项解析与修订状态证据索引.md\n",
    path,
)
text = replace_once(
    text,
    "  regression_cases: 11_验收/director_regression_cases.yaml\n",
    "  regression_cases: 11_验收/director_regression_cases.yaml\n  active_work_item_resolution_regression_cases: 11_验收/active_work_item_resolution_regression_cases.yaml\n",
    path,
)
text = replace_once(
    text,
    "  09_资料证据/AI视频高动态动作提示证据索引.md: github_verified\n",
    "  09_资料证据/AI视频高动态动作提示证据索引.md: github_verified\n  09_资料证据/活动工作项解析与修订状态证据索引.md: github_verified\n",
    path,
)
text = replace_once(
    text,
    "  10_运行时/director_feature_compiler.yaml: github_verified\n",
    "  10_运行时/active_work_item_resolution_gate.yaml: github_verified\n  10_运行时/director_feature_compiler.yaml: github_verified\n",
    path,
)
text = replace_once(
    text,
    "  11_验收/director_regression_cases.yaml: github_verified\n",
    "  11_验收/director_regression_cases.yaml: github_verified\n  11_验收/active_work_item_resolution_regression_cases.yaml: github_verified\n",
    path,
)
write(path, text)

# 10) Continuity materialized active snapshot. Preserve old sections only as prior baseline.
path = "07_连续性与生产状态/连续性与当前生产状态.md"
text = read(path)
active_block = '''\n## ACTIVE_WORK_ITEM_STATE｜机器可读当前工作项\n\n> 运行时 continuation 解析先读本块；本块是当前生产状态的 materialized snapshot，不是剧情/地图/资产第二权威。完整 revision 证据继续留在 source Issue。\n\n<!-- ACTIVE_WORK_ITEM_STATE_BEGIN -->\n```yaml\nactive_work_item:\n  work_item_id: KAIM-SCARF-CLOTHESLINE-TRAVERSE\n  status: ACTIVE_REVISION\n  source_issue: 19\n  baseline_checkpoint_ref: "5424363511"\n  latest_applied_checkpoint_ref: "5454103847"\n  latest_evidence_ref: "5454437860"\n  story_scope_ref: 03_剧本与改编/当前改编剧本.md#凯姆高位搜索之后的屋顶横向移动/当前制作扩展\n  current_effective_state_summary: 凯姆在屋顶之间利用围巾搭过固定粗晾衣绳，从画面右向左长距离横滑；途中撞飞大量衣物，女性束身衣挂到脖颈；抵达左侧建筑双脚缓冲撞墙，女人开窗，凯姆以干冷对白把衣物罩到她头上并在reaction cutaway期间画外离开；回同一master时凯姆已经消失；最后群众继续面向钟楼，仅一名小孩注意掉落衣物。\n  locked_constraints:\n    - scarf_clothesline_geometry\n    - scarf_midpoint_single_drape_over_fixed_thick_line\n    - scarf_ends_separate_and_one_end_per_hand\n    - kaim_body_and_hands_remain_below_fixed_line\n    - scarf_and_kaim_co_translate_while_clothesline_stays_fixed\n    - screen_right_to_screen_left_side_on_traverse\n    - no_open_sky_prison_city_enclosure\n    - disappearance_reveal_return_to_same_master_with_kaim_already_absent\n  preserved_constraints:\n    - mass_laundry_collision\n    - clothes_on_chest\n    - medieval_shaping_garment_around_neck\n    - two_foot_wall_arrival_buffer\n    - adjacent_woman_opens_window\n    - kaim_line_你的衣服掉了\n    - woman_line_不是啊不是我的\n    - final_crowd_faces_bell_tower\n    - only_one_child_breaks_attention_upward\n    - kaim_skilled_efficient_dry_not_clownish\n  revoked_constraints:\n    - over_specified_setup_micro_choreography\n    - broad_strong_textual_constraint_as_default\n  experimental_constraints:\n    - sparse_directing_hard_only_material_narrative_errors\n    - standard_film_editing_terms_for_disappearance\n    - clean_white_model_motion_geometry_reference\n    - separate_motion_geometry_reference_from_appearance_style_reference\n  unresolved_failures:\n    - scarf_persistence_and_co_motion_requires_target_model_validation\n    - launch_momentum_naturalness\n    - action_reference_appearance_contamination_requires_controlled_AB\n  bound_media_or_reference_refs:\n    - current_turn_white_model_scarf_rope_reference\n    - current_turn_high_quality_city_style_reference\n    - issue19_actual_motion_reference_悬索之上的雨城骑士.png\n  current_best_ref: issue19-comment-5454103847\n  previous_work_item_id: KAIM-HIGH-SEARCH-30S\n  next_expected_action: redirect_current_30s_from_latest_effective_state\n  checkpoint_writeback_status: verified\n  writeback_verified_commit: candidate_branch_pending_review\n```\n<!-- ACTIVE_WORK_ITEM_STATE_END -->\n\n'''
anchor = "> 只记录当前有效状态，不建立平行版本。当前文件迁移后以 GitHub 固定路径持续原地维护。\n\n"
if "ACTIVE_WORK_ITEM_STATE_BEGIN" not in text:
    text = replace_once(text, anchor, anchor + active_block, path)
text = text.replace("# 2. 当前剧情位置\n", "# 2. 上一工作项基线｜KAIM-HIGH-SEARCH-30S（非当前 continuation 默认）\n", 1)
text = text.replace("# 3. 当前 30 秒镜头段锁定事件\n", "# 3. 上一工作项30秒基线事件（非当前 active work item）\n", 1)
text = text.replace("# 7. 当前镜头结束接口\n", "# 7. 上一工作项结束接口（历史基线，不得覆盖 ACTIVE_WORK_ITEM_STATE）\n", 1)
text = text.replace("# 8. 下一步制作接口\n", "# 8. 制作接口与迁移说明\n", 1)
text = text.replace("# 9. 当前提示词编译 Constraint Ledger Checkpoint｜2026-08-12\n", "# 9. 上一高位搜索提示词 Constraint Ledger Checkpoint｜2026-08-12\n", 1)
text = text.replace("last_updated: 2026-08-21", "last_updated: 2026-08-29", 1)
write(path, text)

# 11) README explanation.
path = "tools/learning_retriever/README.md"
text = read(path)
section = '''\n\n## Active Work Item Resolution Gate\n\nContinuation-style directing requests such as `上次` / `继续` / `那30秒` / `刚才那个镜头` must resolve a concrete work item before feature compilation. Runtime order is now:\n\n```text\nPROJECT_INDEX\n→ Active Work Item Resolution / freshness gate\n→ Director Feature Compiler\n→ Hard Route\n→ Semantic Recall\n```\n\nThe gate reads the machine-readable `ACTIVE_WORK_ITEM_STATE` projection in the existing continuity canonical. If the snapshot points to a source Issue, orchestration must provide a freshly verified latest structured checkpoint ref. A mismatch fails with `WORK_ITEM_CHECKPOINT_RECONCILE_REQUIRED`; inaccessible or unverified freshness fails with `WORK_ITEM_FRESHNESS_UNVERIFIED`.\n\nThis gate does not make Issue comments or the active pointer into story authority. Screenplay, character, map, formal asset and director-method authority remain unchanged. The pointer only binds which production work item the downstream system is allowed to process.\n\nCLI callers may provide the orchestration receipt with `--work-item-context <json>`.\n'''
if "## Active Work Item Resolution Gate" not in text:
    text += section
write(path, text)

# 12) Existing feature compiler regression must assert new ordering, not old exact list.
path = "tools/learning_retriever/tests/test_feature_compiler.py"
text = read(path)
text = replace_once(
    text,
    '        self.assertEqual(runtime_receipt["flow"], ["director_feature_compiler", "hard_route", "semantic_recall"])\n',
    '        self.assertEqual(runtime_receipt["flow"], ["active_work_item_resolution", "director_feature_compiler", "hard_route", "semantic_recall"])\n        self.assertTrue(runtime_receipt["active_work_item_gate_invoked"])\n        self.assertFalse(runtime_receipt["active_work_item_resolution"]["resolution_required"])\n',
    path,
)
text = replace_once(
    text,
    '        compiler_pos = next(i for i, item in enumerate(always) if item.startswith("director_feature_compiler"))\n',
    '        active_pos = next(i for i, item in enumerate(always) if item.startswith("active_work_item_resolution_gate"))\n        compiler_pos = next(i for i, item in enumerate(always) if item.startswith("director_feature_compiler"))\n',
    path,
)
text = replace_once(
    text,
    '        self.assertLess(compiler_pos, route_pos)\n',
    '        self.assertLess(active_pos, compiler_pos)\n        self.assertLess(compiler_pos, route_pos)\n',
    path,
)
write(path, text)

print("active work item wiring complete")
