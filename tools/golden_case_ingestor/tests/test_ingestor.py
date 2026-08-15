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
            self.assertEqual(guard["status"], "low_motion_hold_candidate")
            for field in ("hold_start_s", "hold_middle_s", "first_micro_change_s", "threshold_s", "release_s"):
                self.assertIn(field, guard)
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
            result = validate_bundle(output)
            self.assertTrue(result.passed, result.errors)

    def test_exact_non_grid_cut_is_refined_locally(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sequence = root / "non-grid-cut"
            sequence.mkdir()
            for index in range(48):
                Image.new("RGB", (160, 90), "black" if index < 19 else "white").save(sequence / f"input_{index:03d}.png")
            output = ingest(IngestOptions("GPC-TEST-REFINED-CUT", root / "bundles", image_dir=sequence, image_fps=16.0), "unused")
            timeline = load_yaml(output / "timeline.yaml")
            cut = next(segment for segment in timeline["segments"] if segment["transition_candidate"] == "hard_cut_candidate")
            self.assertLessEqual(abs(cut["start_s"] - 1.1875), 0.0625)
            self.assertNotEqual(cut["start_s"] % 0.5, 0.0)
            self.assertEqual(cut["boundary_refinement"]["method"], "local_frame_interval_search")
            result = validate_bundle(output)
            self.assertTrue(result.passed, result.errors)

    def test_cut_frame_is_owned_only_by_new_shot_and_precut_evidence_survives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sequence = root / "ownership-cut"
            sequence.mkdir()
            for index in range(48):
                Image.new("RGB", (160, 90), "black" if index < 19 else "white").save(sequence / f"input_{index:03d}.png")
            output = ingest(IngestOptions("GPC-TEST-OWNERSHIP", root / "bundles", image_dir=sequence, image_fps=16.0), "unused")
            timeline = load_yaml(output / "timeline.yaml")
            previous, next_shot = timeline["segments"][:2]
            self.assertEqual(previous["frame_ownership"], "[start_s,end_s)")
            self.assertEqual(next_shot["frame_ownership"], "[start_s,end_s]")
            self.assertFalse(any("__t_1.188s__" in reference for reference in previous["frame_refs"]))
            self.assertTrue(any("__t_1.125s__" in reference for reference in previous["frame_refs"]), "pre-cut evidence must survive")
            self.assertTrue(any("__t_1.188s__" in reference for reference in next_shot["frame_refs"]))
            self.assertTrue(validate_bundle(output).passed)

    def test_opening_interval_hard_cut_is_refined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sequence = root / "opening-cut"
            sequence.mkdir()
            for index in range(48):
                Image.new("RGB", (160, 90), "black" if index < 3 else "white").save(sequence / f"input_{index:03d}.png")
            output = ingest(IngestOptions("GPC-TEST-OPENING-CUT", root / "bundles", image_dir=sequence, image_fps=16.0), "unused")
            timeline = load_yaml(output / "timeline.yaml")
            cut = next(segment for segment in timeline["segments"] if segment["transition_candidate"] == "hard_cut_candidate")
            self.assertLessEqual(abs(cut["start_s"] - 0.1875), 0.0625)
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
            self.assertAlmostEqual(timeline["segments"][1]["start_s"], 2.0, places=3)
            result = validate_bundle(output)
            self.assertTrue(result.passed, result.errors)

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
            result = validate_bundle(output)
            self.assertTrue(result.passed, result.errors)
            case = load_yaml(output / "case.yaml")
            self.assertEqual(case["prompt_provenance"]["source_prompt_provenance"], "user_supplied_verbatim")
            self.assertEqual(case["prompt_provenance"]["reconstructed_prompt"]["provenance"], "inferred_from_media")
            self.assertEqual(case["evidence_ladder"], "M1_media_observation")
            case["prompt_provenance"]["reconstructed_prompt"]["provenance"] = "source_prompt"
            dump_yaml(output / "case.yaml", case)
            self.assertFalse(validate_bundle(output).passed)

    def test_verified_prompt_output_pair_is_m2_only_with_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.txt"
            source.write_text("verified source prompt", encoding="utf-8")
            output = ingest(
                IngestOptions(
                    "GPC-TEST-M2",
                    root / "bundles",
                    image_dir=self._image_sequence(root),
                    image_fps=2.0,
                    source_prompt_file=source,
                    prompt_output_pair_verified=True,
                ),
                "unused",
            )
            case = load_yaml(output / "case.yaml")
            self.assertEqual(case["evidence_ladder"], "M2_prompt_output_pair")
            result = validate_bundle(output)
            self.assertTrue(result.passed, result.errors)

    def test_validator_rejects_third_party_without_rights_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = ingest(
                IngestOptions(
                    "GPC-TEST-RIGHTS",
                    root / "bundles",
                    image_dir=self._image_sequence(root),
                    image_fps=2.0,
                    source_origin_type="third_party",
                    source_uri="https://example.invalid/source",
                ),
                "unused",
            )
            result = validate_bundle(output)
            self.assertFalse(result.passed)
            self.assertTrue(any("third-party source requires explicit source_rights_status" in error for error in result.errors))

    def test_third_party_rights_provenance_passes_when_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = ingest(
                IngestOptions(
                    "GPC-TEST-RIGHTS-EXPLICIT",
                    root / "bundles",
                    image_dir=self._image_sequence(root),
                    image_fps=2.0,
                    source_origin_type="third_party",
                    source_uri="https://example.invalid/source",
                    source_rights_status="license_review_required",
                    persistence_permission_status="derived_evidence_allowed",
                ),
                "unused",
            )
            result = validate_bundle(output)
            self.assertTrue(result.passed, result.errors)

    def test_continuous_startup_motion_does_not_cut(self) -> None:
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
            timeline = load_yaml(output / "timeline.yaml")
            self.assertEqual(len(timeline["segments"]), 1, "continuous high-motion testsrc2 must not become multiple hard cuts")
            self.assertNotIn("motion_candidates", timeline["segments"][0])
            self.assertIn("unclassified_visual_change_candidates", timeline["segments"][0])
            self.assertEqual(timeline["segments"][0]["duration_evidence_guard"]["status"], "generic_temporal_anchor")
            self.assertFalse(any("duration_evidence" in path.name for path in (output / "frames" / "keyframes").glob("*.webp")))

    def test_validator_prevents_persistent_local_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = ingest(IngestOptions("GPC-TEST-PRIVACY", root / "bundles", image_dir=self._image_sequence(root), image_fps=2.0), "unused")
            persistent_text = "\n".join(path.read_text(encoding="utf-8") for path in output.rglob("*") if path.suffix.lower() in {".yaml", ".md", ".txt"})
            self.assertNotIn(str(root), persistent_text)
            case = load_yaml(output / "case.yaml")
            case["source"]["source_uri"] = r"C:\Users\Example\private.mp4"
            dump_yaml(output / "case.yaml", case)
            result = validate_bundle(output)
            self.assertFalse(result.passed)
            self.assertTrue(any("persistent bundle contains local absolute path" in error for error in result.errors))

    def test_validator_rejects_missing_referenced_frame(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = ingest(IngestOptions("GPC-TEST-NEGATIVE", root / "bundles", image_dir=self._image_sequence(root), image_fps=2.0), "unused")
            timeline = load_yaml(output / "timeline.yaml")
            timeline["segments"][0]["frame_refs"][0] = "frames/keyframes/missing.webp"
            dump_yaml(output / "timeline.yaml", timeline)
            self.assertFalse(validate_bundle(output).passed)

    def test_regression_mapping_references_current_cases(self) -> None:
        mapping = load_yaml(PACKAGE_ROOT / "REGRESSION_MAPPING.yaml")
        repo_root = PACKAGE_ROOT.parents[1]
        current = load_yaml(repo_root / "11_验收" / "golden_case_director_pull_regression_cases.yaml")
        case_ids = {item["id"] for item in current["cases"]}
        for item in mapping["automatic_coverage"]:
            self.assertIn(item["regression_id"], case_ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
