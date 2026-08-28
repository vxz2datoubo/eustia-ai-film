from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ci = ROOT / 'tools/learning_retriever/learning_retriever/cinematic_intent.py'
text = ci.read_text(encoding='utf-8')
text = text.replace('from dataclasses import dataclass\n', 'from dataclasses import dataclass, field\n')
text = text.replace('import hashlib\n', '')
text = text.replace('import re\n', '')
old = '''@dataclass(frozen=True)\nclass TrustedUpstreamLockEnvelope:\n    \"\"\"Invocation-bound upstream constraints, never deserialized from proposal intent.\"\"\"\n\n    source_authority_ref: str\n    source_material_digest: str\n    camera: dict[str, Any]\n\n\n'''
new = '''_TRUSTED_UPSTREAM_AUTHORITY_TOKEN = object()\n\n\n@dataclass(frozen=True)\nclass TrustedUpstreamLockEnvelope:\n    \"\"\"Process-local trusted upstream constraints.\n\n    This value is intentionally not deserializable from YAML/JSON or CLI input.\n    It may only be minted by the trusted orchestration boundary inside this module.\n    Serialized downstream callers can never manufacture camera-lock authority.\n    \"\"\"\n\n    source_authority_ref: str\n    camera: dict[str, Any]\n    _authority_token: object = field(repr=False, compare=False)\n\n    def __post_init__(self) -> None:\n        if self._authority_token is not _TRUSTED_UPSTREAM_AUTHORITY_TOKEN:\n            raise CinematicIntentContractError(\n                \"MISSING_TRUSTED_UPSTREAM_BINDING\",\n                \"trusted upstream lock capability cannot be constructed from downstream invocation data\",\n            )\n\n\ndef _mint_trusted_upstream_lock_for_orchestration(\n    *, source_authority_ref: str, camera: Mapping[str, Any]\n) -> TrustedUpstreamLockEnvelope:\n    \"\"\"Internal orchestration boundary. Not exported and not reachable from CLI data.\"\"\"\n    source_ref = str(source_authority_ref or \"\").strip()\n    if not source_ref:\n        raise CinematicIntentContractError(\n            \"MISSING_TRUSTED_UPSTREAM_BINDING\", \"trusted source authority ref is required\"\n        )\n    camera_map = _as_mapping(camera, field=\"trusted_upstream.camera\")\n    unknown_camera = set(camera_map) - _UPSTREAM_CAMERA_LOCK_KEYS\n    if unknown_camera:\n        raise CinematicIntentContractError(\n            \"CONTRACT_UNKNOWN_NESTED_FIELD\",\n            f\"unknown upstream camera lock fields: {sorted(unknown_camera)}\",\n        )\n    un_enforceable = set(camera_map) & _UNENFORCEABLE_CAMERA_LOCK_KEYS\n    if un_enforceable:\n        raise CinematicIntentContractError(\n            \"UNENFORCEABLE_CAMERA_LOCK_SURFACE\",\n            \"current CinematicIntentIR cannot mechanically propose/compare camera lock fields \"\n            f\"{sorted(un_enforceable)}; refusing inert lock authority\",\n        )\n    return TrustedUpstreamLockEnvelope(\n        source_authority_ref=source_ref,\n        camera=camera_map,\n        _authority_token=_TRUSTED_UPSTREAM_AUTHORITY_TOKEN,\n    )\n\n\n'''
if old not in text:
    raise SystemExit('trusted envelope block not found')
