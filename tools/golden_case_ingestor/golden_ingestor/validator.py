from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .util import filename_timestamps, load_yaml


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def passed(self) -> bool:
        return not self.errors


def validate_bundle(bundle: Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    required = ["case.yaml", "retrieval_card.yaml", "timeline.yaml", "ingest_manifest.yaml", "audio_events.yaml", "director_pull.md"]
    for name in required:
        if not (bundle / name).is_file():
            errors.append(f"missing required bundle file: {name}")
    if errors:
        return ValidationResult(errors, warnings)
    case = load_yaml(bundle / "case.yaml")
    retrieval = load_yaml(bundle / "retrieval_card.yaml")
    timeline = load_yaml(bundle / "timeline.yaml")
    manifest = load_yaml(bundle / "ingest_manifest.yaml")
    audio = load_yaml(bundle / "audio_events.yaml")
    case_id = case.get("case_id")
    if not case_id:
        errors.append("case.yaml lacks case_id")
    for name, document in (("retrieval_card.yaml", retrieval), ("timeline.yaml", timeline), ("ingest_manifest.yaml", manifest), ("audio_events.yaml", audio)):
        if document.get("case_id") != case_id:
            errors.append(f"case_id mismatch in {name}")
    director_pull = (bundle / "director_pull.md").read_text(encoding="utf-8")
    if f"case_id: {case_id}" not in director_pull:
        errors.append("case_id mismatch in director_pull.md")
    duration_s = case.get("media_metadata", {}).get("duration_s")
    if not isinstance(duration_s, (float, int)) or duration_s < 0:
        errors.append("case.yaml lacks non-negative media_metadata.duration_s")
        duration_s = 0.0
    prompt = case.get("prompt_provenance", {})
    if prompt.get("source_prompt_present") and not (bundle / "source_prompt.txt").is_file():
        errors.append("source_prompt_present but source_prompt.txt is missing")
    reconstructed = prompt.get("reconstructed_prompt", {})
    if reconstructed.get("present"):
        if reconstructed.get("provenance") != "inferred_from_media":
            errors.append("reconstructed_prompt lacks inferred_from_media provenance")
        if not (bundle / "reconstructed_prompt.txt").is_file():
            errors.append("reconstructed_prompt marked present but file is missing")
    if (bundle / "source_prompt.txt").exists() and (bundle / "reconstructed_prompt.txt").exists():
        if (bundle / "source_prompt.txt").read_bytes() == (bundle / "reconstructed_prompt.txt").read_bytes():
            warnings.append("source and reconstructed prompt have identical bytes; retained separately but review provenance")
    pair_verified = prompt.get("prompt_output_pair_verified") is True
    if pair_verified and not prompt.get("source_prompt_present"):
        errors.append("prompt_output_pair_verified requires a source prompt")
    if case.get("evidence_ladder") == "M2_prompt_output_pair" and not (pair_verified and prompt.get("source_prompt_present")):
        errors.append("M2_prompt_output_pair requires verified prompt/media provenance")
    if case.get("evidence_ladder") == "M1_media_observation" and pair_verified:
        errors.append("verified prompt/media pair must be represented as M2")
    _check_source_provenance(case.get("source", {}), errors)
    if case.get("case_status") != "ingested_evidence_not_registered":
        errors.append("ingestor must not auto-register a Golden Case")
    boundaries = case.get("boundaries", {})
    if not boundaries.get("does_not_register_formal_visual_asset"):
        errors.append("formal asset registration boundary is missing")
    if not boundaries.get("does_not_assert_prompt_causality_from_observed_sequence"):
        errors.append("observed sequence prompt-causality boundary is missing")
    _check_timeline(bundle, timeline, duration_s, errors)
    _check_frame_filenames(bundle, duration_s, errors)
    _check_audio(audio, duration_s, errors)
    _check_persistent_path_privacy(bundle, errors)
    return ValidationResult(errors, warnings)


def _check_timeline(bundle: Path, timeline: dict[str, Any], duration_s: float, errors: list[str]) -> None:
    segments = timeline.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append("timeline has no segments")
        return
    owned_timestamps: set[float] = set()
    for index, segment in enumerate(segments):
        start, end = segment.get("start_s"), segment.get("end_s")
        label = segment.get("segment_id", "unknown segment")
        is_final = index == len(segments) - 1
        if not _valid_range(start, end, duration_s):
            errors.append(f"{label} has timestamp outside video range")
        for ref in segment.get("frame_refs", []):
            frame = bundle / ref
            if not frame.is_file():
                errors.append(f"{label} references missing frame: {ref}")
                continue
            parsed = filename_timestamps(frame)
            if parsed and not _in_filename_range(parsed[0], duration_s):
                errors.append(f"frame timestamp outside video range: {ref}")
        evidence = segment.get("frame_evidence", [])
        if not evidence:
            errors.append(f"{label} lacks machine-readable frame ownership evidence")
        for item in evidence:
            timestamp = item.get("timestamp_s")
            if not isinstance(timestamp, (float, int)) or timestamp < start or (timestamp > end if is_final else timestamp >= end):
                errors.append(f"{label} owns a frame outside its declared interval")
                continue
            if timestamp in owned_timestamps:
                errors.append(f"frame timestamp is owned by more than one shot: {timestamp}")
            owned_timestamps.add(timestamp)
        if index > 0 and not any(abs(item.get("timestamp_s", -1) - start) < 1e-6 for item in evidence):
            errors.append(f"{label} does not own its cut-point frame")
        if "motion_candidates" in segment:
            errors.append(f"{label} must not label pixel deltas as motion candidates")
        guard = segment.get("duration_evidence_guard", {})
        if guard.get("status") == "low_motion_hold_candidate":
            needed = ("hold_start_s", "hold_middle_s", "first_micro_change_s", "threshold_s", "release_s")
            if any(value not in guard for value in needed):
                errors.append(f"{label} lacks required duration evidence guard fields")
            for value in needed:
                if value in guard and not _in_range(guard[value], duration_s):
                    errors.append(f"{label} duration evidence timestamp outside video range")
            for value in needed:
                timestamp = guard.get(value)
                if timestamp is not None and not any(f"__t_{timestamp:.3f}s__duration_evidence" in ref for ref in segment.get("frame_refs", [])):
                    errors.append(f"{label} duration evidence frame missing for {value}")


def _check_frame_filenames(bundle: Path, duration_s: float, errors: list[str]) -> None:
    for frame in (bundle / "frames").rglob("*") if (bundle / "frames").exists() else []:
        if not frame.is_file():
            continue
        if frame.name.startswith(("frame_", "f000")):
            errors.append(f"frame-first filename is forbidden: {frame.relative_to(bundle)}")
        parsed = filename_timestamps(frame)
        if not parsed:
            errors.append(f"frame evidence lacks seconds-first filename: {frame.relative_to(bundle)}")
        elif not _in_filename_range(parsed[0], duration_s) or (parsed[1] is not None and not _in_filename_range(parsed[1], duration_s)):
            errors.append(f"filename timestamp outside video range: {frame.relative_to(bundle)}")


def _check_audio(audio: dict[str, Any], duration_s: float, errors: list[str]) -> None:
    for field in ("silence_regions", "low_density_regions", "peak_candidates", "onset_candidates"):
        for event in audio.get(field, []):
            if not _valid_range(event.get("start_s"), event.get("end_s"), duration_s):
                errors.append(f"audio {field} timestamp outside video range")
    for segment in audio.get("asr", {}).get("segments", []):
        if not _valid_range(segment.get("start_s"), segment.get("end_s"), duration_s):
            errors.append("ASR timestamp outside video range")


def _check_source_provenance(source: dict[str, Any], errors: list[str]) -> None:
    for field in ("source_display_filename", "source_hash", "source_origin_type", "source_rights_status", "persistence_permission_status"):
        if not source.get(field):
            errors.append(f"source provenance lacks {field}")
    if source.get("source_origin_type") in {"third_party", "third_party_public", "external"}:
        if source.get("source_rights_status") in {None, "", "not_provided", "unknown"}:
            errors.append("third-party source requires explicit source_rights_status")
        if source.get("persistence_permission_status") in {None, "", "not_provided", "unknown"}:
            errors.append("third-party source requires explicit persistence_permission_status")


_LOCAL_ABSOLUTE_PATH = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:[\\/]|file://(?:/[A-Za-z]:|/)?|/(?:home|Users)/)", re.IGNORECASE)


def _check_persistent_path_privacy(bundle: Path, errors: list[str]) -> None:
    for path in bundle.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".yaml", ".yml", ".md", ".txt"}:
            continue
        content = path.read_text(encoding="utf-8")
        if _LOCAL_ABSOLUTE_PATH.search(content):
            errors.append(f"persistent bundle contains local absolute path: {path.relative_to(bundle)}")


def _in_range(value: Any, duration_s: float) -> bool:
    return isinstance(value, (float, int)) and -1e-6 <= value <= duration_s + 1e-6


def _in_filename_range(value: Any, duration_s: float) -> bool:
    # Human-facing names are intentionally rounded to milliseconds.
    return isinstance(value, (float, int)) and -0.0005 <= value <= duration_s + 0.0005


def _valid_range(start: Any, end: Any, duration_s: float) -> bool:
    return _in_range(start, duration_s) and _in_range(end, duration_s) and start <= end
