# Golden Case Ingestor MVP

`golden_case_ingestor` is the deterministic evidence layer for a media-backed
Golden Case.  It creates a seconds-first temporal evidence bundle; it does not
invent dramatic function, subtext, camera intent, or prompt causality.

## Install

```powershell
cd tools/golden_case_ingestor
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

The tool uses an `ffmpeg` executable.  It resolves `FFMPEG_BIN`, then a system
`ffmpeg`, then the binary supplied by `imageio-ffmpeg`.  `ffprobe` is optional:
when unavailable, the tool obtains the same practical metadata from ffmpeg and
records that the exact frame count was decoded by ffmpeg.

## Ingest a video

```powershell
.\.venv\Scripts\python -m golden_ingestor ingest `
  --case-id GPC-20260815-DEMO `
  --video C:\media\demo.mp4 `
  --source-prompt-file C:\media\prompt.txt `
  --prompt-output-pair-verified `
  --source-origin-type user_supplied `
  --source-rights-status user_supplied_rights_unverified `
  --output-root ..\..\11_验收\golden_case_bundles
```

For an image sequence, replace `--video` with `--image-dir C:\frames` and set
`--image-fps 24`.  The input video and decoded audio are transient by default;
the output contains only selected temporal evidence.

## Optional ASR

Pass a command that emits JSON with a `segments` list (`start_s`, `end_s`,
`text`, optional `confidence`).  `{audio}` is replaced with the transient WAV
path.

```powershell
.\.venv\Scripts\python -m golden_ingestor ingest ... `
  --asr-command my-asr --input {audio} --json
```

Without an ASR command, audio evidence is still measured (silence, loudness,
onset and peak candidates), but `asr_status` is explicitly
`deferred_no_configured_backend`.

## Validate a bundle

```powershell
.\.venv\Scripts\python -m golden_ingestor validate `
  11_验收\golden_case_bundles\GPC-20260815-DEMO
```

## Design limits

- The ingest result is `ingested_evidence_not_registered`; it never registers
  a formal visual asset or a Golden Case registry record.
- Reconstructed prompts are copied only from an explicit user-supplied file and
  remain `inferred_from_media`; the tool never generates one automatically.
- A source prompt remains `M1_media_observation` unless
  `--prompt-output-pair-verified` explicitly confirms it belongs to this media.
  Only that gate permits `M2_prompt_output_pair`.
- Third-party input records origin, URI when known, rights status, and derived
  evidence persistence status.  The validator rejects an unclassified rights
  status for third-party sources; it does not make legal conclusions.
- Shot/change and audio-event results are confidence-scored candidates, not
  editorial ground truth.  The duration-evidence guard is intentionally
  mechanical: it preserves hold start/middle/change/release evidence, while GPT
  decides whether a hold is dramatically meaningful.
- Contact sheets and selected frames use seconds-first names.  Frame indices
  remain technical metadata only.
