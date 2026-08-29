from pathlib import Path
import tempfile
import unittest

import yaml

from learning_retriever.active_work_item import (
    ActiveWorkItemResolutionError,
    apply_constraint_ledger,
    is_continuation_request,
    load_active_work_item_state,
    resolve_work_item,
    validate_output_work_item,
    validate_state_transition,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
REGRESSION_PATH = REPO_ROOT / "11_验收/active_work_item_resolution_regression_cases.yaml"
REGRESSIONS = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))


class ActiveWorkItemResolutionTests(unittest.TestCase):
    def test_current_continuity_exposes_machine_readable_active_state(self):
        state = load_active_work_item_state(REPO_ROOT)
        self.assertEqual(state["work_item_id"], "KAIM-SCARF-CLOTHESLINE-TRAVERSE")
        self.assertEqual(int(state["source_issue"]), 19)
        self.assertEqual(str(state["latest_applied_checkpoint_ref"]), "5454103847")
        self.assertIn("scarf_clothesline_geometry", state["locked_constraints"])
        self.assertIn("over_specified_setup_micro_choreography", state["revoked_constraints"])

    def test_wrong_30s_regression_resolves_active_pointer(self):
        result = resolve_work_item(
            "重新导演上次那30秒",
            project_root=REPO_ROOT,
            context={
                "source_issue_accessible": True,
                "latest_source_checkpoint_ref": "5454103847",
            },
        )
        self.assertTrue(result.resolution_required)
        self.assertEqual(result.resolved_work_item_id, "KAIM-SCARF-CLOTHESLINE-TRAVERSE")
        self.assertEqual(result.continuation_resolution_source, "active_work_item_pointer")
        self.assertTrue(result.freshness_verified)
        self.assertEqual(result.gate_status, "RESOLVED_VERIFIED")

    def test_explicit_old_work_item_override_requires_verified_target(self):
        with self.assertRaisesRegex(
            ActiveWorkItemResolutionError,
            "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
        ):
            resolve_work_item(
                "重新导演之前爬楼那30秒",
                project_root=REPO_ROOT,
                context={"explicit_work_item_id": "KAIM-HIGH-SEARCH-30S"},
            )

        result = resolve_work_item(
            "重新导演之前爬楼那30秒",
            project_root=REPO_ROOT,
            context={
                "explicit_work_item_id": "KAIM-HIGH-SEARCH-30S",
                "explicit_target_verified": True,
            },
        )
        self.assertEqual(result.resolved_work_item_id, "KAIM-HIGH-SEARCH-30S")
        self.assertEqual(result.continuation_resolution_source, "user_explicit")

    def test_checkpoint_lag_fails_before_compilation(self):
        with self.assertRaisesRegex(
            ActiveWorkItemResolutionError,
            "WORK_ITEM_CHECKPOINT_RECONCILE_REQUIRED",
        ):
            resolve_work_item(
                "继续上一版",
                project_root=REPO_ROOT,
                context={
                    "source_issue_accessible": True,
                    "latest_source_checkpoint_ref": "NEWER-CHECKPOINT",
                },
            )

    def test_source_issue_must_be_freshly_verified(self):
        with self.assertRaisesRegex(
            ActiveWorkItemResolutionError,
            "WORK_ITEM_FRESHNESS_UNVERIFIED",
        ):
            resolve_work_item(
                "继续那30秒",
                project_root=REPO_ROOT,
                context={"source_issue_accessible": False},
            )

        with self.assertRaisesRegex(
            ActiveWorkItemResolutionError,
            "WORK_ITEM_FRESHNESS_UNVERIFIED",
        ):
            resolve_work_item(
                "继续那30秒",
                project_root=REPO_ROOT,
                context={"source_issue_accessible": True},
            )

    def test_noncontinuation_request_does_not_add_read_amplification(self):
        result = resolve_work_item(
            "设计圣女第一次公开登场时群众由喧闹转为安静的镜头",
            project_root=REPO_ROOT,
        )
        self.assertFalse(result.resolution_required)
        self.assertEqual(result.gate_status, "NOT_REQUIRED")

    def test_missing_pointer_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "07_连续性与生产状态/连续性与当前生产状态.md"
            path.parent.mkdir(parents=True)
            path.write_text("# no active state\n", encoding="utf-8")
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "ACTIVE_WORK_ITEM_STATE_MISSING",
            ):
                resolve_work_item(
                    "继续下一镜",
                    project_root=root,
                    context={"source_issue_accessible": True},
                )

    def test_output_guard_rejects_wrong_work_item(self):
        resolution = resolve_work_item(
            "继续那30秒",
            project_root=REPO_ROOT,
            context={
                "source_issue_accessible": True,
                "latest_source_checkpoint_ref": "5454103847",
            },
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
            ["over_specified_setup_micro_choreography", "scarf_is_load_bearing_mechanism"],
            preserved=["scarf_is_load_bearing_mechanism"],
            revoked=["over_specified_setup_micro_choreography"],
        )
        self.assertNotIn("over_specified_setup_micro_choreography", effective)
        self.assertIn("scarf_is_load_bearing_mechanism", effective)

    def test_state_machine_rejects_invalid_transition(self):
        self.assertTrue(validate_state_transition("ACTIVE_REVISION", "CHECKPOINTED"))
        with self.assertRaisesRegex(
            ActiveWorkItemResolutionError,
            "INVALID_WORK_ITEM_STATE_TRANSITION",
        ):
            validate_state_transition("CLOSED", "ACTIVE_REVISION")

    def test_declared_regressions_cover_p0_and_fail_closed_paths(self):
        ids = {case["case_id"] for case in REGRESSIONS["cases"]}
        self.assertIn("AWIR-WRONG-30S-001", ids)
        self.assertIn("AWIR-EXPLICIT-OLD-001", ids)
        self.assertIn("AWIR-CHECKPOINT-LAG-001", ids)
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

    def test_in_scene_continue_action_never_requires_source_issue_freshness(self):
        result = resolve_work_item(
            "卫兵盯着门口逃犯继续追击",
            project_root=REPO_ROOT,
        )
        self.assertFalse(result.resolution_required)
        self.assertEqual(result.gate_status, "NOT_REQUIRED")


if __name__ == "__main__":
    unittest.main()
