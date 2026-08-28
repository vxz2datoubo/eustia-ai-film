from pathlib import Path

ROOT = Path('.')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'missing anchor: {label}')
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Runtime: separate downstream proposal from trusted upstream lock binding.
# ---------------------------------------------------------------------------
p = ROOT / 'tools/learning_retriever/learning_retriever/cinematic_intent.py'
text = p.read_text(encoding='utf-8')
text = replace_once(text, 'import json\nfrom pathlib import Path\n', 'import json\nimport re\nfrom pathlib import Path\n', 'import re')
text = replace_once(
    text,
    '''@dataclass(frozen=True)\nclass CinematicIntentContract:\n    contract_id: str\n    intent: dict[str, Any]\n    provenance: dict[str, Any]\n    context: dict[str, Any]\n    locked_contracts: dict[str, Any]\n\n\n_TOP_LEVEL_KEYS = {"contract_id", "intent", "provenance", "context", "locked_contracts"}\n''',
    '''@dataclass(frozen=True)\nclass CinematicIntentContract:\n    contract_id: str\n    intent: dict[str, Any]\n    provenance: dict[str, Any]\n    context: dict[str, Any]\n\n\n@dataclass(frozen=True)\nclass TrustedUpstreamLockEnvelope:\n    """Invocation-bound upstream constraints, never deserialized from proposal intent."""\n\n    source_authority_ref: str\n    source_material_digest: str\n    camera: dict[str, Any]\n\n\n_TOP_LEVEL_KEYS = {"contract_id", "intent", "provenance", "context"}\n''',
    'dataclass/top keys',
)
text = replace_once(
    text,
    '    "continuity_override",\n}\n',
    '    "continuity_override",\n    "locked_contracts",\n}\n',
    'caller locked contracts forbidden',
)
text = replace_once(
    text,
    '''_LOCKED_CONTRACT_KEYS = {"camera", "blocking_fingerprint", "map_fingerprint"}\n_CAMERA_LOCK_KEYS = {"position", "orientation", "shot_size", "camera_height", "lens_intent", "camera_motion"}\n''',
    '''_UPSTREAM_LOCK_ENVELOPE_KEYS = {"source_authority_ref", "source_material_digest", "camera"}\n_UPSTREAM_CAMERA_LOCK_KEYS = {"position", "orientation", "shot_size", "camera_height", "lens_intent", "camera_motion"}\n_ENFORCEABLE_CAMERA_LOCK_KEYS = {"position", "lens_intent"}\n_UNENFORCEABLE_CAMERA_LOCK_KEYS = _UPSTREAM_CAMERA_LOCK_KEYS - _ENFORCEABLE_CAMERA_LOCK_KEYS\n_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")\n''',
    'lock constants',
)
text = replace_once(
    text,
    '''    "INVALID_MATERIAL_FIELD",\n    "INVALID_CONTRACT_SHAPE",\n}\n''',
    '''    "INVALID_MATERIAL_FIELD",\n    "INVALID_CONTRACT_SHAPE",\n    "MISSING_TRUSTED_UPSTREAM_BINDING",\n    "UPSTREAM_BINDING_MISMATCH",\n    "UNENFORCEABLE_CAMERA_LOCK_SURFACE",\n}\n''',
    'structural codes',
)
insert_anchor = '''def validate_cinematic_intent_contract(\n    raw: Mapping[str, Any], *, project_root: str | Path\n) -> CinematicIntentContract:\n'''
validator = '''def _validate_trusted_upstream_lock_envelope(\n    raw: Mapping[str, Any] | None,\n    *,\n    trusted_upstream_source_digest: str | None,\n) -> TrustedUpstreamLockEnvelope:\n    """Cross-bind a separately supplied upstream lock envelope to trusted invocation evidence.\n\n    The downstream CinematicIntent proposal cannot carry this envelope.  The trusted\n    digest is a separate invocation input owned by the upstream orchestration path.\n    This runtime verifies equality and refuses lock surfaces it cannot mechanically\n    enforce instead of accepting inert authority-shaped fields.\n    """\n\n    if raw is None or _is_empty(trusted_upstream_source_digest):\n        raise CinematicIntentContractError(\n            "MISSING_TRUSTED_UPSTREAM_BINDING",\n            "CinematicIntent compilation requires a separate upstream lock envelope and trusted source digest",\n        )\n    envelope = _as_mapping(raw, field="upstream_lock_envelope")\n    unknown = set(envelope) - _UPSTREAM_LOCK_ENVELOPE_KEYS\n    if unknown:\n        raise CinematicIntentContractError(\n            "CONTRACT_UNKNOWN_FIELD",\n            f"unknown upstream lock envelope fields: {sorted(unknown)}",\n        )\n\n    source_ref = str(envelope.get("source_authority_ref") or "").strip()\n    source_digest = str(envelope.get("source_material_digest") or "").strip().lower()\n    trusted_digest = str(trusted_upstream_source_digest or "").strip().lower()\n    if not source_ref or not _SHA256_RE.fullmatch(source_digest) or not _SHA256_RE.fullmatch(trusted_digest):\n        raise CinematicIntentContractError(\n            "UPSTREAM_BINDING_MISMATCH",\n            "upstream lock binding requires a non-empty authority ref and exact SHA-256 source digests",\n        )\n    if source_digest != trusted_digest:\n        raise CinematicIntentContractError(\n            "UPSTREAM_BINDING_MISMATCH",\n            "upstream lock envelope source digest does not match trusted invocation digest",\n        )\n\n    camera = _as_mapping(envelope.get("camera"), field="upstream_lock_envelope.camera")\n    unknown_camera = set(camera) - _UPSTREAM_CAMERA_LOCK_KEYS\n    if unknown_camera:\n        raise CinematicIntentContractError(\n            "CONTRACT_UNKNOWN_NESTED_FIELD",\n            f"unknown upstream camera lock fields: {sorted(unknown_camera)}",\n        )\n    un_enforceable = set(camera) & _UNENFORCEABLE_CAMERA_LOCK_KEYS\n    if un_enforceable:\n        raise CinematicIntentContractError(\n            "UNENFORCEABLE_CAMERA_LOCK_SURFACE",\n            "current CinematicIntentIR cannot mechanically propose/compare camera lock fields "\n            f"{sorted(un_enforceable)}; refusing inert lock authority",\n        )\n\n    return TrustedUpstreamLockEnvelope(\n        source_authority_ref=source_ref,\n        source_material_digest=source_digest,\n        camera=camera,\n    )\n\n\n'''
if insert_anchor not in text:
    raise SystemExit('missing upstream validator insertion anchor')