text = text.replace(old, new)
text = text.replace('_UPSTREAM_LOCK_ENVELOPE_KEYS = {"source_authority_ref", "source_material_digest", "camera"}\n', '')
text = text.replace('_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")\n', '')
start = text.index('def _validate_trusted_upstream_lock_envelope(')
end = text.index('\ndef validate_cinematic_intent_contract(', start)
text = text[:start] + text[end+1:]
old_compile = '''def compile_cinematic_intent_contract(\n    raw: Mapping[str, Any],\n    *,\n    project_root: str | Path,\n    upstream_lock_envelope: Mapping[str, Any] | None = None,\n    trusted_upstream_source_digest: str | None = None,\n) -> dict[str, Any]:\n    \"\"\"Validate, cross-bind upstream locks, and compile a minimal material overlay.\"\"\"\n\n    contract = validate_cinematic_intent_contract(raw, project_root=project_root)\n    trusted_locks = _validate_trusted_upstream_lock_envelope(\n        upstream_lock_envelope,\n        trusted_upstream_source_digest=trusted_upstream_source_digest,\n    )\n'''
new_compile = '''def compile_cinematic_intent_contract(\n    raw: Mapping[str, Any],\n    *,\n    project_root: str | Path,\n    trusted_upstream_lock: TrustedUpstreamLockEnvelope | None = None,\n) -> dict[str, Any]:\n    \"\"\"Validate and compile a minimal material overlay.\n\n    Camera-sensitive intent requires a process-local trusted capability. Ordinary\n    serialized invocation data has no field or digest knob that can mint authority.\n    \"\"\"\n\n    contract = validate_cinematic_intent_contract(raw, project_root=project_root)\n    capture = dict(contract.intent.get(\"capture_intent\") or {})\n    camera_sensitive = any(\n        not _is_empty(capture.get(key))\n        for key in (\"camera_physical_position\", \"lens_intent\")\n    )\n    if trusted_upstream_lock is None:\n        if camera_sensitive:\n            raise CinematicIntentContractError(\n                \"MISSING_TRUSTED_UPSTREAM_BINDING\",\n                \"camera-sensitive CinematicIntent requires process-local trusted upstream authority\",\n            )\n        trusted_locks = _mint_trusted_upstream_lock_for_orchestration(\n            source_authority_ref=\"runtime://no-camera-lock-required\", camera={}\n        )\n    elif not isinstance(trusted_upstream_lock, TrustedUpstreamLockEnvelope):\n        raise CinematicIntentContractError(\n            \"MISSING_TRUSTED_UPSTREAM_BINDING\",\n            \"trusted upstream lock must be a process-local capability, not serialized invocation data\",\n        )\n    else:\n        trusted_locks = trusted_upstream_lock\n'''
if old_compile not in text:
    raise SystemExit('compile block not found')
text = text.replace(old_compile, new_compile)
text = text.replace('            "source_material_digest": trusted_locks.source_material_digest,\n', '')
# Replace CLI authority args with fail-closed plain contract CLI.
cli_start = text.index('    parser.add_argument(\n        "--upstream-lock-envelope"')
cli_end = text.index('    args = parser.parse_args()', cli_start)
text = text[:cli_start] + text[cli_end:]
read_start = text.index('    upstream_path = Path(args.upstream_lock_envelope)')
try_start = text.index('    try:\n', read_start)
text = text[:read_start] + text[try_start:]
text = text.replace('            upstream_lock_envelope=upstream_raw,\n            trusted_upstream_source_digest=args.trusted_upstream_source_digest,\n', '')
ci.write_text(text, encoding='utf-8')

# Rewrite primary contract tests to use process-local capability; add caller-mint adversarial test.
test = ROOT / 'tools/learning_retriever/tests/test_cinematic_intent_contract.py'
t = test.read_text(encoding='utf-8')
t = t.replace('import hashlib\nimport json\n', '')
t = t.replace('    compile_cinematic_intent_contract,\n', '    TrustedUpstreamLockEnvelope,\n    _mint_trusted_upstream_lock_for_orchestration,\n    compile_cinematic_intent_contract,\n')
start = t.index('UPSTREAM_FIXTURE =')
end = t.index('\n\nclass CinematicIntentContractTests', start)
helper = '''UPSTREAM_FIXTURE = SUITE["trusted_upstream_fixture"]\n\n\ndef _trusted_lock(camera=None, source_ref="test_fixture://trusted_orchestration/shot_plan"):\n    return _mint_trusted_upstream_lock_for_orchestration(\n        source_authority_ref=source_ref, camera=camera or {}\n    )\n\n\ndef _compile_case(case):\n    envelope = case.get("upstream_lock_envelope")\n    if envelope:\n        camera = envelope.get("camera") or {}\n        source_ref = envelope.get("source_authority_ref") or "test_fixture://trusted_orchestration/shot_plan"\n    else:\n        camera = (UPSTREAM_FIXTURE.get("envelope") or {}).get("camera") or {}\n        source_ref = (UPSTREAM_FIXTURE.get("envelope") or {}).get("source_authority_ref") or "test_fixture://trusted_orchestration/shot_plan"\n    return compile_cinematic_intent_contract(\n        case["contract"],\n        project_root=REPO_ROOT,\n        trusted_upstream_lock=_trusted_lock(camera, source_ref),\n    )\n'''
t = t[:start] + helper + t[end:]
# Replace old attack test body wholesale.
old_method_start = t.index('    def test_upstream_binding_and_unenforceable_lock_attacks_fail_closed(self):')
old_method_end = t.index('\n    def test_matching_trusted_position_lock_is_preserved_in_receipt', old_method_start)
new_method = '''    def test_serialized_caller_cannot_mint_trusted_lock_authority(self):\n        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")\n        forged_camera = {"position": "forged_downstream_position"}\n        with self.assertRaises(CinematicIntentContractError) as ctx:\n            TrustedUpstreamLockEnvelope(\n                source_authority_ref="caller://forged",\n                camera=forged_camera,\n                _authority_token=object(),\n            )\n        self.assertEqual(ctx.exception.code, "MISSING_TRUSTED_UPSTREAM_BINDING")\n\n        # Plain mappings/digests are no longer accepted invocation channels at all.\n        with self.assertRaises(TypeError):\n            compile_cinematic_intent_contract(\n                case["contract"],\n                project_root=REPO_ROOT,\n                upstream_lock_envelope={"source_authority_ref": "caller://forged", "camera": forged_camera},\n                trusted_upstream_source_digest="0" * 64,\n            )\n\n    def test_unenforceable_lock_surfaces_fail_closed_at_trusted_boundary(self):\n        for field in ("orientation", "shot_size", "camera_height", "camera_motion"):\n            with self.subTest(field=field):\n                with self.assertRaises(CinematicIntentContractError) as ctx:\n                    _trusted_lock({field: "forbidden_surface"})\n                self.assertEqual(ctx.exception.code, "UNENFORCEABLE_CAMERA_LOCK_SURFACE")\n\n'''
t = t[:old_method_start] + new_method + t[old_method_end:]
t = t.replace('        self.assertEqual(\n            result["upstream_lock_binding"]["source_material_digest"],\n            case["trusted_upstream_source_digest"],\n        )\n', '')
test.write_text(t, encoding='utf-8')

