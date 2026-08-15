from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from .util import parse_fraction, resolve_ffprobe, run, sha256_file


def probe_video(video: Path, ffmpeg: str) -> dict[str, Any]:
    """Probe metadata with ffprobe when available; use ffmpeg decode as a safe fallback."""
    ffprobe = resolve_ffprobe(ffmpeg)
    if ffprobe:
        result = run(
            [
                ffprobe,
                "-v",
                "error",
                "-count_frames",
                "-show_entries",
                "format=duration:stream=index,codec_type,width,height,avg_frame_rate,nb_read_frames",
                "-of",
                "json",
                str(video),
            ]
        )
        parsed = json.loads(result.stdout)
        streams = parsed.get("streams", [])
        visual = next((s for s in streams if s.get("codec_type") == "video"), None)
        if not visual:
            raise ValueError("No video stream was found")
        fps = parse_fraction(visual.get("avg_frame_rate"))
        frame_count_raw = visual.get("nb_read_frames")
        frame_count = int(frame_count_raw) if frame_count_raw and frame_count_raw != "N/A" else None
        return {
            "duration_s": round(float(parsed["format"]["duration"]), 6),
            "fps": round(fps, 6) if fps else None,
            "width": visual.get("width"),
            "height": visual.get("height"),
            "frame_count": frame_count,
            "frame_count_method": "ffprobe_count_frames",
            "audio_present": any(s.get("codec_type") == "audio" for s in streams),
            "metadata_probe": "ffprobe",
            "sha256": sha256_file(video),
        }
    info = run([ffmpeg, "-hide_banner", "-i", str(video)], check=False).stderr
    duration = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", info)
    visual = re.search(r"Video:.*?(\d{2,5})x(\d{2,5}).*?(\d+(?:\.\d+)?)\s*fps", info)
    if not duration or not visual:
        raise ValueError("Unable to read duration/resolution/fps through ffmpeg fallback")
    duration_s = int(duration.group(1)) * 3600 + int(duration.group(2)) * 60 + float(duration.group(3))
    fps = float(visual.group(3))
    decoded = run([ffmpeg, "-v", "info", "-i", str(video), "-map", "0:v:0", "-f", "null", "-"], check=False)
    frames = re.findall(r"frame=\s*(\d+)", decoded.stderr)
    return {
        "duration_s": round(duration_s, 6),
        "fps": fps,
        "width": int(visual.group(1)),
        "height": int(visual.group(2)),
        "frame_count": int(frames[-1]) if frames else round(duration_s * fps),
        "frame_count_method": "ffmpeg_decode_count",
        "audio_present": "Audio:" in info,
        "metadata_probe": "ffmpeg_fallback",
        "sha256": sha256_file(video),
    }


def extract_video_frame(ffmpeg: str, video: Path, timestamp_s: float, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-ss",
            f"{timestamp_s:.6f}",
            "-frames:v",
            "1",
            str(destination),
        ]
    )


def decode_audio_to_wav(ffmpeg: str, video: Path, destination: Path) -> bool:
    result = run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ],
        check=False,
    )
    return result.returncode == 0 and destination.exists()


def temporary_directory() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory(prefix="golden-ingestor-")
