from pathlib import Path
import inspect
import unittest

import yaml

import learning_retriever._active_work_item_remote as remote
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

    def test_top_snapshot_is_single_continuation_default(self):
        self.assertEqual(self.state["work_item_id"], ACTIVE_ID)
        self.assertEqual(int(self.state["source_issue"]), 19)
        self.assertEqual(self.state["previous_work_item_id"], HISTORICAL_ID)
        self.assertEqual(str(self.state["latest_applied_checkpoint_ref"]), "5454103847")
        self.assertEqual(str(self.state["latest_evidence_ref"]), "5454437860")

    def test_contract_uses_fixed_github_not_local_git_as_trust_root(self):
        boundary = self.contract["canonical_github_readback_trust_boundary"]
        self.assertEqual(boundary["fixed_repository"], "vxz2datoubo/eustia-ai-film")
        self.assertEqual(boundary["fixed_branch"], "main")
        self.assertEqual(boundary["fixed_api_origin"], "https://api.github.com")
        self.assertTrue(boundary["repository_branch_and_api_origin_are_not_caller_configurable"])
        self.assertTrue(boundary["local_checkout_is_never_canonical_authority"])
        self.assertTrue(boundary["local_git_graph_cannot_mint_freshness"])
        self.assertTrue(boundary["caller_created_repo_named_main_cannot_mint_freshness"])
        self.assertTrue(boundary["git_subprocess_authority_forbidden"])
        self.assertTrue(boundary["ambient_http_proxy_is_ignored_for_authority_readback"])
        self.assertEqual(boundary["verification_basis"], "canonical_github_readback_verified_snapshot")

    def test_issue36_live_revision_freshness_is_restored(self):
        freshness = self.contract["source_issue_freshness"]
        self.assertTrue(freshness["runtime_live_probe_required"])
        self.assertEqual(freshness["source_issue_role"], "revision_and_evidence_trace_only")
        self.assertFalse(freshness["source_issue_may_override_screenplay_map_asset_or_character_authority"])
        self.assertTrue(freshness["evidence_only_comments_do_not_advance_revision_checkpoint"])
        self.assertEqual(freshness["newer_structured_checkpoint_behavior"]["gate_status"], "RECONCILE_REQUIRED")
        self.assertEqual(freshness["newer_structured_checkpoint_behavior"]["error_code"], "WORK_ITEM_SOURCE_REVISION_AHEAD_OF_CANONICAL")

    def test_runtime_module_contains_no_subprocess_or_git_authority(self):
        source = inspect.getsource(remote)
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("git -C", source)
        self.assertIn("ProxyHandler({})", source)
        self.assertIn("ssl.PROTOCOL_TLS_CLIENT", source)

    def test_context_projection_is_toctou_hardened(self):
        projection = self.contract["context_projection"]
        self.assertTrue(projection["context_packet_must_be_built_from_trusted_resolution_metadata"])
        self.assertTrue(projection["local_state_reread_after_resolution_forbidden"])
        self.assertTrue(projection["protects_against_post_resolution_local_TOCTOU"])

    def test_historical_high_search_cannot_claim_current_identity(self):
        markers = (
            f"# 2. 上一工作项基线｜{HISTORICAL_ID}（非当前 continuation 默认）",
            "# 3. 上一工作项30秒基线事件（非当前 active work item）",
            "# 7. 上一工作项结束接口（历史基线，不得覆盖 ACTIVE_WORK_ITEM_STATE）",
            "HISTORICAL / NOT_ACTIVE_WORK_ITEM",
            "`KAIM-HIGH-SEARCH-30S` 不再作为 continuation 默认",
        )
        for marker in markers:
            self.assertIn(marker, self.text)

    def test_other_scene_chain_cannot_masquerade_as_active_pointer(self):
        self.assertIn("# 10. 钟楼 / 诺瓦斯历史闪回场景链连续性 Checkpoint｜2026-08-21（非 active_work_item pointer）", self.text)
        self.assertIn("不定义“继续/那30秒”等指代的默认 work item", self.text)


if __name__ == "__main__":
    unittest.main()
