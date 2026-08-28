from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

p = ROOT / 'tools/learning_retriever/learning_retriever/cinematic_intent.py'
s = p.read_text(encoding='utf-8')
s = s.replace('from dataclasses import dataclass\n', 'from dataclasses import dataclass, field\n').replace('import hashlib\n', '').replace('import re\n', '')
s = s.replace('_UPSTREAM_LOCK_ENVELOPE_KEYS = {"source_authority_ref", "source_material_digest", "camera"}\n', '').replace('_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")\n', '')
pattern = r'@dataclass\(frozen=True\)\nclass TrustedUpstreamLockEnvelope:.*?\n\n_TOP_LEVEL_KEYS ='
replacement = '''_TRUSTED_UPSTREAM_AUTHORITY_TOKEN = object()\n\n\n@dataclass(frozen=True)\nclass TrustedUpstreamLockEnvelope:\n    \"\"\"Process-local camera-lock capability; never deserialized from caller data.\"\"\"\n\n    source_authority_ref: str\n    camera: dict[str, Any]\n    _authority_token: object = field(repr=False, compare=False)\n\n    def __post_init__(self) -> None:\n        if self._authority_token is not _TRUSTED_UPSTREAM_AUTHORITY_TOKEN:\n            raise CinematicIntentContractError(\n                \"MISSING_TRUSTED_UPSTREAM_BINDING\",\n                \"trusted camera-lock capability cannot be minted from downstream invocation data\",\n            )\n\n\ndef _mint_trusted_upstream_lock_for_orchestration(\n    *, source_authority_ref: str, camera: Mapping[str, Any]\n) -> TrustedUpstreamLockEnvelope:\n    \"\"\"Internal orchestration boundary; intentionally absent from public package exports/CLI.\"\"\"\n    source_ref = str(source_authority_ref or \"\").strip()\n    if not source_ref:\n        raise CinematicIntentContractError(\n            \"MISSING_TRUSTED_UPSTREAM_BINDING\", \"trusted source authority ref is required\"\n        )\n    camera_map = _as_mapping(camera, field=\"trusted_upstream.camera\")\n    unknown_camera = set(camera_map) - _UPSTREAM_CAMERA_LOCK_KEYS\n    if unknown_camera:\n        raise CinematicIntentContractError(\n            \"CONTRACT_UNKNOWN_NESTED_FIELD\",\n            f\"unknown upstream camera lock fields: {sorted(unknown_camera)}\",\n        )\n    unsupported = set(camera_map) & _UNENFORCEABLE_CAMERA_LOCK_KEYS\n    if unsupported:\n        raise CinematicIntentContractError(\n            \"UNENFORCEABLE_CAMERA_LOCK_SURFACE\",\n            f\"camera lock fields are not mechanically enforceable here: {sorted(unsupported)}\",\n        )\n    return TrustedUpstreamLockEnvelope(\n        source_authority_ref=source_ref,\n        camera=camera_map,\n        _authority_token=_TRUSTED_UPSTREAM_AUTHORITY_TOKEN,\n    )\n\n\n_TOP_LEVEL_KEYS ='''
s2, n = re.subn(pattern, replacement, s, flags=re.S)
assert n == 1, f'envelope replace count={n}'
s = s2
s2, n = re.subn(r'def _validate_trusted_upstream_lock_envelope\(.*?\n(?=def validate_cinematic_intent_contract)', '', s, flags=re.S)
assert n == 1, f'validator remove count={n}'
s = s2
pattern = r'def compile_cinematic_intent_contract\(.*?\n    diagnostics = evaluate_cinematic_intent\('
replacement = '''def compile_cinematic_intent_contract(\n    raw: Mapping[str, Any],\n    *,\n    project_root: str | Path,\n    trusted_upstream_lock: TrustedUpstreamLockEnvelope | None = None,\n) -> dict[str, Any]:\n    \"\"\"Compile with a non-serializable trusted lock capability.\n\n    YAML/JSON/CLI callers have no envelope, digest, or token input that can mint\n    upstream camera authority. Camera-sensitive intent without capability fails closed.\n    \"\"\"\n    contract = validate_cinematic_intent_contract(raw, project_root=project_root)\n    capture = dict(contract.intent.get(\"capture_intent\") or {})\n    camera_sensitive = any(\n        not _is_empty(capture.get(key))\n        for key in (\"camera_physical_position\", \"lens_intent\")\n    )\n    if trusted_upstream_lock is None:\n        if camera_sensitive:\n            raise CinematicIntentContractError(\n                \"MISSING_TRUSTED_UPSTREAM_BINDING\",\n                \"camera-sensitive CinematicIntent requires process-local trusted upstream authority\",\n            )\n        trusted_locks = _mint_trusted_upstream_lock_for_orchestration(\n            source_authority_ref=\"runtime://no-camera-lock-required\", camera={}\n        )\n    elif not isinstance(trusted_upstream_lock, TrustedUpstreamLockEnvelope):\n        raise CinematicIntentContractError(\n            \"MISSING_TRUSTED_UPSTREAM_BINDING\",\n            \"serialized mappings/digests cannot serve as trusted camera authority\",\n        )\n    else:\n        trusted_locks = trusted_upstream_lock\n    diagnostics = evaluate_cinematic_intent('''
s2, n = re.subn(pattern, replacement, s, flags=re.S)
assert n == 1, f'compile replace count={n}'
s = s2
s = s.replace('            "source_material_digest": trusted_locks.source_material_digest,\n', '')
# CLI: remove caller-mintable lock knobs and their deserialization.
s2, n = re.subn(r'    parser\.add_argument\(\n        "--upstream-lock-envelope".*?    args = parser\.parse_args\(\)\n', '    args = parser.parse_args()\n', s, flags=re.S)
assert n == 1, f'cli args replace count={n}'
s = s2
s2, n = re.subn(r'    upstream_path = Path\(args\.upstream_lock_envelope\).*?    try:\n', '    try:\n', s, flags=re.S)
assert n == 1, f'cli parse replace count={n}'
s = s2
s = s.replace('            upstream_lock_envelope=upstream_raw,\n            trusted_upstream_source_digest=args.trusted_upstream_source_digest,\n', '')
p.write_text(s, encoding='utf-8')