text = text.replace(insert_anchor, validator + insert_anchor, 1)

old_lock_parse = '''    locked_contracts = _as_mapping(raw.get("locked_contracts"), field="locked_contracts")\n    unknown_locks = set(locked_contracts) - _LOCKED_CONTRACT_KEYS\n    if unknown_locks:\n        raise CinematicIntentContractError(\n            "CONTRACT_UNKNOWN_FIELD", f"unknown locked contract fields: {sorted(unknown_locks)}"\n        )\n    if "camera" in locked_contracts:\n        camera = _as_mapping(locked_contracts["camera"], field="locked_contracts.camera")\n        unknown_camera = set(camera) - _CAMERA_LOCK_KEYS\n        if unknown_camera:\n            raise CinematicIntentContractError(\n                "CONTRACT_UNKNOWN_NESTED_FIELD",\n                f"unknown locked camera fields: {sorted(unknown_camera)}",\n            )\n        locked_contracts["camera"] = camera\n\n'''
if old_lock_parse not in text:
    raise SystemExit('missing old caller lock parse block')
text = text.replace(old_lock_parse, '', 1)
text = replace_once(
    text,
    '''        provenance=provenance,\n        context=context,\n        locked_contracts=locked_contracts,\n    )\n''',
    '''        provenance=provenance,\n        context=context,\n    )\n''',
    'contract return lock removal',
)
text = replace_once(
    text,
    '''def evaluate_cinematic_intent(\n    contract: CinematicIntentContract, *, project_root: str | Path\n) -> list[Diagnostic]:\n''',
    '''def evaluate_cinematic_intent(\n    contract: CinematicIntentContract,\n    *,\n    project_root: str | Path,\n    upstream_lock_envelope: TrustedUpstreamLockEnvelope,\n) -> list[Diagnostic]:\n''',
    'evaluate signature',
)
text = replace_once(
    text,
    '    locked_camera = dict(contract.locked_contracts.get("camera") or {})\n',
    '    locked_camera = dict(upstream_lock_envelope.camera or {})\n',
    'evaluate trusted camera',
)
text = replace_once(
    text,
    '''def compile_cinematic_intent_contract(\n    raw: Mapping[str, Any], *, project_root: str | Path\n) -> dict[str, Any]:\n    """Validate, evaluate and compile a minimal material execution overlay."""\n\n    contract = validate_cinematic_intent_contract(raw, project_root=project_root)\n    diagnostics = evaluate_cinematic_intent(contract, project_root=project_root)\n''',
    '''def compile_cinematic_intent_contract(\n    raw: Mapping[str, Any],\n    *,\n    project_root: str | Path,\n    upstream_lock_envelope: Mapping[str, Any] | None = None,\n    trusted_upstream_source_digest: str | None = None,\n) -> dict[str, Any]:\n    """Validate, cross-bind upstream locks, and compile a minimal material overlay."""\n\n    contract = validate_cinematic_intent_contract(raw, project_root=project_root)\n    trusted_locks = _validate_trusted_upstream_lock_envelope(\n        upstream_lock_envelope,\n        trusted_upstream_source_digest=trusted_upstream_source_digest,\n    )\n    diagnostics = evaluate_cinematic_intent(\n        contract,\n        project_root=project_root,\n        upstream_lock_envelope=trusted_locks,\n    )\n''',
    'compile signature/binding',
)
text = replace_once(
    text,
    '''        "reverse_eval_expectations": reverse_expectations,\n        "authority_mutation_allowed": False,\n    }\n''',
    '''        "reverse_eval_expectations": reverse_expectations,\n        "upstream_lock_binding": {\n            "source_authority_ref": trusted_locks.source_authority_ref,\n            "source_material_digest": trusted_locks.source_material_digest,\n            "camera": dict(trusted_locks.camera),\n            "proposal_can_mutate": False,\n        },\n        "authority_mutation_allowed": False,\n    }\n''',
    'compile result binding receipt',
)
text = replace_once(
    text,
    '''    parser.add_argument("--contract", required=True, help="JSON or YAML contract file")\n    args = parser.parse_args()\n\n    path = Path(args.contract)\n    text = path.read_text(encoding="utf-8")\n    if path.suffix.lower() == ".json":\n        raw = json.loads(text)\n    else:\n        raw = yaml.safe_load(text)\n    try:\n        result = compile_cinematic_intent_contract(raw, project_root=args.project_root)\n''',
    '''    parser.add_argument("--contract", required=True, help="JSON or YAML downstream proposal file")\n    parser.add_argument(\n        "--upstream-lock-envelope",\n        required=True,\n        help="JSON or YAML upstream lock envelope supplied separately from the proposal",\n    )\n    parser.add_argument(\n        "--trusted-upstream-source-digest",\n        required=True,\n        help="trusted upstream source SHA-256 supplied by the orchestration boundary",\n    )\n    args = parser.parse_args()\n\n    path = Path(args.contract)\n    text = path.read_text(encoding="utf-8")\n    if path.suffix.lower() == ".json":\n        raw = json.loads(text)\n    else:\n        raw = yaml.safe_load(text)\n\n    upstream_path = Path(args.upstream_lock_envelope)\n    upstream_text = upstream_path.read_text(encoding="utf-8")\n    if upstream_path.suffix.lower() == ".json":\n        upstream_raw = json.loads(upstream_text)\n    else:\n        upstream_raw = yaml.safe_load(upstream_text)\n    try:\n        result = compile_cinematic_intent_contract(\n            raw,\n            project_root=args.project_root,\n            upstream_lock_envelope=upstream_raw,\n            trusted_upstream_source_digest=args.trusted_upstream_source_digest,\n        )\n''',
    'CLI upstream binding',
)
p.write_text(text, encoding='utf-8')


