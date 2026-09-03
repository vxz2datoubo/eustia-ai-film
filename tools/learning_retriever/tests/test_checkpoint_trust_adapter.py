from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

import yaml

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


def index_without_activation(*, mutation: str) -> str:
    value = yaml.safe_load(INDEX)
    if mutation == "flag":
        value["policy"].pop("active_work_item_checkpoint_compiler_required_for_checkpoint_or_series_close", None)
    elif mutation == "canonical":
        value["canonical"]["active_work_item_checkpoint_compiler"] = "10_运行时/not_the_checkpoint_compiler.yaml"
    elif mutation == "effective":
        value["effective_sources"]["10_运行时/active_work_item_checkpoint_compiler.yaml"] = "candidate"
    else:
        raise AssertionError(mutation)
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False)


class CheckpointTrustAdapterTests(unittest.TestCase):
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

    def test_checkpoint_execution_requires_complete_project_index_activation_tuple(self):
        branch = {"commit": {"sha": MAIN_SHA}}
        for mutation in ("flag", "canonical", "effective"):
            with self.subTest(mutation=mutation):
                broken_index = index_without_activation(mutation=mutation)

                def file_text(path, ref):
                    return broken_index if str(path).endswith("PROJECT_INDEX.yaml") else CONTINUITY

                with patch("learning_retriever.checkpoint_trust._remote._github_api_json", return_value=branch), \
                     patch("learning_retriever.checkpoint_trust._remote._github_file_text", side_effect=file_text):
                    with self.assertRaisesRegex(
                        CheckpointTrustError,
                        "CHECKPOINT_ACTIVATION_REGISTRATION_INVALID",
                    ):
                        load_trusted_checkpoint_baseline(REPO_ROOT)

    def test_activation_is_checked_before_continuity_or_source_issue_authority_is_consumed(self):
        branch = {"commit": {"sha": MAIN_SHA}}
        broken_index = index_without_activation(mutation="flag")
        calls: list[str] = []

        def file_text(path, ref):
            normalized = str(path).replace("\\", "/")
            calls.append(normalized)
            if normalized.endswith("PROJECT_INDEX.yaml"):
                return broken_index
            raise AssertionError("continuity must not be read before activation validates")

        with patch("learning_retriever.checkpoint_trust._remote._github_api_json", return_value=branch), \
             patch("learning_retriever.checkpoint_trust._remote._github_file_text", side_effect=file_text), \
             patch("learning_retriever.checkpoint_trust._remote._github_issue_comments") as issue_comments:
            with self.assertRaisesRegex(
                CheckpointTrustError,
                "CHECKPOINT_ACTIVATION_REGISTRATION_INVALID",
            ):
                load_trusted_checkpoint_baseline(REPO_ROOT)
        self.assertEqual(calls, ["PROJECT_INDEX.yaml"])
        issue_comments.assert_not_called()

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
