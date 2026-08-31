from copy import deepcopy
import inspect
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import yaml

import learning_retriever._active_work_item_remote as remote
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
CONTINUITY = Path("07_连续性与生产状态/连续性与当前生产状态.md")
REGRESSION_PATH = REPO_ROOT / "11_验收/active_work_item_resolution_regression_cases.yaml"
REGRESSIONS = yaml.safe_load(REGRESSION_PATH.read_text(encoding="utf-8"))
REMOTE_SHA = "a" * 40


def _temp_projection() -> tuple[tempfile.TemporaryDirectory, Path]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    (root / CONTINUITY.parent).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / "PROJECT_INDEX.yaml", root / "PROJECT_INDEX.yaml")
    shutil.copyfile(REPO_ROOT / CONTINUITY, root / CONTINUITY)
    return tmp, root


def _trusted_mocks(root: Path, *, comments: list[dict] | None = None, compare_status: str = "ahead", merge_base: str | None = None, materialized_text: str | None = None):
    index_text = (root / "PROJECT_INDEX.yaml").read_text(encoding="utf-8")
    continuity_text = (root / CONTINUITY).read_text(encoding="utf-8")
    state = load_active_work_item_state(root)
    declared = str(state["writeback_verified_commit"])
    comments = comments if comments is not None else [
        {"id": 5454103847, "body": "## Micro Capture — A2 real-output review"},
        {"id": 5454437860, "body": "## Evidence clarification — actual motion-reference identity confirmed by user"},
    ]

    def api(endpoint: str):
        if endpoint.endswith("/branches/main"):
            return {"commit": {"sha": REMOTE_SHA}}
        if f"/commits/{declared}" in endpoint:
            return {"sha": declared}
        if "/compare/" in endpoint:
            return {"status": compare_status, "merge_base_commit": {"sha": merge_base or declared}}
        raise AssertionError(f"unexpected API endpoint: {endpoint}")

    def file_text(path: Path, ref: str):
        if path == Path("PROJECT_INDEX.yaml") and ref == REMOTE_SHA:
            return index_text
        if path == CONTINUITY and ref == REMOTE_SHA:
            return continuity_text
        if path == CONTINUITY and ref == declared:
            return materialized_text if materialized_text is not None else continuity_text
        raise AssertionError(f"unexpected file read: {path}@{ref}")

    return patch.object(remote, "_github_api_json", side_effect=api), patch.object(remote, "_github_file_text", side_effect=file_text), patch.object(remote, "_github_issue_comments", return_value=comments)


