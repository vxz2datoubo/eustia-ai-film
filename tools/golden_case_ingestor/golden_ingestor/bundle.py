from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from .analysis import (
    FrameSample,
    analyze_wav,
    baseline_timestamps,
    deduplicate,
    dense_timestamps,
    duration_evidence_guard,
    infer_shots,
    make_contact_sheet,
    refresh_metrics,
)
from .media import decode_audio_to_wav, extract_video_frame, probe_video
from .util import dump_yaml, interval_filename, run, seconds_filename, sha256_file


@dataclass
class IngestOptions:
    case_id: str
    output_root: Path
    video: Path | None = None
    image_dir: Path | None = None
    image_fps: float | None = None
    source_prompt_file: Path | None = None
    reconstructed_prompt_file: Path | None = None
    context_file: Path | None = None
    asr_command: list[str] | None = None
    explicit_golden_intent: bool = False
    prompt_output_pair_verified: bool = False
    source_origin_type: str = "user_supplied"
    source_uri: str | None = None
    source_rights_status: str = "not_provided"
    persistence_permission_status: str = "derived_evidence_only"


def ingest(options: IngestOptions, ffmpeg: str) -> Path:
    if bool(options.video) == bool(options.image_dir):
        raise ValueError("Provide exactly one of --video or --image-dir")
    if not options.case_id.startswith("GPC-"):
        raise ValueError("case_id must start with GPC-")
    if options.prompt_output_pair_verified and not options.source_prompt_file:
        raise ValueError("--prompt-output-pair-verified requires --source-prompt-file")
    output = options.output_root / options.case_id
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing bundle: {output}")
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="golden-ingestor-") as temp_name:
        temp = Path(temp_name)
        if options.video:
            metadata = probe_video(options.video, ffmpeg)
            duration_s = metadata["duration_s"]
            get_frame = _video_frame_reader(ffmpeg, options.video, temp / "decoded", duration_s, metadata.get("fps"))
            source = _source_provenance(options, "video", str(options.video), metadata["sha256"])
        else:
            image_paths = _image_paths(options.image_dir)
            if not image_paths:
                raise ValueError("image_dir contains no supported images")
            if not options.image_fps or options.image_fps <= 0:
                raise ValueError("--image-fps must be positive for an image sequence")
            duration_s = round(max(0, len(image_paths) - 1) / options.image_fps, 6)
            metadata = {
                "duration_s": duration_s,
                "fps": options.image_fps,
                "width": _image_dimensions(image_paths[0])[0],
                "height": _image_dimensions(image_paths[0])[1],
                "frame_count": len(image_paths),
                "frame_count_method": "image_sequence_count",
                "audio_present": False,
                "metadata_probe": "image_sequence",
                "sha256": _sequence_hash(image_paths),
            }
            get_frame = _image_frame_reader(image_paths, options.image_fps, temp / "decoded")
            source = _source_provenance(options, "image_sequence", str(options.image_dir), metadata["sha256"])

        baseline = _sample(get_frame, baseline_timestamps(duration_s))
        baseline = _refresh_deltas(baseline)
        local_interval_s = round(1.0 / metadata["fps"], 6) if metadata.get("fps") else 0.125
        shots, boundary_samples = infer_shots(baseline, duration_s, get_frame, local_interval_s)
        audio = _audio_evidence(options, ffmpeg, temp) if options.video and metadata["audio_present"] else _no_audio_evidence()

        candidate_times = set(item.timestamp_s for item in baseline)
        candidate_times.update(item.timestamp_s for item in boundary_samples)
        candidate_times.update(dense_timestamps(baseline, shots))
        for event in audio.get("onset_candidates", []):
            for offset in (-0.125, 0.0, 0.125):
                candidate_times.add(round(max(0.0, min(duration_s, event["start_s"] + offset)), 6))
        all_samples = _refresh_deltas(_sample(get_frame, sorted(candidate_times)))
        duration_guards: dict[str, dict] = {}
        protected_roles: dict[float, str] = {}
        for shot in shots:
            roles, guard = duration_evidence_guard(all_samples, shot)
            duration_guards[shot["shot_id"]] = guard
            for point, role in roles.items():
                if role == "duration_evidence" or point not in protected_roles:
                    protected_roles[point] = role
        protected = set(protected_roles)
        selected = deduplicate(all_samples, protected)
        frame_refs = _persist_frames(options.case_id, output, selected, protected_roles, candidate_times - set(item.timestamp_s for item in baseline))
        _persist_contact_sheets(options.case_id, output, shots, selected)

        timeline = _timeline(options.case_id, shots, selected, frame_refs, audio, duration_guards)
        audio["case_id"] = options.case_id
        prompts = _persist_prompts(options, output)
        context = _persist_context(options.context_file, output)
        manifest = {
            "schema": "10_运行时/golden_media_evidence_schema.yaml",
            "tool": {"name": "golden_case_ingestor", "version": "0.1.0", "deterministic_where_practical": True},
            "case_id": options.case_id,
            "source": source,
            "metadata": metadata,
            "sampling": {
                "baseline_interval_s": 0.5,
                "dense_interval_s": 0.125,
                "baseline_role": "recall_safety_net_not_persistence_requirement",
                "dedup": "perceptual_delta_with_duration_evidence_guard",
            },
            "source_video_retained": False,
            "formal_asset_registration": "not_attempted",
            "director_interpretation": "not_generated",
            "prompt_causality": "not_claimed_by_ingestor",
            "files": sorted(path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()),
        }
        case = {
            "case_id": options.case_id,
            "case_status": "ingested_evidence_not_registered",
            "explicit_golden_case_intent": options.explicit_golden_intent,
            "evidence_ladder": "M2_prompt_output_pair" if prompts["prompt_output_pair_verified"] else "M1_media_observation",
            "source": source,
            "media_metadata": metadata,
            "prompt_provenance": prompts,
            "context_provenance": context,
            "director_pull": {"status": "pending_gpt_completion", "path": "director_pull.md"},
            "boundaries": {
                "does_not_register_formal_visual_asset": True,
                "does_not_assert_director_interpretation": True,
                "does_not_assert_prompt_causality_from_observed_sequence": True,
            },
        }
        retrieval = {
            "case_id": options.case_id,
            "status": "evidence_only_pending_gpt_director_pull",
            "source_type": source["input_type"],
            "duration_s": duration_s,
            "shot_ids": [shot["shot_id"] for shot in shots],
            "available_evidence": ["timeline.yaml", "audio_events.yaml", "frames/contact_sheets", "frames/keyframes"],
            "director_interpretation": "pending_gpt_completion",
            "reconstructed_prompt": prompts["reconstructed_prompt"],
        }
        dump_yaml(output / "case.yaml", case)
        dump_yaml(output / "retrieval_card.yaml", retrieval)
        dump_yaml(output / "timeline.yaml", timeline)
        dump_yaml(output / "audio_events.yaml", audio)
        _write_director_pull_stub(output, options.case_id)
        manifest["files"] = sorted(
            {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()} | {"ingest_manifest.yaml"}
        )
        dump_yaml(output / "ingest_manifest.yaml", manifest)
    return output