# ---------------------------------------------------------------------------
# Regression YAML: separate proposal from upstream lock fixtures + adversarial gates.
# ---------------------------------------------------------------------------
p = ROOT / '11_验收/cinematic_intent_contract_regression_cases.yaml'
text = p.read_text(encoding='utf-8')
text = replace_once(
    text,
    '  learning_maturity_unchanged: true\n\ncompile_cases:\n',
    '''  learning_maturity_unchanged: true\n  proposal_cannot_supply_locked_contracts: true\n  upstream_lock_envelope_is_separate_invocation_input: true\n  upstream_source_digest_cross_binding_required: true\n  unsupported_camera_lock_surfaces_fail_closed: true\n\ntrusted_upstream_fixture:\n  trusted_source_digest: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n  envelope:\n    source_authority_ref: test_fixture://shot_plan/no_camera_lock\n    source_material_digest: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n    camera: {}\n\ncompile_cases:\n''',
    'yaml policy/fixture',
)
# Remove the two old caller-side lock blocks.
old = '''      locked_contracts:\n        camera:\n          position: exterior_side\n'''
if text.count(old) != 2:
    raise SystemExit(f'expected exactly two caller lock blocks, got {text.count(old)}')
text = text.replace(old, '')
# Bind valid/minimal and contradiction cases through separate invocation metadata.
text = replace_once(
    text,
    '''    expected_status: PASS\n    expected_overlay_fields: [composition, color_intent]\n''',
    '''    upstream_lock_envelope:\n      source_authority_ref: test_fixture://shot_plan/locked_side_camera\n      source_material_digest: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"\n      camera:\n        position: exterior_side\n    trusted_upstream_source_digest: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"\n    expected_status: PASS\n    expected_overlay_fields: [composition, color_intent]\n''',
    'valid matching lock fixture',
)
text = replace_once(
    text,
    '''    expected_status: FAIL\n    expected_diagnostics: [CAMERA_SCOPE_CONFLICT]\n    expected_overlay_fields: []\n''',
    '''    upstream_lock_envelope:\n      source_authority_ref: test_fixture://shot_plan/locked_side_camera\n      source_material_digest: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"\n      camera:\n        position: exterior_side\n    trusted_upstream_source_digest: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"\n    expected_status: FAIL\n    expected_diagnostics: [CAMERA_SCOPE_CONFLICT]\n    expected_overlay_fields: []\n''',
    'contradictory lock fixture',
)
# Add an explicit caller-minting structural attack.
text = replace_once(
    text,
    '''  - id: CIC-UNKNOWN-TOP-FIELD-001\n''',
    '''  - id: CIC-CALLER-MINTED-LOCK-001\n    contract:\n      contract_id: CIC-CALLER-MINTED-LOCK-001\n      intent:\n        capture_intent:\n          camera_physical_position: front_three_quarter\n      locked_contracts:\n        camera:\n          position: front_three_quarter\n    expected_error_code: CINEMATIC_INTENT_AUTHORITY_VIOLATION\n\n  - id: CIC-UNKNOWN-TOP-FIELD-001\n''',
    'caller lock attack',
)
# Add upstream-envelope adversarial gates before suite gates.
text = replace_once(
    text,
    '''gates:\n''',
    '''upstream_gate_cases:\n  - id: CIC-UPSTREAM-DIGEST-SUBSTITUTION-001\n    contract_ref: CIC-VALID-MINIMAL-001\n    upstream_lock_envelope:\n      source_authority_ref: test_fixture://shot_plan/substituted\n      source_material_digest: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"\n      camera:\n        position: exterior_side\n    trusted_upstream_source_digest: "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"\n    expected_error_code: UPSTREAM_BINDING_MISMATCH\n\n  - id: CIC-UPSTREAM-ORIENTATION-UNENFORCEABLE-001\n    contract_ref: CIC-VALID-MINIMAL-001\n    camera_lock: {orientation: side_on}\n    expected_error_code: UNENFORCEABLE_CAMERA_LOCK_SURFACE\n\n  - id: CIC-UPSTREAM-SHOT-SIZE-UNENFORCEABLE-001\n    contract_ref: CIC-VALID-MINIMAL-001\n    camera_lock: {shot_size: wide}\n    expected_error_code: UNENFORCEABLE_CAMERA_LOCK_SURFACE\n\n  - id: CIC-UPSTREAM-CAMERA-HEIGHT-UNENFORCEABLE-001\n    contract_ref: CIC-VALID-MINIMAL-001\n    camera_lock: {camera_height: rooftop_level}\n    expected_error_code: UNENFORCEABLE_CAMERA_LOCK_SURFACE\n\n  - id: CIC-UPSTREAM-CAMERA-MOTION-UNENFORCEABLE-001\n    contract_ref: CIC-VALID-MINIMAL-001\n    camera_lock: {camera_motion: locked_off}\n    expected_error_code: UNENFORCEABLE_CAMERA_LOCK_SURFACE\n\ngates:\n''',
    'upstream gate cases',
)
text = replace_once(
    text,
    '''  no_model_specific_behavior_universalized: true\n''',
    '''  no_model_specific_behavior_universalized: true\n  downstream_proposal_cannot_mint_lock_authority: true\n  every_accepted_camera_lock_surface_is_mechanically_enforced: true\n''',
    'yaml final gates',
)
p.write_text(text, encoding='utf-8')


