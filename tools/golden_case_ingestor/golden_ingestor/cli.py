from __future__ import annotations

import argparse
from pathlib import Path

from .bundle import IngestOptions, ingest
from .util import resolve_ffmpeg
from .validator import validate_bundle


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="golden_ingestor", description="Golden Case deterministic temporal-evidence ingestor")
    commands = root.add_subparsers(dest="command", required=True)
    ingest_parser = commands.add_parser("ingest", help="create a temporal evidence bundle")
    ingest_parser.add_argument("--case-id", required=True)
    source = ingest_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--video", type=Path)
    source.add_argument("--image-dir", type=Path)
    ingest_parser.add_argument("--image-fps", type=float)
    ingest_parser.add_argument("--output-root", type=Path, default=Path("11_验收/golden_case_bundles"))
    ingest_parser.add_argument("--source-prompt-file", type=Path)
    ingest_parser.add_argument("--reconstructed-prompt-file", type=Path)
    ingest_parser.add_argument("--context-file", type=Path)
    ingest_parser.add_argument("--asr-command", nargs="+", help="External ASR command; include literal {audio} argument")
    ingest_parser.add_argument("--explicit-golden-intent", action="store_true", help="Record user intent only; never auto-registers a case")
    validate_parser = commands.add_parser("validate", help="validate a generated bundle")
    validate_parser.add_argument("bundle", type=Path)
    return root


def main(argv: list[str] | None = None) -> None:
    args = parser().parse_args(argv)
    if args.command == "ingest":
        bundle = ingest(
            IngestOptions(
                case_id=args.case_id,
                output_root=args.output_root,
                video=args.video,
                image_dir=args.image_dir,
                image_fps=args.image_fps,
                source_prompt_file=args.source_prompt_file,
                reconstructed_prompt_file=args.reconstructed_prompt_file,
                context_file=args.context_file,
                asr_command=args.asr_command,
                explicit_golden_intent=args.explicit_golden_intent,
            ),
            resolve_ffmpeg() if args.video else "unused-for-image-sequence",
        )
        result = validate_bundle(bundle)
        print(f"BUNDLE={bundle}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        if not result.passed:
            for error in result.errors:
                print(f"ERROR: {error}")
            raise SystemExit(2)
        print("VALIDATION=PASS")
        return
    result = validate_bundle(args.bundle)
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")
    print("VALIDATION=PASS" if result.passed else "VALIDATION=FAIL")
    raise SystemExit(0 if result.passed else 2)
