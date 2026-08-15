from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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
    return ValidationResult(errors, warnings)


def _check_timeline(bundle: Path, timeline: dict[str, Any], duration_s: float, errors: list[str]) -> None:
    segments = timeline.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append("timeline has no segments")
        return
    for segment in segments:
        start, end = segment.get("start_s"), segment.get("end_s")
        label = segment.get("segment_id", "unknown segment")
        if not _valid_range(start, end, duration_s):
            errors.append(f"{label} has timestamp outside video range")
        for ref in segment.get("frame_refs", []):
            frame = bundle / ref
            if not frame.is_file():
                errors.append(f"{label} references missing frame: {ref}")
                continue
            parsed = filename_timestamps(frame)
            if parsed and not _in_range(parsed[0], duration_s):
                errors.append(f"frame timestamp outside video range: {ref}")
        guard = segment.get("duration_evidence_guard", {})
        if guard.get("status") == "protected_duration_evidence":
            needed = ("hold_start_s", "hold_middle_s", "release_s")
            if any(value not in guard for value in needed):
                errors.append(f"{label} lacks required duration evidence guard fields")
            for value in needed:
                if value in guard and not _in_range(guard[value], duration_s):
                    errors.append(f"{label} duration evidence timestamp outside video range")


def _check_frame_filenames(bundle: Path, duration_s: float, errors: list[str]) -> None:
    for frame in (bundle / "frames").rglob("*") if (bundle / "frames").exists() else []:
        if not frame.is_file():
            continue
        if frame.name.startswith(("frame_", "f000")):
            errors.append(f"frame-first filename is forbidden: {frame.relative_to(bundle)}")
        parsed = filename_timestamps(frame)
        if not parsed:
            errors.append(f"frame evidence lacks seconds-first filename: {frame.relative_to(bundle)}")
        elif not _in_range(parsed[0], duration_s) or (parsed[1] is not None and not _in_range(parsed[1], duration_s)):
            errors.append(f"filename timestamp outside video range: {frame.relative_to(bundle)}")


def _check_audio(audio: dict[str, Any], duration_s: float, errors: list[str]) -> None:
    for field in ("silence_regions", "low_density_regions", "peak_candidates", "onset_candidates"):
        for event in audio.get(field, []):
            if not _valid_range(event.get("start_s"), event.get("end_s"), duration_s):
                errors.append(f"audio {field} timestamp outside video range")
    for segment in audio.get("asr", {}).get("segments", []):
        if not _valid_range(segment.get("start_s"), segment.get("end_s"), duration_s):
            errors.append("ASR timestamp outside video range")


def _in_range(value: Any, duration_s: float) -> bool:
    return isinstance(value, (float, int)) and -1e-6 <= value <= duration_s + 1e-6


def _valid_range(start: Any, end: Any, duration_s: float) -> bool:
    return _in_range(start, duration_s) and _in_range(end, duration_s) and start <= end