# ---------------------------------------------------------------------------
# Tests: route every compile case through separate upstream binding and attack it.
# ---------------------------------------------------------------------------
p = ROOT / 'tools/learning_retriever/tests/test_cinematic_intent_contract.py'
text = p.read_text(encoding='utf-8')
helper_anchor = '''SCHEMA = yaml.safe_load(\n    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")\n)\n\n\n'''
helper = '''SCHEMA = yaml.safe_load(\n    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")\n)\nUPSTREAM_FIXTURE = SUITE["trusted_upstream_fixture"]\n\n\ndef _compile_case(case):\n    return compile_cinematic_intent_contract(\n        case["contract"],\n        project_root=REPO_ROOT,\n        upstream_lock_envelope=case.get("upstream_lock_envelope", UPSTREAM_FIXTURE["envelope"]),\n        trusted_upstream_source_digest=case.get(\n            "trusted_upstream_source_digest", UPSTREAM_FIXTURE["trusted_source_digest"]\n        ),\n    )\n\n\n'''
text = replace_once(text, helper_anchor, helper, 'test compile helper')
text = text.replace('compile_cinematic_intent_contract(case["contract"], project_root=REPO_ROOT)', '_compile_case(case)')
text = text.replace('compile_cinematic_intent_contract(valid["contract"], project_root=REPO_ROOT)', '_compile_case(valid)')
# Insert adversarial upstream tests after structural gate test.
anchor = '''    def test_runtime_diagnostics_are_declared_by_canonical_schema(self):\n'''
addition = '''    def test_missing_separate_upstream_binding_fails_closed(self):\n        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")\n        with self.assertRaises(CinematicIntentContractError) as ctx:\n            compile_cinematic_intent_contract(case["contract"], project_root=REPO_ROOT)\n        self.assertEqual(ctx.exception.code, "MISSING_TRUSTED_UPSTREAM_BINDING")\n        self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)\n\n    def test_upstream_binding_and_unenforceable_lock_attacks_fail_closed(self):\n        contract_by_id = {case["id"]: case["contract"] for case in SUITE["compile_cases"]}\n        for case in SUITE["upstream_gate_cases"]:\n            with self.subTest(case=case["id"]):\n                if "upstream_lock_envelope" in case:\n                    envelope = case["upstream_lock_envelope"]\n                    trusted_digest = case["trusted_upstream_source_digest"]\n                else:\n                    envelope = {\n                        "source_authority_ref": "test_fixture://shot_plan/unrepresentable_camera_lock",\n                        "source_material_digest": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",\n                        "camera": case["camera_lock"],\n                    }\n                    trusted_digest = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"\n                with self.assertRaises(CinematicIntentContractError) as ctx:\n                    compile_cinematic_intent_contract(\n                        contract_by_id[case["contract_ref"]],\n                        project_root=REPO_ROOT,\n                        upstream_lock_envelope=envelope,\n                        trusted_upstream_source_digest=trusted_digest,\n                    )\n                self.assertEqual(ctx.exception.code, case["expected_error_code"])\n                self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)\n\n    def test_matching_trusted_position_lock_is_preserved_in_receipt(self):\n        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")\n        result = _compile_case(case)\n        self.assertEqual(result["status"], "PASS")\n        self.assertEqual(result["upstream_lock_binding"]["camera"], {"position": "exterior_side"})\n        self.assertFalse(result["upstream_lock_binding"]["proposal_can_mutate"])\n        self.assertEqual(\n            result["upstream_lock_binding"]["source_material_digest"],\n            case["trusted_upstream_source_digest"],\n        )\n\n'''
text = replace_once(text, anchor, addition + anchor, 'upstream adversarial tests')
# Ensure all remaining direct compile calls in test methods carry the helper except the intentional missing-binding test.
# The reference-risk and fail/overlay tests use `case`; replacement above has already converted them.
p.write_text(text, encoding='utf-8')


