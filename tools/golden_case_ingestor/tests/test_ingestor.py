from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from golden_ingestor.bundle import IngestOptions, ingest
from golden_ingestor.util import dump_yaml, load_yaml, resolve_ffmpeg, run
from golden_ingestor.validator import validate_bundle


class GoldenCaseIngestorTests(unittest.TestCase):
    def _image_sequence(self, root: Path) -> Path:
        directory = root / "images"
        directory.mkdir()
        for index in range(8):
            image = Image.new("RGB", (160, 90), "#161616")
            draw = ImageDraw.Draw(image)
            # First four frames hold; later frames change position and color.
            if index >= 4:
                draw.rectangle((20 + index * 8, 20, 70 + index * 8, 70), fill="#df4141")
            else:
                draw.rectangle((30, 20, 80, 70), fill="#7f7f7f")
            image.save(directory / f"frame_{index:03d}.png")
        return directory

    def test_image_sequence_preserves_duration_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = ingest(
                IngestOptions("GPC-TEST-STILLNESS", root / "bundles", image_dir=self._image_sequence(root), image_fps=2.0),
                "unused",
            )
            result = validate_bundle(output)
            self.assertTrue(result.passed, result.errors)
            timeline = load_yaml(output / "timeline.yaml")
            guard = timeline["segments"][0]["duration_evidence_guard"]
            self.assertEqual(guard["status"], "protected_duration_evidence")
            self.assertIn("hold_start_s", guard)
            self.assertIn("hold_middle_s", guard)
            self.assertIn("release_s", guard)
            evidence = list((output / "frames" / "keyframes").glob("*duration_evidence.webp"))
            self.assertGreaterEqual(len(evidence), 3)
            self.assertTrue((output / "director_pull.md").is_file())

    def test_seconds_first_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = ingest(
                IngestOptions("GPC-TEST-NAMING", root / "bundles", image_dir=self._image_sequence(root), image_fps=2.0),
                "unused",
            )
            for path in (output / "frames").rglob("*.webp"):
                self.assertIn("__t_", path.name)
                self.assertNotIn("frame_", path.name)
            self.assertTrue(validate_bundle(output).passed)

    def test_shot_segmentation_detects_hard_cut_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sequence = root / "cut-images"
            sequence.mkdir()
            for index in range(8):
                Image.new("RGB", (160, 90), "black" if index < 4 else "white").save(sequence / f"input_{index:03d}.png")
            output = ingest(IngestOptions("GPC-TEST-CUT", root / "bundles", image_dir=sequence, image_fps=2.0), "unused")
            timeline = load_yaml(output / "timeline.yaml")
            self.assertGreaterEqual(len(timeline["segments"]), 2)
            self.assertIn("hard_cut_candidate", [segment["transition_candidate"] for segment in timeline["segments"]])
            self.assertTrue(validate_bundle(output).passed)

    def test_prompt_boundary_and_validator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.txt"
            reconstruction = root / "reconstructed.txt"
            source.write_text("verbatim source prompt", encoding="utf-8")
            reconstruction.write_text("inferred candidate prompt", encoding="utf-8")
            output = ingest(
                IngestOptions(
                    "GPC-TEST-PROMPT",
                    root / "bundles",
                    image_dir=self._image_sequence(root),
                    image_fps=2.0,
                    source_prompt_file=source,
                    reconstructed_prompt_file=reconstruction,
                ),
                "unused",
            )
            self.assertTrue(validate_bundle(output).passed)
            case = load_yaml(output / "case.yaml")
            self.assertEqual(case["prompt_provenance"]["source_prompt_provenance"], "user_supplied_verbatim")
            self.assertEqual(case["prompt_provenance"]["reconstructed_prompt"]["provenance"], "inferred_from_media")
            case["prompt_provenance"]["reconstructed_prompt"]["provenance"] = "source_prompt"
            dump_yaml(output / "case.yaml", case)
            self.assertFalse(validate_bundle(output).passed)

    def test_video_fixture_audio_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "fixture.mp4"
            ffmpeg = resolve_ffmpeg()
            run(
                [
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=8:duration=2",
                    "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=16000:duration=2",
                    "-shortest", "-c:v", "mpeg4", "-q:v", "5", "-c:a", "aac", str(video),
                ]
            )
            output = ingest(IngestOptions("GPC-TEST-AUDIO", root / "bundles", video=video), ffmpeg)
            result = validate_bundle(output)
            self.assertTrue(result.passed, result.errors)
            audio = load_yaml(output / "audio_events.yaml")
            self.assertTrue(audio["audio_present"])
            self.assertEqual(audio["asr"]["status"], "deferred_no_configured_backend")
            self.assertIn("onset_candidates", audio)

    def test_regression_mapping_references_current_cases(self) -> None:
        mapping = load_yaml(PACKAGE_ROOT / "REGRESSION_MAPPING.yaml")
        repo_root = PACKAGE_ROOT.parents[1]
        current = load_yaml(repo_root / "11_验收" / "golden_case_director_pull_regression_cases.yaml")
        case_ids = {item["id"] for item in current["cases"]}
        for item in mapping["automatic_coverage"]:
            self.assertIn(item["regression_id"], case_ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