def _video_frame_reader(ffmpeg: str, video: Path, directory: Path, duration_s: float, fps: float | None) -> Callable[[float], Path]:
    cache: dict[float, Path] = {}

    def reader(timestamp_s: float) -> Path:
        timestamp_s = round(timestamp_s, 6)
        if timestamp_s not in cache:
            destination = directory / f"sample_{timestamp_s:.6f}.png"
            # A demuxer commonly has no decodable frame at exact duration.  The
            # evidence coordinate remains the segment endpoint while decoding
            # uses the last available frame.
            seek_s = min(timestamp_s, max(0.0, duration_s - (1.0 / fps if fps else 0.001)))
            extract_video_frame(ffmpeg, video, seek_s, destination)
            cache[timestamp_s] = destination
        return cache[timestamp_s]

    return reader


def _image_paths(directory: Path) -> list[Path]:
    return sorted(path for path in directory.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"})


def _image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.width, image.height


def _sequence_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def _image_frame_reader(paths: list[Path], fps: float, directory: Path) -> Callable[[float], Path]:
    cache: dict[float, Path] = {}

    def reader(timestamp_s: float) -> Path:
        timestamp_s = round(timestamp_s, 6)
        if timestamp_s not in cache:
            index = min(len(paths) - 1, max(0, round(timestamp_s * fps)))
            destination = directory / f"sample_{timestamp_s:.6f}.png"
            destination.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(paths[index]) as source:
                source.convert("RGB").save(destination, "PNG")
            cache[timestamp_s] = destination
        return cache[timestamp_s]

    return reader


def _sample(reader: Callable[[float], Path], timestamps: list[float]) -> list[FrameSample]:
    return [FrameSample(timestamp_s=timestamp, path=reader(timestamp)) for timestamp in timestamps]


def _refresh_deltas(samples: list[FrameSample]) -> list[FrameSample]:
    return refresh_metrics(samples)


def _audio_evidence(options: IngestOptions, ffmpeg: str, temp: Path) -> dict:
    wav = temp / "audio.wav"
    if not decode_audio_to_wav(ffmpeg, options.video, wav):
        return {"audio_present": True, "analysis_status": "decode_failed", "asr_status": "not_attempted"}
    evidence = {"audio_present": True, **analyze_wav(wav)}
    evidence["asr"] = _run_asr(options.asr_command, wav) if options.asr_command else {
        "status": "deferred_no_configured_backend",
        "segments": [],
        "note": "No speech content is inferred without a configured timestamped ASR backend.",
    }
    return evidence


def _run_asr(command_template: list[str], wav: Path) -> dict:
    command = [part.replace("{audio}", str(wav)) for part in command_template]
    if not any(str(wav) == part for part in command):
        return {"status": "failed_invalid_command", "segments": [], "reason": "--asr-command must contain {audio}"}
    result = run(command, check=False)
    if result.returncode:
        return {"status": "failed_backend", "segments": [], "stderr": result.stderr[-1000:]}
    try:
        import json

        parsed = json.loads(result.stdout)
        segments = parsed.get("segments", parsed) if isinstance(parsed, (dict, list)) else []
        if not isinstance(segments, list):
            raise ValueError("segments is not a list")
        normalized = [
            {"start_s": float(item["start_s"]), "end_s": float(item["end_s"]), "text": str(item["text"]), "confidence": item.get("confidence")}
            for item in segments
        ]
        return {"status": "provided_external_asr", "segments": normalized}
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return {"status": "failed_invalid_asr_json", "segments": [], "reason": str(exc)}


def _no_audio_evidence() -> dict:
    return {"audio_present": False, "analysis_status": "no_audio_track", "asr": {"status": "not_applicable", "segments": []}}


def _persist_frames(case_id: str, output: Path, samples: list[FrameSample], protected_roles: dict[float, str], dense: set[float]) -> dict[float, str]:
    refs = {}
    for sample in samples:
        role = next((value for point, value in protected_roles.items() if abs(sample.timestamp_s - point) < 1e-6), "keyframe")
        name = seconds_filename(case_id, sample.timestamp_s, role)
        target = output / "frames" / "keyframes" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(sample.path) as source:
            source.convert("RGB").save(target, "WEBP", quality=88, method=6)
        refs[sample.timestamp_s] = target.relative_to(output).as_posix()
        if any(abs(sample.timestamp_s - point) < 1e-6 for point in dense):
            dense_target = output / "frames" / "dense_windows" / seconds_filename(case_id, sample.timestamp_s, "dense")
            dense_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(target, dense_target)
    return refs


def _persist_contact_sheets(case_id: str, output: Path, shots: list[dict], samples: list[FrameSample]) -> None:
    for shot in shots:
        selected = [sample for sample in samples if shot["start_s"] - 1e-6 <= sample.timestamp_s <= shot["end_s"] + 1e-6]
        target = output / "frames" / "contact_sheets" / interval_filename(case_id, shot["start_s"], shot["end_s"], "shot_contactsheet")
        make_contact_sheet(selected, target)


def _timeline(case_id: str, shots: list[dict], samples: list[FrameSample], refs: dict[float, str], audio: dict, guards: dict[str, dict]) -> dict:
    segments = []
    for shot in shots:
        in_shot = [sample for sample in samples if shot["start_s"] - 1e-6 <= sample.timestamp_s <= shot["end_s"] + 1e-6]
        changes = [
            {
                "timestamp_s": sample.timestamp_s,
                "pixel_delta": sample.visual_delta,
                "histogram_distance": sample.histogram_distance,
                "changed_block_ratio": sample.changed_block_ratio,
                "confidence": round(min(1.0, sample.visual_delta / 40), 3),
            }
            for sample in in_shot
            if sample.visual_delta >= 9.0
        ]
        audio_events = [event for event in audio.get("onset_candidates", []) if shot["start_s"] <= event["start_s"] <= shot["end_s"]]
        dialogue = [event for event in audio.get("asr", {}).get("segments", []) if shot["start_s"] <= event["start_s"] <= shot["end_s"]]
        segments.append(
            {
                "segment_id": f"SEG-{shot['shot_id'].split('-')[-1]}",
                **shot,
                "frame_refs": [refs[sample.timestamp_s] for sample in in_shot],
                "unclassified_visual_change_candidates": changes,
                "audio_events": audio_events,
                "duration_evidence_guard": guards[shot["shot_id"]],
                "dialogue": dialogue,
                "confidence": 0.5,
                "gpt_fields_pending": ["expression", "micro_expression", "performance_beat", "camera_interpretation", "director_interpretation", "dramatic_function"],
            }
        )
    return {"case_id": case_id, "coordinate_system": "seconds", "segments": segments}


def _persist_prompts(options: IngestOptions, output: Path) -> dict:
    result = {
        "source_prompt_present": False,
        "prompt_output_pair_verified": False,
        "reconstructed_prompt": {"present": False},
    }
    if options.source_prompt_file:
        shutil.copyfile(options.source_prompt_file, output / "source_prompt.txt")
        result["source_prompt_present"] = True
        result["source_prompt_path"] = "source_prompt.txt"
        result["source_prompt_provenance"] = "user_supplied_verbatim"
        result["prompt_output_pair_verified"] = options.prompt_output_pair_verified
    if options.reconstructed_prompt_file:
        shutil.copyfile(options.reconstructed_prompt_file, output / "reconstructed_prompt.txt")
        result["reconstructed_prompt"] = {"present": True, "path": "reconstructed_prompt.txt", "provenance": "inferred_from_media"}
    return result


def _source_provenance(options: IngestOptions, input_type: str, path: str, source_hash: str) -> dict:
    return {
        "input_type": input_type,
        "path": path,
        "sha256": source_hash,
        "source_origin_type": options.source_origin_type,
        "source_uri": options.source_uri,
        "source_rights_status": options.source_rights_status,
        "persistence_permission_status": options.persistence_permission_status,
    }


def _persist_context(path: Path | None, output: Path) -> dict:
    if not path:
        return {"present": False}
    destination = output / "source_context.txt"
    shutil.copyfile(path, destination)
    return {"present": True, "path": "source_context.txt", "sha256": sha256_file(path), "provenance": "user_supplied_context_verbatim"}


def _write_director_pull_stub(output: Path, case_id: str) -> None:
    (output / "director_pull.md").write_text(
        "---\n"
        f"case_id: {case_id}\n"
        "status: pending_gpt_completion\n"
        "pull_mode: observed_director_pull\n"
        "evidence_basis: seconds_grounded_temporal_bundle\n"
        "---\n\n"
        "# Director Pull Pending\n\n"
        "This stub deliberately contains no inferred psychology, dramatic function, or prompt causality. "
        "GPT must complete it from the timeline, audio evidence, contact sheets, and supplied context.\n",
        encoding="utf-8",
    )