hard = ROOT / 'tools/learning_retriever/tests/test_cinematic_intent_contract_hardening.py'
h = hard.read_text(encoding='utf-8')
h = h.replace('import hashlib\nimport json\n', '')
h = h.replace('    compile_cinematic_intent_contract,\n', '    _mint_trusted_upstream_lock_for_orchestration,\n    compile_cinematic_intent_contract,\n')
start = h.index('def _binding(')
end = h.index('\n\nclass CinematicIntentContractHardeningTests', start)
helper = '''def _compile(raw, *, camera=None, source_ref="test_fixture://trusted_orchestration/no_camera_lock"):\n    trusted = _mint_trusted_upstream_lock_for_orchestration(\n        source_authority_ref=source_ref, camera=camera or {}\n    )\n    return compile_cinematic_intent_contract(\n        raw, project_root=REPO_ROOT, trusted_upstream_lock=trusted\n    )\n'''
h = h[:start] + helper + h[end:]
hard.write_text(h, encoding='utf-8')

# README: remove public envelope/digest instructions and state fail-closed boundary.
readme = ROOT / 'tools/learning_retriever/README.md'
r = readme.read_text(encoding='utf-8')
r = r.replace('The downstream proposal cannot carry camera locks. Camera-lock authority enters through a separate upstream envelope whose canonical `source_authority_ref + camera` payload is SHA-256 hashed by the runtime and must exactly match both the envelope digest and a separately supplied trusted upstream digest. Current canonical `capture_intent` can mechanically propose only camera physical position and lens intent, so those are the only accepted lock surfaces in this runtime. Orientation, shot size, camera height and camera motion remain owned by upstream ShotPlan/Visible camera state and fail closed here rather than being accepted inertly.\n', 'The downstream proposal cannot carry camera locks, and serialized YAML/JSON/CLI inputs cannot mint camera-lock authority through an envelope, digest, or caller-supplied token. Camera-sensitive `capture_intent` requires a process-local trusted upstream capability injected by orchestration; without it compilation fails closed. Current canonical `capture_intent` can mechanically propose only camera physical position and lens intent, so those are the only accepted lock surfaces. Orientation, shot size, camera height and camera motion remain upstream-owned and fail closed rather than being accepted inertly.\n')
ex_start = r.find('Example upstream lock envelope:')
if ex_start != -1:
    ex_end = r.find('Targeted contract regressions live', ex_start)
    r = r[:ex_start] + 'CLI note: the standalone contract CLI intentionally has no camera-lock authority input. Contracts that materially propose camera position/lens must run through the trusted orchestration path or fail closed.\n\n' + r[ex_end:]
readme.write_text(r, encoding='utf-8')
