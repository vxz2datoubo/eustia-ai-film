from copy import deepcopy
import inspect
from pathlib import Path
import tempfile
import unittest

import yaml

from learning_retriever import DirectorLearningRuntime
from learning_retriever.active_work_item import (
    ActiveWorkItemResolutionError,
    apply_constraint_ledger,
    build_work_item_context_packet,
    is_continuation_request,
    load_active_work_item_state,
    resolve_work_item,
    validate_output_work_item,
    validate_state_transition,
    validate_work_item_context_packet,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
REGRESSION_PATH = (
    REPO_ROOT / "11_验收/active_work_item_resolution_regression_cases.yaml"
)
REGRESSIONS = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))


def _write_temp_authority(
    root: Path,
    *,
    state_overrides: dict | None = None,
    include_state: bool = True,
    include_history: bool = True,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    index = {
        "project_id": "EUSTIA_AI_FILM",
        "canonical": {
            "continuity": "07_连续性与生产状态/连续性与当前生产状态.md"
        },
    }
    (root / "PROJECT_INDEX.yaml").write_text(
        yaml.safe_dump(index, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    continuity = root / "07_连续性与生产状态/连续性与当前生产状态.md"
    continuity.parent.mkdir(parents=True, exist_ok=True)
    if not include_state:
        continuity.write_text("# no active state\n", encoding="utf-8")
        return

    state = deepcopy(load_active_work_item_state(REPO_ROOT))
    state.update(state_overrides or {})
    payload = yaml.safe_dump(
        {"active_work_item": state},
        allow_unicode=True,
        sort_keys=False,
    )
    parts = [
        "# 连续性与当前生产状态",
        "<!-- ACTIVE_WORK_ITEM_STATE_BEGIN -->",
        "```yaml",
        payload.rstrip(),
        "```",
        "<!-- ACTIVE_WORK_ITEM_STATE_END -->",
    ]
    if include_history:
        parts.extend(
            [
                "",
                "# 2. 上一工作项基线｜KAIM-HIGH-SEARCH-30S（非当前 continuation 默认）",
                "",
                "凯姆已经在攀爬楼房，爱丽丝为画外音；经过开窗妇女与菲奥奈巡查，最终登顶搜索男孩。",
                "该历史工作项不能覆盖当前 active work item。",
                "",
                "# 3. 其他内容",
            ]
        )
    continuity.write_text("\n".join(parts) + "\n", encoding="utf-8")


class ActiveWorkItemResolutionTests(unittest.TestCase):
    def test_current_continuity_exposes_machine_readable_active_state(self):
        state = load_active_work_item_state(REPO_ROOT)
        self.assertEqual(
            state["work_item_id"], "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
        )
        self.assertEqual(int(state["source_issue"]), 19)
        self.assertEqual(
            str(state["latest_applied_checkpoint_ref"]), "5454103847"
        )
        self.assertEqual(state["checkpoint_writeback_status"], "verified")
        self.assertTrue(str(state["writeback_verified_commit"]).strip())
        self.assertIn("scarf_clothesline_geometry", state["locked_constraints"])
        self.assertIn(
            "over_specified_setup_micro_choreography",
            state["revoked_constraints"],
        )

    def test_wrong_30s_regression_resolves_verified_canonical_pointer_without_provider(self):
        result = resolve_work_item(
            "重新导演上次那30秒",
            project_root=REPO_ROOT,
        )
        self.assertTrue(result.resolution_required)
        self.assertEqual(
            result.resolved_work_item_id,
            "KAIM-SCARF-CLOTHESLINE-TRAVERSE",
        )
        self.assertEqual(
            result.continuation_resolution_source,
            "active_work_item_pointer",
        )
        self.assertTrue(result.freshness_verified)
        self.assertEqual(result.gate_status, "RESOLVED_VERIFIED")
        self.assertEqual(
            result.verification_basis,
            "canonical_continuity_verified_snapshot",
        )
        self.assertTrue(result.snapshot_fingerprint)

    def test_callback_authority_surface_is_removed_from_public_api(self):
        resolve_params = inspect.signature(resolve_work_item).parameters
        runtime_params = inspect.signature(DirectorLearningRuntime).parameters
        self.assertNotIn("freshness_provider", resolve_params)
        self.assertNotIn("explicit_target_provider", resolve_params)
        self.assertNotIn("freshness_provider", runtime_params)
        self.assertNotIn("explicit_target_provider", runtime_params)

        with self.assertRaises(TypeError):
            resolve_work_item(
                "继续那30秒",
                project_root=REPO_ROOT,
                freshness_provider=lambda state: {  # type: ignore[call-arg]
                    "source_issue_accessible": True,
                    "latest_source_checkpoint_ref": "5454103847",
                },
            )

    def test_snapshot_must_have_verified_writeback_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(
                root,
                state_overrides={"checkpoint_writeback_status": "pending"},
            )
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            ):
                resolve_work_item("继续那30秒", project_root=root)

    def test_snapshot_must_have_verified_commit_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(
                root,
                state_overrides={"writeback_verified_commit": ""},
            )
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            ):
                resolve_work_item("继续那30秒", project_root=root)

    def test_project_index_must_register_continuity_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root)
            (root / "PROJECT_INDEX.yaml").write_text(
                yaml.safe_dump(
                    {
                        "project_id": "EUSTIA_AI_FILM",
                        "canonical": {"continuity": "wrong/path.md"},
                    },
                    allow_unicode=True,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE",
            ):
                resolve_work_item("继续那30秒", project_root=root)

    def test_source_issue_is_trace_not_runtime_freshness_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(
                root,
                state_overrides={"source_issue": 999999},
            )
            result = resolve_work_item("继续那30秒", project_root=root)
            self.assertTrue(result.freshness_verified)
            self.assertEqual(result.source_issue, 999999)
            self.assertIsNone(result.latest_source_checkpoint_ref)
            self.assertEqual(
                result.verification_basis,
                "canonical_continuity_verified_snapshot",
            )

    def test_exact_previous_relation_resolves_only_from_canonical_history(self):
        result = resolve_work_item(
            "重新导演之前那个30秒",
            project_root=REPO_ROOT,
        )
        self.assertEqual(result.resolved_work_item_id, "KAIM-HIGH-SEARCH-30S")
        self.assertEqual(
            result.continuation_resolution_source,
            "user_explicit_canonical_previous_work_item",
        )
        self.assertTrue(result.freshness_verified)
        self.assertEqual(
            result.verification_basis,
            "canonical_continuity_historical_binding",
        )
        packet = build_work_item_context_packet(REPO_ROOT, result)
        self.assertIn("凯姆", packet["effective_state_summary"])
        self.assertTrue(
            validate_work_item_context_packet(
                packet,
                expected_work_item_id="KAIM-HIGH-SEARCH-30S",
            )
        )

    def test_ambiguous_old_referent_fails_closed_instead_of_guessing(self):
        with self.assertRaisesRegex(
            ActiveWorkItemResolutionError,
            "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
        ):
            resolve_work_item(
                "重新导演之前爬楼那30秒",
                project_root=REPO_ROOT,
            )

    def test_previous_target_requires_canonical_historical_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root, include_history=False)
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
            ):
                resolve_work_item("重新导演之前那个30秒", project_root=root)

    def test_noncontinuation_request_does_not_require_active_snapshot(self):
        result = resolve_work_item(
            "设计圣女第一次公开登场时群众由喧闹转为安静的镜头",
            project_root=REPO_ROOT,
        )
        self.assertFalse(result.resolution_required)
        self.assertEqual(result.gate_status, "NOT_REQUIRED")

    def test_missing_pointer_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root, include_state=False)
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "ACTIVE_WORK_ITEM_STATE_MISSING",
            ):
                resolve_work_item("继续下一镜", project_root=root)

    def test_output_guard_rejects_wrong_work_item(self):
        resolution = resolve_work_item(
            "继续那30秒",
            project_root=REPO_ROOT,
        )
        with self.assertRaisesRegex(
            ActiveWorkItemResolutionError,
            "WORK_ITEM_OUTPUT_SCOPE_MISMATCH",
        ):
            validate_output_work_item(
                resolution,
                loaded_work_item_id="KAIM-SCARF-CLOTHESLINE-TRAVERSE",
                output_work_item_id="KAIM-HIGH-SEARCH-30S",
            )

        receipt = validate_output_work_item(
            resolution,
            loaded_work_item_id="KAIM-SCARF-CLOTHESLINE-TRAVERSE",
            output_work_item_id="KAIM-SCARF-CLOTHESLINE-TRAVERSE",
        )
        self.assertEqual(receipt["status"], "PASS")

    def test_omission_is_not_revocation(self):
        effective = apply_constraint_ledger(
            [
                "scarf_is_load_bearing_mechanism",
                "right_to_left_screen_trajectory",
                "wall_impact_two_foot_buffer",
            ],
            changed=["disappearance_edit_language"],
        )
        self.assertIn("scarf_is_load_bearing_mechanism", effective)
        self.assertIn("right_to_left_screen_trajectory", effective)
        self.assertIn("wall_impact_two_foot_buffer", effective)
        self.assertIn("disappearance_edit_language", effective)

    def test_explicit_revoke_removes_only_named_constraint(self):
        effective = apply_constraint_ledger(
            [
                "over_specified_setup_micro_choreography",
                "scarf_is_load_bearing_mechanism",
            ],
            preserved=["scarf_is_load_bearing_mechanism"],
            revoked=["over_specified_setup_micro_choreography"],
        )
        self.assertNotIn("over_specified_setup_micro_choreography", effective)
        self.assertIn("scarf_is_load_bearing_mechanism", effective)

    def test_state_machine_rejects_invalid_transition(self):
        self.assertTrue(
            validate_state_transition("ACTIVE_REVISION", "CHECKPOINTED")
        )
        with self.assertRaisesRegex(
            ActiveWorkItemResolutionError,
            "INVALID_WORK_ITEM_STATE_TRANSITION",
        ):
            validate_state_transition("CLOSED", "ACTIVE_REVISION")

    def test_declared_regressions_cover_p0_and_trust_boundary(self):
        ids = {case["case_id"] for case in REGRESSIONS["cases"]}
        self.assertIn("AWIR-WRONG-30S-001", ids)
        self.assertIn("AWIR-EXPLICIT-OLD-001", ids)
        self.assertIn("AWIR-EXPLICIT-AMBIGUOUS-001", ids)
        self.assertIn("AWIR-SNAPSHOT-UNVERIFIED-001", ids)
        self.assertIn("AWIR-CALLBACK-FORBIDDEN-001", ids)
        self.assertIn("AWIR-POINTER-MISSING-001", ids)
        self.assertIn("AWIR-OUTPUT-MISMATCH-001", ids)

    def test_continuation_signal_detection_is_bounded(self):
        positive = (
            "继续",
            "继续上一版",
            "继续那30秒",
            "刚才那个镜头",
            "接着做下一镜",
            "重新导演之前那个30秒",
        )
        for text in positive:
            with self.subTest(text=text):
                self.assertTrue(is_continuation_request(text))

        action_language = (
            "卫兵盯着门口逃犯继续追击",
            "凯姆继续向左滑行，镜头侧面跟随",
            "格兰继续攀爬并抓住屋檐",
            "妇女接着推开窗户",
            "设计一个新的群众仪式镜头",
        )
        for text in action_language:
            with self.subTest(text=text):
                self.assertFalse(is_continuation_request(text))

    def test_in_scene_continue_action_never_requires_work_item_resolution(self):
        result = resolve_work_item(
            "卫兵盯着门口逃犯继续追击",
            project_root=REPO_ROOT,
        )
        self.assertFalse(result.resolution_required)
        self.assertEqual(result.gate_status, "NOT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
