from copy import deepcopy
import inspect
from pathlib import Path
import subprocess
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
CONTINUITY_REL = Path("07_连续性与生产状态/连续性与当前生产状态.md")


def _git(root: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if check and completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def _render_continuity(
    state: dict,
    *,
    include_history: bool = True,
) -> str:
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
    return "\n".join(parts) + "\n"


def _write_project_index(root: Path, *, continuity_path: str | None = None) -> None:
    index = {
        "project_id": "EUSTIA_AI_FILM",
        "canonical": {
            "continuity": continuity_path or CONTINUITY_REL.as_posix(),
        },
    }
    (root / "PROJECT_INDEX.yaml").write_text(
        yaml.safe_dump(index, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _write_continuity(
    root: Path,
    state: dict,
    *,
    include_history: bool = True,
) -> None:
    path = root / CONTINUITY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _render_continuity(state, include_history=include_history),
        encoding="utf-8",
    )


def _commit_all(root: Path, message: str) -> str:
    _git(root, "add", "PROJECT_INDEX.yaml", CONTINUITY_REL.as_posix())
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _write_temp_authority(
    root: Path,
    *,
    state_overrides: dict | None = None,
    include_state: bool = True,
    include_history: bool = True,
    finalize: bool = True,
    final_state_overrides: dict | None = None,
    continuity_path: str | None = None,
) -> dict[str, str | dict | None]:
    """Create a real two-phase canonical main Git fixture.

    Phase 1 materializes the substantive snapshot with pending audit fields.
    Phase 2 finalizes it by recording the materialization commit. Runtime trust
    therefore exercises real commit existence, ancestry, tree/blob readback and
    snapshot-identity checks rather than trusting fixture booleans.
    """
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "eustia-test@example.invalid")
    _git(root, "config", "user.name", "Eustia Test")
    _write_project_index(root, continuity_path=continuity_path)

    if not include_state:
        continuity = root / CONTINUITY_REL
        continuity.parent.mkdir(parents=True, exist_ok=True)
        continuity.write_text("# no active state\n", encoding="utf-8")
        materialization_sha = _commit_all(root, "materialize missing-state fixture")
        return {
            "materialization_sha": materialization_sha,
            "final_sha": materialization_sha,
            "state": None,
        }

    state = deepcopy(load_active_work_item_state(REPO_ROOT))
    state.update(state_overrides or {})
    state["checkpoint_writeback_status"] = "pending"
    state["writeback_verified_commit"] = "pending_materialization"
    _write_continuity(root, state, include_history=include_history)
    materialization_sha = _commit_all(root, "materialize active work item")

    if not finalize:
        return {
            "materialization_sha": materialization_sha,
            "final_sha": materialization_sha,
            "state": state,
        }

    state["checkpoint_writeback_status"] = "verified"
    state["writeback_verified_commit"] = materialization_sha
    state.update(final_state_overrides or {})
    _write_continuity(root, state, include_history=include_history)
    final_sha = _commit_all(root, "finalize active work item")
    return {
        "materialization_sha": materialization_sha,
        "final_sha": final_sha,
        "state": state,
    }


def _rewrite_current_state(
    root: Path,
    overrides: dict,
    *,
    include_history: bool = True,
) -> dict:
    state = load_active_work_item_state(root)
    state.update(overrides)
    _write_continuity(root, state, include_history=include_history)
    return state


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
        self.assertIn("scarf_clothesline_geometry", state["locked_constraints"])
        self.assertIn(
            "over_specified_setup_micro_choreography",
            state["revoked_constraints"],
        )

    def test_wrong_30s_regression_resolves_from_real_canonical_git_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root)
            result = resolve_work_item("重新导演上次那30秒", project_root=root)
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

    def test_pending_materialization_is_not_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root, finalize=False)
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            ):
                resolve_work_item("继续那30秒", project_root=root)

    def test_empty_materialization_commit_reference_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(
                root,
                final_state_overrides={"writeback_verified_commit": ""},
            )
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            ):
                resolve_work_item("继续那30秒", project_root=root)

    def test_existing_nonancestor_superseded_commit_cannot_mint_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            info = _write_temp_authority(root)
            materialization_sha = str(info["materialization_sha"])

            _git(root, "checkout", "-b", "superseded", materialization_sha)
            _rewrite_current_state(
                root,
                {
                    "checkpoint_writeback_status": "candidate_branch_pending_review",
                    "writeback_verified_commit": "candidate_branch_pending_review",
                },
            )
            superseded_sha = _commit_all(root, "superseded candidate snapshot")

            _git(root, "checkout", "main")
            _rewrite_current_state(
                root,
                {
                    "checkpoint_writeback_status": "verified",
                    "writeback_verified_commit": superseded_sha,
                },
            )
            _commit_all(root, "forge nonancestor audit reference on main")

            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            ) as caught:
                resolve_work_item("继续那30秒", project_root=root)
            self.assertEqual(
                caught.exception.details.get("reason"),
                "materialization_commit_not_canonical_ancestor",
            )

    def test_candidate_branch_cannot_mint_canonical_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root)
            _git(root, "checkout", "-b", "candidate")
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            ) as caught:
                resolve_work_item("继续那30秒", project_root=root)
            self.assertEqual(
                caught.exception.details.get("reason"),
                "current_head_is_not_canonical_main",
            )

    def test_uncommitted_continuity_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root)
            _rewrite_current_state(
                root,
                {"current_effective_state_summary": "tampered worktree summary"},
            )
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            ) as caught:
                resolve_work_item("继续那30秒", project_root=root)
            self.assertEqual(
                caught.exception.details.get("reason"),
                "continuity_worktree_differs_from_canonical_main",
            )

    def test_uncommitted_project_index_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root)
            index_path = root / "PROJECT_INDEX.yaml"
            index_path.write_text(
                index_path.read_text(encoding="utf-8") + "\n# tamper\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            ) as caught:
                resolve_work_item("继续那30秒", project_root=root)
            self.assertEqual(
                caught.exception.details.get("reason"),
                "project_index_worktree_differs_from_canonical_main",
            )

    def test_directory_without_git_main_cannot_mint_freshness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.mkdir(parents=True, exist_ok=True)
            _write_project_index(root)
            state = deepcopy(load_active_work_item_state(REPO_ROOT))
            state["checkpoint_writeback_status"] = "verified"
            state["writeback_verified_commit"] = "0" * 40
            _write_continuity(root, state)
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "WORK_ITEM_SNAPSHOT_UNVERIFIED",
            ):
                resolve_work_item("继续那30秒", project_root=root)

    def test_project_index_must_register_continuity_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root, continuity_path="wrong/path.md")
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
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root)
            result = resolve_work_item(
                "重新导演之前那个30秒",
                project_root=root,
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
            packet = build_work_item_context_packet(root, result)
            self.assertIn("凯姆", packet["effective_state_summary"])
            self.assertTrue(
                validate_work_item_context_packet(
                    packet,
                    expected_work_item_id="KAIM-HIGH-SEARCH-30S",
                )
            )

    def test_ambiguous_old_referent_fails_closed_instead_of_guessing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root)
            with self.assertRaisesRegex(
                ActiveWorkItemResolutionError,
                "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION",
            ):
                resolve_work_item(
                    "重新导演之前爬楼那30秒",
                    project_root=root,
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
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_temp_authority(root)
            resolution = resolve_work_item("继续那30秒", project_root=root)
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
        self.assertIn("AWIR-NONANCESTOR-COMMIT-001", ids)
        self.assertIn("AWIR-CANDIDATE-CHECKOUT-001", ids)
        self.assertIn("AWIR-WORKTREE-TAMPER-001", ids)

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
