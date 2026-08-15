from __future__ import annotations

import array
import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageDraw, ImageStat


@dataclass(frozen=True)
class FrameSample:
    timestamp_s: float
    path: Path
    visual_delta: float = 0.0
    histogram_distance: float = 0.0
    changed_block_ratio: float = 0.0


def load_image_metric(path: Path) -> Image.Image:
    with Image.open(path) as source:
        image = source.convert("RGB")
        image.thumbnail((160, 90))
        return image.copy()


def image_delta(a: Path, b: Path) -> float:
    return frame_change_metrics(a, b)["pixel_delta"]


def frame_change_metrics(a: Path, b: Path) -> dict[str, float]:
    left, right = load_image_metric(a), load_image_metric(b)
    if left.size != right.size:
        right = right.resize(left.size)
    difference = ImageChops.difference(left, right)
    pixel_delta = sum(ImageStat.Stat(difference).mean) / 3
    left_histogram = left.convert("L").histogram()
    right_histogram = right.convert("L").histogram()
    pixel_count = left.width * left.height
    histogram_distance = sum(abs(first - second) for first, second in zip(left_histogram, right_histogram)) / pixel_count
    changed_blocks = 0
    for row in range(4):
        for column in range(4):
            box = (column * left.width // 4, row * left.height // 4, (column + 1) * left.width // 4, (row + 1) * left.height // 4)
            block_delta = sum(ImageStat.Stat(difference.crop(box)).mean) / 3
            if block_delta >= 12.0:
                changed_blocks += 1
    return {
        "pixel_delta": round(pixel_delta, 4),
        "histogram_distance": round(histogram_distance, 6),
        "changed_block_ratio": round(changed_blocks / 16, 4),
    }


def baseline_timestamps(duration_s: float, interval_s: float = 0.5) -> list[float]:
    timestamps = [round(index * interval_s, 6) for index in range(int(math.floor(duration_s / interval_s)) + 1)]
    final = round(duration_s, 6)
    if not timestamps or timestamps[-1] != final:
        timestamps.append(final)
    return sorted(set(timestamps))


def infer_shots(samples: list[FrameSample], duration_s: float, reader=None, local_interval_s: float = 0.125) -> tuple[list[dict], list[FrameSample]]:
    """Find editorial-cut candidates, then refine every coarse candidate locally."""
    boundaries = [0.0]
    refined_samples: list[FrameSample] = []
    for index, sample in enumerate(samples[1:], 1):
        # The first baseline interval has no preceding change interval, so it
        # cannot establish an editorial discontinuity rather than startup motion.
        if index < 2:
            continue
        before_score = _cut_score(samples[index - 1])
        after_score = _cut_score(samples[index + 1]) if index + 1 < len(samples) else 0.0
        score = _cut_score(sample)
        if not _is_coarse_cut(sample, score, before_score, after_score):
            continue
        boundary, _, local = _refine_boundary(reader, samples[index - 1].timestamp_s, sample.timestamp_s, local_interval_s, sample)
        if boundary > boundaries[-1] + 1e-6 and boundary < duration_s - 1e-6:
            boundaries.append(boundary)
            refined_samples.extend(local)
    if duration_s > boundaries[-1]:
        boundaries.append(round(duration_s, 6))
    shots: list[dict] = []
    for index, start in enumerate(boundaries[:-1], 1):
        end = boundaries[index]
        local = next((sample for sample in refined_samples if abs(sample.timestamp_s - start) < 1e-6), None)
        shots.append(
            {
                "shot_id": f"SHOT-{index:03d}",
                "start_s": start,
                "end_s": end,
                "duration_s": round(end - start, 6),
                "transition_candidate": "hard_cut_candidate" if index > 1 else "source_start",
                "transition_confidence": round(_cut_score(local) if local else (1.0 if index == 1 else 0.5), 3),
                "boundary_refinement": {
                    "method": "local_frame_interval_search",
                    "refined_boundary_s": start,
                    "local_interval_s": local_interval_s,
                } if index > 1 else None,
            }
        )
    if not shots:
        shots.append(
            {
                "shot_id": "SHOT-001",
                "start_s": 0.0,
                "end_s": round(duration_s, 6),
                "duration_s": round(duration_s, 6),
                "transition_candidate": "source_start",
                "transition_confidence": 1.0,
            }
        )
    return shots, refresh_metrics(refined_samples)


def _cut_score(sample: FrameSample | None) -> float:
    if sample is None:
        return 0.0
    return round(
        0.25 * min(1.0, sample.visual_delta / 80.0)
        + 0.55 * min(1.0, sample.histogram_distance / 0.8)
        + 0.20 * sample.changed_block_ratio,
        6,
    )


def _is_coarse_cut(sample: FrameSample, score: float, before_score: float, after_score: float) -> bool:
    is_global_discontinuity = sample.histogram_distance >= 0.35 and sample.changed_block_ratio >= 0.65
    is_local_peak = score >= 0.45 and score >= before_score * 1.2 and score >= after_score * 1.2
    return is_global_discontinuity and is_local_peak


def _refine_boundary(reader, start_s: float, end_s: float, interval_s: float, fallback: FrameSample) -> tuple[float, float, list[FrameSample]]:
    if reader is None or interval_s <= 0:
        return fallback.timestamp_s, _cut_score(fallback), [fallback]
    timestamps = [start_s]
    current = start_s + interval_s
    while current <= end_s + 1e-6:
        timestamps.append(round(min(current, end_s), 6))
        current += interval_s
    local = refresh_metrics([FrameSample(timestamp_s=timestamp, path=reader(timestamp)) for timestamp in sorted(set(timestamps))])
    strongest = max(local[1:], key=_cut_score, default=fallback)
    return strongest.timestamp_s, _cut_score(strongest), local


def dense_timestamps(samples: list[FrameSample], shots: list[dict], dense_interval_s: float = 0.125) -> set[float]:
    points: set[float] = set()
    for shot in shots:
        points.update({shot["start_s"], shot["end_s"], round((shot["start_s"] + shot["end_s"]) / 2, 6)})
    for sample in samples[1:]:
        if sample.visual_delta >= 9.0:
            for offset in (-dense_interval_s, 0.0, dense_interval_s):
                candidate = round(sample.timestamp_s + offset, 6)
                if 0 <= candidate <= samples[-1].timestamp_s:
                    points.add(candidate)
    return points


def duration_evidence_guard(samples: list[FrameSample], shot: dict) -> tuple[dict[float, str], dict]:
    inside = [s for s in samples if shot["start_s"] <= s.timestamp_s <= shot["end_s"]]
    if not inside:
        return {}, {"status": "not_observed"}
    start, end = shot["start_s"], shot["end_s"]
    middle = round((start + end) / 2, 6)
    changes = [s for s in inside if s.visual_delta >= 3.0]
    first = changes[0].timestamp_s if changes else None
    threshold = max(inside, key=lambda s: s.visual_delta).timestamp_s if changes else None
    low_motion_candidate = (
        shot["duration_s"] >= 0.5
        and bool(changes)
        and sum(sample.visual_delta < 3.0 for sample in inside[1:]) >= max(1, len(inside[1:]) // 2)
    )
    if not low_motion_candidate:
        return {start: "temporal_anchor", middle: "temporal_anchor", end: "temporal_anchor"}, {
            "status": "generic_temporal_anchor",
            "anchor_start_s": start,
            "anchor_middle_s": middle,
            "anchor_end_s": end,
            "note": "No low-motion hold candidate was detected; anchors preserve ordinary temporal orientation only.",
        }
    protected = {start: "duration_evidence", middle: "duration_evidence", end: "duration_evidence"}
    for value in (first, threshold):
        if value is not None:
            protected[value] = "duration_evidence"
    return protected, {
        "status": "low_motion_hold_candidate",
        "hold_start_s": start,
        "hold_middle_s": middle,
        "first_micro_change_s": first,
        "threshold_s": threshold,
        "release_s": end,
        "confidence": 0.55 if changes else 0.3,
        "note": "Mechanical guard; GPT determines whether this is high-information performance.",
    }


def refresh_metrics(samples: list[FrameSample]) -> list[FrameSample]:
    refreshed = []
    previous = None
    for sample in sorted(samples, key=lambda item: item.timestamp_s):
        metrics = frame_change_metrics(previous.path, sample.path) if previous else {"pixel_delta": 0.0, "histogram_distance": 0.0, "changed_block_ratio": 0.0}
        refreshed.append(FrameSample(sample.timestamp_s, sample.path, metrics["pixel_delta"], metrics["histogram_distance"], metrics["changed_block_ratio"]))
        previous = refreshed[-1]
    return refreshed


def deduplicate(samples: list[FrameSample], protected: set[float], threshold: float = 2.0) -> list[FrameSample]:
    kept: list[FrameSample] = []
    for sample in sorted(samples, key=lambda item: item.timestamp_s):
        if any(abs(sample.timestamp_s - item) < 1e-6 for item in protected):
            kept.append(sample)
            continue
        if not kept or image_delta(kept[-1].path, sample.path) >= threshold:
            kept.append(sample)
    return kept


def analyze_wav(wav_path: Path, window_s: float = 0.125) -> dict:
    with wave.open(str(wav_path), "rb") as handle:
        sample_rate = handle.getframerate()
        sample_width = handle.getsampwidth()
        channels = handle.getnchannels()
        if sample_width != 2:
            return {"analysis_status": "unsupported_sample_width"}
        raw = array.array("h", handle.readframes(handle.getnframes()))
    if channels > 1:
        raw = array.array("h", (raw[index] for index in range(0, len(raw), channels)))
    window = max(1, int(sample_rate * window_s))
    values = []
    for start in range(0, len(raw), window):
        chunk = raw[start : start + window]
        if not chunk:
            continue
        rms = math.sqrt(sum(sample * sample for sample in chunk) / len(chunk)) / 32768.0
        values.append((round(start / sample_rate, 6), round(min((start + len(chunk)) / sample_rate, len(raw) / sample_rate), 6), rms))
    peak = max((entry[2] for entry in values), default=0.0)
    silence_cutoff = max(0.002, peak * 0.08)
    low_cutoff = max(0.006, peak * 0.18)
    silence = _join_audio_regions(values, lambda rms: rms <= silence_cutoff)
    low_density = _join_audio_regions(values, lambda rms: rms <= low_cutoff)
    peaks = [
        {"start_s": start, "end_s": end, "rms": round(rms, 6), "confidence": round(rms / peak, 3) if peak else 0.0}
        for start, end, rms in values
        if peak and rms >= peak * 0.8
    ]
    onsets = []
    previous = 0.0
    for start, end, rms in values:
        if rms - previous >= max(0.03, peak * 0.25):
            onsets.append(
                {
                    "start_s": start,
                    "end_s": end,
                    "event_type": "unclassified_audio_onset_candidate",
                    "loudness_delta": round(rms - previous, 6),
                    "confidence": round(min(1.0, (rms - previous) / max(peak, 0.001)), 3),
                }
            )
        previous = rms
    return {
        "analysis_status": "measured_pcm_rms",
        "window_s": window_s,
        "peak_rms": round(peak, 6),
        "silence_regions": silence,
        "low_density_regions": low_density,
        "peak_candidates": peaks,
        "onset_candidates": onsets,
    }


def _join_audio_regions(values: Iterable[tuple[float, float, float]], predicate) -> list[dict]:
    regions = []
    active = None
    for start, end, rms in values:
        if predicate(rms):
            if active is None:
                active = [start, end]
            else:
                active[1] = end
        elif active:
            if active[1] - active[0] >= 0.25:
                regions.append({"start_s": active[0], "end_s": active[1], "duration_s": round(active[1] - active[0], 6)})
            active = None
    if active and active[1] - active[0] >= 0.25:
        regions.append({"start_s": active[0], "end_s": active[1], "duration_s": round(active[1] - active[0], 6)})
    return regions


def make_contact_sheet(samples: list[FrameSample], destination: Path, columns: int = 4) -> None:
    if len(samples) > 12:
        indexes = {round(index * (len(samples) - 1) / 11) for index in range(12)}
        samples = [sample for index, sample in enumerate(samples) if index in indexes]
    tiles = []
    for sample in samples:
        with Image.open(sample.path) as source:
            tile = source.convert("RGB")
            tile.thumbnail((320, 180))
            canvas = Image.new("RGB", (320, 212), "black")
            canvas.paste(tile, ((320 - tile.width) // 2, 0))
            ImageDraw.Draw(canvas).text((8, 188), f"t={sample.timestamp_s:.3f}s", fill="white")
            tiles.append(canvas)
    if not tiles:
        return
    rows = math.ceil(len(tiles) / columns)
    sheet = Image.new("RGB", (columns * 320, rows * 212), "black")
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % columns) * 320, (index // columns) * 212))
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, "WEBP", quality=85, method=6)