class ActiveWorkItemResolutionTests(unittest.TestCase):
    def test_current_candidate_state_is_machine_readable(self):
        state = load_active_work_item_state(REPO_ROOT)
        self.assertEqual(state["work_item_id"], "KAIM-SCARF-CLOTHESLINE-TRAVERSE")
        self.assertEqual(int(state["source_issue"]), 19)
        self.assertEqual(str(state["latest_applied_checkpoint_ref"]), "5454103847")
        self.assertEqual(str(state["latest_evidence_ref"]), "5454437860")

    def test_public_api_has_no_caller_mintable_trust_root(self):
        params = inspect.signature(resolve_work_item).parameters
        for forbidden in ("freshness_provider", "explicit_target_provider", "repository", "api_url", "branch", "git_binary", "receipt"):
            self.assertNotIn(forbidden, params)
        runtime_source = inspect.getsource(remote)
        self.assertNotIn("import subprocess", runtime_source)
        self.assertNotIn("git -C", runtime_source)
        self.assertEqual(remote.CANONICAL_REPOSITORY, "vxz2datoubo/eustia-ai-film")
        self.assertEqual(remote.CANONICAL_BRANCH, "main")
        self.assertEqual(remote.GITHUB_API_ROOT, "https://api.github.com")

    def test_noncontinuation_fast_path_makes_no_remote_read(self):
        with patch.object(remote, "_github_api_json", side_effect=AssertionError("network must not run")):
            result = resolve_work_item("设计圣女第一次公开登场时群众安静下来的镜头", project_root=REPO_ROOT)
        self.assertFalse(result.resolution_required)
        self.assertEqual(result.gate_status, "NOT_REQUIRED")

    def test_active_pointer_resolves_only_after_fixed_github_and_issue_freshness(self):
        tmp, root = _temp_projection()
        try:
            api, files, comments = _trusted_mocks(root)
            with api, files, comments:
                result = resolve_work_item("重新导演上次那30秒", project_root=root)
            self.assertEqual(result.resolved_work_item_id, "KAIM-SCARF-CLOTHESLINE-TRAVERSE")
            self.assertTrue(result.freshness_verified)
            self.assertEqual(result.latest_source_checkpoint_ref, "5454103847")
            self.assertEqual(result.verification_basis, "canonical_github_readback_verified_snapshot")
            self.assertTrue(result.snapshot_fingerprint)
        finally:
            tmp.cleanup()

    def test_newer_evidence_only_comment_does_not_move_revision_pointer(self):
        tmp, root = _temp_projection()
        try:
            comments_payload = [
                {"id": 5454103847, "body": "## Micro Capture — accepted checkpoint"},
                {"id": 5459999999, "body": "## Evidence clarification — binary reference identity"},
            ]
            api, files, comments = _trusted_mocks(root, comments=comments_payload)
            with api, files, comments:
                result = resolve_work_item("继续那30秒", project_root=root)
            self.assertTrue(result.freshness_verified)
            self.assertEqual(result.latest_source_checkpoint_ref, "5454103847")
        finally:
            tmp.cleanup()

    def test_newer_structured_checkpoint_forces_reconcile_before_compiler(self):
        tmp, root = _temp_projection()
        try:
            comments_payload = [
                {"id": 5454103847, "body": "## Micro Capture — applied"},
                {"id": 5455000000, "body": "## Revision checkpoint — newer accepted delta"},
            ]
            api, files, comments = _trusted_mocks(root, comments=comments_payload)
            with api, files, comments, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                resolve_work_item("继续那30秒", project_root=root)
            self.assertEqual(ctx.exception.code, "WORK_ITEM_SOURCE_REVISION_AHEAD_OF_CANONICAL")
            self.assertEqual(ctx.exception.details["gate_status"], "RECONCILE_REQUIRED")
            self.assertEqual(ctx.exception.details["latest_source_checkpoint_ref"], "5455000000")
        finally:
            tmp.cleanup()

    def test_source_issue_inaccessible_fails_closed(self):
        tmp, root = _temp_projection()
        try:
            api, files, _ = _trusted_mocks(root)
            with api, files, patch.object(remote, "_github_issue_comments", side_effect=ActiveWorkItemResolutionError("WORK_ITEM_CANONICAL_AUTHORITY_UNAVAILABLE", details={"reason": "denied"})), self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                resolve_work_item("继续那30秒", project_root=root)
            self.assertEqual(ctx.exception.code, "WORK_ITEM_SOURCE_ISSUE_UNAVAILABLE")
        finally:
            tmp.cleanup()

    def test_fake_local_main_or_local_git_cannot_mint_freshness(self):
        tmp, root = _temp_projection()
        try:
            (root / ".git").mkdir()
            remote_continuity = (root / CONTINUITY).read_text(encoding="utf-8")
            (root / CONTINUITY).write_text(remote_continuity + "\n# caller-local forged main\n", encoding="utf-8")
            state = load_active_work_item_state(root)
            declared = str(state["writeback_verified_commit"])
            def api(endpoint: str):
                if endpoint.endswith("/branches/main"):
                    return {"commit": {"sha": REMOTE_SHA}}
                if f"/commits/{declared}" in endpoint:
                    return {"sha": declared}
                if "/compare/" in endpoint:
                    return {"status": "ahead", "merge_base_commit": {"sha": declared}}
                raise AssertionError(endpoint)
            def files(path: Path, ref: str):
                if path == Path("PROJECT_INDEX.yaml"):
                    return (root / "PROJECT_INDEX.yaml").read_text(encoding="utf-8")
                return remote_continuity
            with patch.object(remote, "_github_api_json", side_effect=api), patch.object(remote, "_github_file_text", side_effect=files), self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                resolve_work_item("继续那30秒", project_root=root)
            self.assertEqual(ctx.exception.details.get("reason"), "continuity_local_differs_from_fixed_github_main")
        finally:
            tmp.cleanup()

    def test_project_index_local_mismatch_remote_fails_closed(self):
        tmp, root = _temp_projection()
        try:
            original = (root / "PROJECT_INDEX.yaml").read_text(encoding="utf-8")
            (root / "PROJECT_INDEX.yaml").write_text(original + "\ncaller_fake: true\n", encoding="utf-8")
            state = load_active_work_item_state(root)
            declared = str(state["writeback_verified_commit"])
            continuity = (root / CONTINUITY).read_text(encoding="utf-8")
            def api(endpoint: str):
                if endpoint.endswith("/branches/main"):
                    return {"commit": {"sha": REMOTE_SHA}}
                if f"/commits/{declared}" in endpoint:
                    return {"sha": declared}
                if "/compare/" in endpoint:
                    return {"status": "ahead", "merge_base_commit": {"sha": declared}}
                raise AssertionError(endpoint)
            def files(path: Path, ref: str):
                return original if path == Path("PROJECT_INDEX.yaml") else continuity
            with patch.object(remote, "_github_api_json", side_effect=api), patch.object(remote, "_github_file_text", side_effect=files), self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                resolve_work_item("继续那30秒", project_root=root)
            self.assertEqual(ctx.exception.details.get("reason"), "project_index_local_differs_from_fixed_github_main")
        finally:
            tmp.cleanup()

    def test_nonancestor_materialization_fails_closed(self):
        tmp, root = _temp_projection()
        try:
            api, files, comments = _trusted_mocks(root, compare_status="diverged", merge_base="b" * 40)
            with api, files, comments, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                resolve_work_item("继续那30秒", project_root=root)
            self.assertEqual(ctx.exception.details.get("reason"), "materialization_commit_not_canonical_ancestor")
        finally:
            tmp.cleanup()

    def test_materialization_identity_mismatch_fails_closed(self):
        tmp, root = _temp_projection()
        try:
            materialized = (root / CONTINUITY).read_text(encoding="utf-8").replace("scarf_clothesline_geometry", "different_geometry", 1)
            api, files, comments = _trusted_mocks(root, materialized_text=materialized)
            with api, files, comments, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                resolve_work_item("继续那30秒", project_root=root)
            self.assertEqual(ctx.exception.details.get("reason"), "materialization_snapshot_identity_mismatch")
        finally:
            tmp.cleanup()

    def test_exact_previous_target_comes_from_trusted_remote_history(self):
        tmp, root = _temp_projection()
        try:
            api, files, comments = _trusted_mocks(root)
            with api, files, comments:
                result = resolve_work_item("重新导演之前那个30秒", project_root=root)
            self.assertEqual(result.resolved_work_item_id, "KAIM-HIGH-SEARCH-30S")
            self.assertEqual(result.verification_basis, "canonical_github_readback_historical_binding")
            packet = build_work_item_context_packet(root, result)
            self.assertTrue(validate_work_item_context_packet(packet, expected_work_item_id="KAIM-HIGH-SEARCH-30S"))
        finally:
            tmp.cleanup()

    def test_ambiguous_old_referent_fails_closed(self):
        tmp, root = _temp_projection()
        try:
            api, files, comments = _trusted_mocks(root)
            with api, files, comments, self.assertRaises(ActiveWorkItemResolutionError) as ctx:
                resolve_work_item("重新导演之前爬楼那30秒", project_root=root)
            self.assertEqual(ctx.exception.code, "EXPLICIT_NONACTIVE_REFERENT_REQUIRES_RESOLUTION")
        finally:
            tmp.cleanup()

    def test_context_packet_cannot_be_changed_by_local_TOCTOU_after_resolution(self):
        tmp, root = _temp_projection()
        try:
            api, files, comments = _trusted_mocks(root)
            with api, files, comments:
                result = resolve_work_item("继续那30秒", project_root=root)
            trusted_summary = result.target_metadata["current_effective_state_summary"]
            (root / CONTINUITY).write_text("# tampered after resolution\n", encoding="utf-8")
            packet = build_work_item_context_packet(root, result)
            self.assertEqual(packet["effective_state_summary"], trusted_summary)
            self.assertTrue(validate_work_item_context_packet(packet, expected_work_item_id="KAIM-SCARF-CLOTHESLINE-TRAVERSE"))
        finally:
            tmp.cleanup()

    def test_output_guard_and_constraint_ledger(self):
        resolution = remote.WorkItemResolution(True, "A", "test", "1", True, target_metadata={"work_item_id": "A"}, verification_basis="canonical_github_readback_verified_snapshot")
        with self.assertRaises(ActiveWorkItemResolutionError):
            validate_output_work_item(resolution, loaded_work_item_id="A", output_work_item_id="B")
        self.assertEqual(validate_output_work_item(resolution, loaded_work_item_id="A", output_work_item_id="A")["status"], "PASS")
        effective = apply_constraint_ledger(["keep_a", "remove_b"], changed=["add_c"], revoked=["remove_b"])
        self.assertEqual(effective, ["keep_a", "add_c"])
        self.assertTrue(validate_state_transition("ACTIVE_REVISION", "CHECKPOINTED"))

    def test_regression_registry_contains_remote_trust_and_live_freshness_cases(self):
        ids = {case["case_id"] for case in REGRESSIONS["cases"]}
        for required in (
            "AWIR-WRONG-30S-001", "AWIR-FIXED-GITHUB-TRUST-001", "AWIR-LOCAL-GIT-MINT-FORBIDDEN-001",
            "AWIR-SOURCE-ISSUE-LIVE-FRESH-001", "AWIR-SOURCE-ISSUE-AHEAD-001", "AWIR-EVIDENCE-ONLY-NEWER-001",
            "AWIR-CONTEXT-TOCTOU-001", "AWIR-OUTPUT-MISMATCH-001",
        ):
            self.assertIn(required, ids)

    def test_continuation_detection_remains_bounded(self):
        for text in ("继续", "继续上一版", "继续那30秒", "刚才那个镜头", "接着做下一镜", "重新导演之前那个30秒"):
            self.assertTrue(is_continuation_request(text), text)
        for text in ("卫兵盯着门口逃犯继续追击", "凯姆继续向左滑行，镜头侧面跟随", "妇女接着推开窗户", "设计新的群众仪式镜头"):
            self.assertFalse(is_continuation_request(text), text)


if __name__ == "__main__":
    unittest.main()