# ---------------------------------------------------------------------------
# README: make the authority seam explicit for production callers.
# ---------------------------------------------------------------------------
p = ROOT / 'tools/learning_retriever/README.md'
text = p.read_text(encoding='utf-8')
text = text.replace('''locked_contracts:\n  camera:\n    position: exterior_side\n''', '')
marker = '''Run it directly:\n\n```bash\nPYTHONPATH=tools/learning_retriever python -m learning_retriever.cinematic_intent \\\n  --project-root . \\\n  --contract cinematic_intent.yaml\n```\n'''
replacement = '''The downstream proposal cannot carry camera locks. Camera-lock authority enters through a separate upstream envelope, cross-bound to a trusted source digest. Current canonical `capture_intent` can mechanically propose only camera physical position and lens intent, so those are the only accepted lock surfaces in this runtime. Orientation, shot size, camera height and camera motion remain owned by upstream ShotPlan/Visible camera state and fail closed here rather than being accepted inertly.\n\nExample upstream lock envelope:\n\n```yaml\nsource_authority_ref: shot_plan://current_generation/camera_state\nsource_material_digest: <sha256-of-trusted-upstream-source-material>\ncamera:\n  position: exterior_side\n  lens_intent: side_profile_readability\n```\n\nRun it directly:\n\n```bash\nPYTHONPATH=tools/learning_retriever python -m learning_retriever.cinematic_intent \\\n  --project-root . \\\n  --contract cinematic_intent.yaml \\\n  --upstream-lock-envelope upstream_camera_lock.yaml \\\n  --trusted-upstream-source-digest <trusted-sha256-from-upstream-orchestration>\n```\n'''
text = replace_once(text, marker, replacement, 'README CLI block')
p.write_text(text, encoding='utf-8')

print('P1 cinematic lock-authority remediation applied')