# Hardening tests: replace digest helper with process-local capability helper.
p = ROOT / 'tools/learning_retriever/tests/test_cinematic_intent_contract_hardening.py'
s = p.read_text(encoding='utf-8').replace('import hashlib\nimport json\n', '')
s = s.replace('    compile_cinematic_intent_contract,\n', '    _mint_trusted_upstream_lock_for_orchestration,\n    compile_cinematic_intent_contract,\n')
s2, n = re.subn(r'def _binding\(.*?\n(?=class CinematicIntentContractHardeningTests)', '''def _compile(raw, *, camera=None, source_ref="test_fixture://trusted_orchestration/no_camera_lock"):\n    trusted = _mint_trusted_upstream_lock_for_orchestration(\n        source_authority_ref=source_ref, camera=camera or {}\n    )\n    return compile_cinematic_intent_contract(\n        raw, project_root=REPO_ROOT, trusted_upstream_lock=trusted\n    )\n\n\n''', s, flags=re.S)
assert n == 1, f'hard helper replace count={n}'
p.write_text(s2, encoding='utf-8')

# Main contract tests: replace caller digest helper and attack test.
p = ROOT / 'tools/learning_retriever/tests/test_cinematic_intent_contract.py'
s = p.read_text(encoding='utf-8').replace('import hashlib\nimport json\n', '')
s = s.replace('    compile_cinematic_intent_contract,\n', '    TrustedUpstreamLockEnvelope,\n    _mint_trusted_upstream_lock_for_orchestration,\n    compile_cinematic_intent_contract,\n')
s2, n = re.subn(r'UPSTREAM_FIXTURE =.*?\n(?=class CinematicIntentContractTests)', '''UPSTREAM_FIXTURE = SUITE["trusted_upstream_fixture"]\n\n\ndef _trusted_lock(camera=None, source_ref="test_fixture://trusted_orchestration/shot_plan"):\n    return _mint_trusted_upstream_lock_for_orchestration(\n        source_authority_ref=source_ref, camera=camera or {}\n    )\n\n\ndef _compile_case(case):\n    envelope = case.get("upstream_lock_envelope") or UPSTREAM_FIXTURE.get("envelope") or {}\n    return compile_cinematic_intent_contract(\n        case["contract"],\n        project_root=REPO_ROOT,\n        trusted_upstream_lock=_trusted_lock(\n            envelope.get("camera") or {},\n            envelope.get("source_authority_ref") or "test_fixture://trusted_orchestration/shot_plan",\n        ),\n    )\n\n\n''', s, flags=re.S)
assert n == 1, f'main helper replace count={n}'
s = s2
s2, n = re.subn(r'    def test_upstream_binding_and_unenforceable_lock_attacks_fail_closed\(self\):.*?(?=    def test_matching_trusted_position_lock_is_preserved_in_receipt)', '''    def test_serialized_caller_cannot_mint_trusted_lock_authority(self):\n        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")\n        with self.assertRaises(CinematicIntentContractError) as ctx:\n            TrustedUpstreamLockEnvelope(\n                source_authority_ref="caller://forged",\n                camera={"position": "forged"},\n                _authority_token=object(),\n            )\n        self.assertEqual(ctx.exception.code, "MISSING_TRUSTED_UPSTREAM_BINDING")\n        with self.assertRaises(TypeError):\n            compile_cinematic_intent_contract(\n                case["contract"], project_root=REPO_ROOT,\n                upstream_lock_envelope={"source_authority_ref": "caller://forged", "camera": {"position": "forged"}},\n                trusted_upstream_source_digest="0" * 64,\n            )\n\n    def test_unenforceable_lock_surfaces_fail_closed_at_trusted_boundary(self):\n        for field in ("orientation", "shot_size", "camera_height", "camera_motion"):\n            with self.subTest(field=field):\n                with self.assertRaises(CinematicIntentContractError) as ctx:\n                    _trusted_lock({field: "forbidden"})\n                self.assertEqual(ctx.exception.code, "UNENFORCEABLE_CAMERA_LOCK_SURFACE")\n\n''', s, flags=re.S)
assert n == 1, f'attack method replace count={n}'
s = s2
s = re.sub(r'        self\.assertEqual\(\n            result\["upstream_lock_binding"\]\["source_material_digest"\],.*?        \)\n', '', s, flags=re.S)
p.write_text(s, encoding='utf-8')

print('robust P1 remediation applied')
