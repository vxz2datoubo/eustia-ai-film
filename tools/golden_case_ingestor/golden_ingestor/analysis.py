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


def load_image_metric(path: Path) -> Image.Image:
    with Image.open(path) as source:
        image = source.convert("RGB")
        image.thumbnail((160, 90))
        return image.copy()


def image_delta(a: Path, b: Path) -> float:
    left, right = load_image_metric(a), load_image_metric(b)
    if left.size != right.size:
        right = right.resize(left.size)
    return round(sum(ImageStat.Stat(ImageChops.difference(left, right)).mean) / 3, 4)


def baseline_timestamps(duration_s: float, interval_s: float = 0.5) -> list[float]:
    timestamps = [round(index * interval_s, 6) for index in range(int(math.floor(duration_s / interval_s)) + 1)]
    final = round(duration_s, 6)
    if not timestamps or timestamps[-1] != final:
        timestamps.append(final)
    return sorted(set(timestamps))


def infer_shots(samples: list[FrameSample], duration_s: float, cut_threshold: float = 28.0) -> list[dict]:
    boundaries = [0.0]
    for sample in samples[1:]:
        if sample.visual_delta >= cut_threshold and sample.timestamp_s > boundaries[-1]:
            boundaries.append(sample.timestamp_s)
    if duration_s > boundaries[-1]:
        boundaries.append(round(duration_s, 6))
    shots: list[dict] = []
    for index, start in enumerate(boundaries[:-1], 1):
        end = boundaries[index]
        adjacent = next((s for s in samples if abs(s.timestamp_s - start) < 1e-6), None)
        shots.append(
            {
                "shot_id": f"SHOT-{index:03d}",
                "start_s": start,
                "end_s": end,
                "duration_s": round(end - start, 6),
                "transition_candidate": "hard_cut_candidate" if index > 1 else "source_start",
                "transition_confidence": round(min(1.0, (adjacent.visual_delta if adjacent else 0.0) / 60), 3),
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
    return shots


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


def duration_evidence_guard(samples: list[FrameSample], shot: dict) -> tuple[set[float], dict]:
    inside = [s for s in samples if shot["start_s"] <= s.timestamp_s <= shot["end_s"]]
    if not inside:
        return set(), {"status": "not_observed"}
    start, end = shot["start_s"], shot["end_s"]
    middle = round((start + end) / 2, 6)
    changes = [s for s in inside if s.visual_delta >= 3.0]
    first = changes[0].timestamp_s if changes else None
    threshold = max(inside, key=lambda s: s.visual_delta).timestamp_s if changes else None
    protected = {start, middle, end}
    protected.update(value for value in (first, threshold) if value is not None)
    mean_delta = sum(sample.visual_delta for sample in inside) / len(inside)
    return protected, {
        "status": "protected_duration_evidence",
        "low_motion_candidate": mean_delta < 3.0,
        "hold_start_s": start,
        "hold_middle_s": middle,
        "first_micro_change_s": first,
        "threshold_s": threshold,
        "release_s": end,
        "confidence": 0.55 if changes else 0.3,
        "note": "Mechanical guard; GPT determines whether this is high-information performance.",
    }


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
