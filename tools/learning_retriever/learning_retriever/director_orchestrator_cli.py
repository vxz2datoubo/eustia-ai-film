"""CLI for the bounded Director Runtime Orchestrator P0.

This command reads a creative decision packet from JSON/YAML and emits a
non-executable ``DIRECTOR_RUNTIME_CANDIDATE/v1``. It never accepts a project-root
authority override and never grants model execution or canonical-write authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import yaml

from .director_orchestrator import DirectorRuntimeError, DirectorRuntimeOrchestrator


def _load_packet(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile a CreativeDecisionPacket through Director Runtime P0"
    )
    parser.add_argument("--description", required=True)
    parser.add_argument("--creative-packet", required=True)
    parser.add_argument("--task-id", default="DIRECTOR_RUNTIME_P0_CLI")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--output", default=None, help="Optional JSON output file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    packet_path = Path(args.creative_packet)
    try:
        packet = _load_packet(packet_path)
        result = DirectorRuntimeOrchestrator().compile(
            args.description,
            packet,
            task_id=args.task_id,
            top_k=args.top_k,
        )
    except (DirectorRuntimeError, OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        if isinstance(exc, DirectorRuntimeError):
            payload = {
                "status": "FAIL",
                "code": exc.code,
                "error": exc.message,
                "details": exc.details,
            }
        else:
            payload = {
                "status": "FAIL",
                "code": "DIRECTOR_PACKET_INPUT_ERROR",
                "error": str(exc),
            }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
