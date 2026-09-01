from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from learning_retriever.checkpoint_trust import (
    CheckpointTrustError,
    fetch_fixed_continuity_at_commit,
    load_trusted_checkpoint_baseline,
    validate_live_checkpoint,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
INDEX = (REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8")
CONTINUITY = (REPO_ROOT / "07_连续性与生产状态/连续性与当前生产状态.md").read_text(encoding="utf-8")
MAIN_SHA = "1" * 40
MATERIALIZATION_SHA = "2" * 40
APPLIED = 5454103847
NEW = 5500000001


def comment(comment_id: int, body: str):
    return {"id": comment_id, "body": body}


class CheckpointTrustAdapterTests(unittest.TestCase):
    def _remote_patches(self, *, local_continuity=None, comments=None):
        local_continuity = CONTINUITY if local_continuity is None else local_continuity
        comments = comments or [
            comment(APPLIED, "## Revision checkpoint\nschema: REVISION_CHECKPOINT/v1"),
            comment(NEW, "## Micro Capture\nschema: MICRO_CAPTURE/v1"),
        ]
        branch = {"commit": {"sha": MAIN_SHA}}

        def file_text(path, ref):
            name = str(path).replace("\\", "/")
            if name.endswith("PROJECT_INDEX.yaml"):
                return INDEX
            return CONTINUITY

        return (
            patch("learning_retriever.checkpoint_trust._remote._github_api_json", return_value=branch),
            patch("learning_retriever.checkpoint_trust._remote._github_file_text", side_effect=file_text),
            patch("learning_retriever.checkpoint_trust._remote._remote_materialization", return_value=MATERIALIZATION_SHA),
            patch("learning_retriever.checkpoint_trust._remote._github_issue_comments", return_value=comments),
            patch.object(Path, "read_text", autospec=True),
            local_continuity,
        )

    def test_baseline_uses_fixed_repo_branch_and_allows_source_ahead_without_promoting_it(self):
        branch = {"commit": {"sha": MAIN_SHA}}
        comments = [
            comment(APPLIED, "## Revision checkpoint\nschema: REVISION_CHECKPOINT/v1"),
            comment(NEW, "## Micro Capture\nschema: MICRO_CAPTURE/v1"),
        ]
        def file_text(path, ref):
            return INDEX if str(path).endswith("PROJECT_INDEX.yaml") else CONTINUITY
        with patch("learning_retriever.checkpoint_trust._remote._github_api_json", return_value=branch), \
             patch("learning_retriever.checkpoint_trust._remote._github_file_text", side_effect=file_text), \
             patch("learning_retriever.checkpoint_trust._remote._remote_materialization", return_value=MATERIALIZATION_SHA), \
             patch("learning_retriever.checkpoint_trust._remote._github_issue_comments", return_value=comments):
            baseline = load_trusted_checkpoint_baseline(REPO_ROOT)
        self.assertEqual(baseline.canonical_sha, MAIN_SHA)
        self.assertEqual(baseline.materialization_commit_sha, MATERIALIZATION_SHA)
        self.assertEqual(baseline.latest_structured_source_checkpoint, str(NEW))
        self.assertEqual(baseline.state["latest_applied_checkpoint_ref"], str(APPLIED))

    def test_local_continuity_drift_fails_closed(self):
        branch = {"commit": {"sha": MAIN_SHA}}
        comments = [comment(APPLIED, "## Revision checkpoint\nschema: REVISION_CHECKPOINT/v1")]
        def file_text(path, ref):
            return INDEX if str(path).endswith("PROJECT_INDEX.yaml") else CONTINUITY
        original = Path.read_text
        def local_read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if str(path).replace("\\", "/").endswith("07_连续性与生产状态/连续性与当前生产状态.md"):
                return text + "\nLOCAL-DRIFT"
            return text
        with patch("learning_retriever.checkpoint_trust._remote._github_api_json", return_value=branch), \
             patch("learning_retriever.checkpoint_trust._remote._github_file_text", side_effect=file_text), \
             patch("learning_retriever.checkpoint_trust._remote._remote_materialization", return_value=MATERIALIZATION_SHA), \
             patch("learning_retriever.checkpoint_trust._remote._github_issue_comments", return_value=comments), \
             patch.object(Path, "read_text", local_read):
            with self.assertRaisesRegex(CheckpointTrustError, "CHECKPOINT_CONTINUITY_DRIFT_FROM_FIXED_GITHUB"):
                load_trusted_checkpoint_baseline(REPO_ROOT)

    def test_applied_checkpoint_must_exist_and_still_be_structured(self):
        with patch("learning_retriever.checkpoint_trust._remote._github_issue_comments", return_value=[
            comment(NEW, "## Micro Capture\nschema: MICRO_CAPTURE/v1")
        ]):
            with self.assertRaisesRegex(CheckpointTrustError, "CHECKPOINT_SOURCE_COMMENT_MISSING"):
                validate_live_checkpoint(19, APPLIED, require_latest=False)
        with patch("learning_retriever.checkpoint_trust._remote._github_issue_comments", return_value=[
            comment(APPLIED, "Evidence clarification only")
        ]):
            with self.assertRaisesRegex(CheckpointTrustError, "CHECKPOINT_SOURCE_COMMENT_NOT_STRUCTURED_REVISION"):
                validate_live_checkpoint(19, APPLIED, require_latest=False)

    def test_proposed_checkpoint_must_be_latest_structured_comment(self):
        comments = [
            comment(APPLIED, "## Revision checkpoint\nschema: REVISION_CHECKPOINT/v1"),
            comment(NEW, "## Micro Capture\nschema: MICRO_CAPTURE/v1"),
        ]
        with patch("learning_retriever.checkpoint_trust._remote._github_issue_comments", return_value=comments):
            with self.assertRaisesRegex(CheckpointTrustError, "CHECKPOINT_SOURCE_REF_NOT_LATEST_STRUCTURED_REVISION"):
                validate_live_checkpoint(19, APPLIED, require_latest=True)
            self.assertEqual(validate_live_checkpoint(19, NEW, require_latest=True), str(NEW))

    def test_fixed_commit_readback_rejects_missing_or_changed_commit_identity(self):
        with patch("learning_retriever.checkpoint_trust._remote._github_api_json", return_value={"sha": "3" * 40}):
            with self.assertRaisesRegex(CheckpointTrustError, "CHECKPOINT_FIXED_REPOSITORY_COMMIT_MISSING"):
                fetch_fixed_continuity_at_commit(MATERIALIZATION_SHA)


if __name__ == "__main__":
    unittest.main()
