from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable

import yaml


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def seconds_name(value: float) -> str:
    return f"{value:.3f}"


def seconds_filename(case_id: str, seconds: float, role: str, ext: str = "webp") -> str:
    return f"{case_id}__t_{seconds_name(seconds)}s__{role}.{ext}"


def interval_filename(case_id: str, start_s: float, end_s: float, role: str, ext: str = "webp") -> str:
    return f"{case_id}__t_{seconds_name(start_s)}s-{seconds_name(end_s)}s__{role}.{ext}"


def parse_fraction(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return None


def resolve_binary(name: str, environment_name: str) -> str | None:
    configured = os.environ.get(environment_name)
    if configured and Path(configured).is_file():
        return configured
    return shutil.which(name)


def resolve_ffmpeg() -> str:
    found = resolve_binary("ffmpeg", "FFMPEG_BIN")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError(
            "ffmpeg was not found. Set FFMPEG_BIN, add ffmpeg to PATH, or install imageio-ffmpeg."
        ) from exc


def resolve_ffprobe(ffmpeg: str) -> str | None:
    found = resolve_binary("ffprobe", "FFPROBE_BIN")
    if found:
        return found
    sibling = Path(ffmpeg).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    return str(sibling) if sibling.is_file() else None


def run(command: Iterable[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(list(command), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        rendered = " ".join(map(str, command))
        raise RuntimeError(f"Command failed ({result.returncode}): {rendered}\n{result.stderr[-4000:]}")
    return result


def json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


TIMESTAMP_NAME_RE = re.compile(r"__t_(\d+\.\d{3})s(?:-(\d+\.\d{3})s)?__")


def filename_timestamps(path: Path) -> tuple[float, float | None] | None:
    match = TIMESTAMP_NAME_RE.search(path.name)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2)) if match.group(2) else None
