from pathlib import Path
import re
import unittest

import yaml

from learning_retriever.active_work_item import load_active_work_item_state


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTINUITY_PATH = REPO_ROOT / "07_连续性与生产状态/连续性与当前生产状态.md"
CONTRACT_PATH = REPO_ROOT / "10_运行时/active_work_item_resolution_gate.yaml"
ACTIVE_ID = "KAIM-SCARF-CLOTHESLINE-TRAVERSE"
HISTORICAL_ID = "KAIM-HIGH-SEARCH-30S"


class ActiveWorkItemContinuityGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = CONTINUITY_PATH.read_text(encoding="utf-8")
        cls.state = load_active_work_item_state(REPO_ROOT)
        cls.contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_top_snapshot_is_single_continuation_default(self) -> None:
        self.assertEqual(self.state["work_item_id"], ACTIVE_ID)
        self.assertEqual(int(self.state["source_issue"]), 19)
        self.assertEqual(self.state["previous_work_item_id"], HISTORICAL_ID)
        self.assertIn("checkpoint_writeback_status", self.state)
        self.assertIn("writeback_verified_commit", self.state)

    def test_writeback_fields_are_not_standalone_runtime_authority(self) -> None:
        boundary = self.contract["canonical_snapshot_trust_boundary"]
        threat = boundary["threat_model"]
        self.assertFalse(threat["nonempty_or_sha_shaped_commit_string_can_mint_freshness"])
        self.assertFalse(threat["candidate_branch_can_mint_canonical_freshness"])
        required = set(boundary["required_current_snapshot_checks"])
        self.assertIn("current_HEAD_equals_canonical_main", required)
        self.assertIn("materialization_commit_is_ancestor_of_canonical_main", required)
        self.assertIn("materialization_snapshot_identity_equals_current_snapshot_identity_excluding_finalization_audit_fields", required)
        receipt = boundary["two_phase_provenance"]
        self.assertEqual(
            receipt["writeback_verified_commit_role"],
            "required_audit_receipt_consistency_constraint_not_standalone_authority",
        )

    def test_historical_high_search_headings_cannot_claim_current_identity(self) -> None:
        required_markers = (
            f"# 2. 上一工作项基线｜{HISTORICAL_ID}（非当前 continuation 默认）",
            "# 3. 上一工作项30秒基线事件（非当前 active work item）",
            "# 4. 上一工作项信息保护 / Reveal Budget",
            "# 5. 上一工作项角色连续性",
            "# 7. 上一工作项结束接口（历史基线，不得覆盖 ACTIVE_WORK_ITEM_STATE）",
            "HISTORICAL / NOT_ACTIVE_WORK_ITEM",
        )
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)

    def test_no_old_section_reopens_high_search_as_current_revision_series(self) -> None:
        old_checkpoint_start = self.text.index("# 9. 上一高位搜索提示词 Constraint Ledger Checkpoint")
        novus_start = self.text.index("# 10. 钟楼 / 诺瓦斯历史闪回场景链连续性 Checkpoint")
        old_section = self.text[old_checkpoint_start:novus_start]
        forbidden_patterns = (
            r"^状态：`OPEN / REVISION SERIES ACTIVE`$",
            r"^当前 30 秒段保持 revision series 打开",
            r"^当前不重新生成整段最终提示词",
        )
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, old_section, flags=re.MULTILINE))

    def test_other_scene_chain_state_cannot_masquerade_as_active_pointer(self) -> None:
        self.assertIn(
            "# 10. 钟楼 / 诺瓦斯历史闪回场景链连续性 Checkpoint｜2026-08-21（非 active_work_item pointer）",
            self.text,
        )
        self.assertIn(
            "不定义“继续/那30秒”等指代的默认 work item",
            self.text,
        )

    def test_active_pointer_boundary_is_explicit_for_human_and_runtime_readers(self) -> None:
        self.assertIn(
            "当前 active work item 以顶部 `ACTIVE_WORK_ITEM_STATE` 为唯一 continuation 默认",
            self.text,
        )
        self.assertIn(
            "`KAIM-HIGH-SEARCH-30S` 不再作为 continuation 默认",
            self.text,
        )


if __name__ == "__main__":
    unittest.main()
