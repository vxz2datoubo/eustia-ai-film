from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'missing anchor: {label}')
    return text.replace(old, new, 1)


p = Path('tools/learning_retriever/learning_retriever/cinematic_intent.py')
text = p.read_text(encoding='utf-8')
text = replace_once(text, 'from dataclasses import dataclass\nimport json\nimport re\n', 'from dataclasses import dataclass\nimport hashlib\nimport json\nimport re\n', 'hashlib import')
old = '''    un_enforceable = set(camera) & _UNENFORCEABLE_CAMERA_LOCK_KEYS\n    if un_enforceable:\n        raise CinematicIntentContractError(\n            "UNENFORCEABLE_CAMERA_LOCK_SURFACE",\n            "current CinematicIntentIR cannot mechanically propose/compare camera lock fields "\n            f"{sorted(un_enforceable)}; refusing inert lock authority",\n        )\n\n    return TrustedUpstreamLockEnvelope(\n'''
new = '''    binding_payload = {\n        "source_authority_ref": source_ref,\n        "camera": camera,\n    }\n    canonical_binding = json.dumps(\n        binding_payload,\n        ensure_ascii=False,\n        sort_keys=True,\n        separators=(",", ":"),\n    ).encode("utf-8")\n    computed_digest = hashlib.sha256(canonical_binding).hexdigest()\n    if source_digest != computed_digest or trusted_digest != computed_digest:\n        raise CinematicIntentContractError(\n            "UPSTREAM_BINDING_MISMATCH",\n            "upstream lock payload, declared source digest and trusted invocation digest must match exactly",\n        )\n\n    un_enforceable = set(camera) & _UNENFORCEABLE_CAMERA_LOCK_KEYS\n    if un_enforceable:\n        raise CinematicIntentContractError(\n            "UNENFORCEABLE_CAMERA_LOCK_SURFACE",\n            "current CinematicIntentIR cannot mechanically propose/compare camera lock fields "\n            f"{sorted(un_enforceable)}; refusing inert lock authority",\n        )\n\n    return TrustedUpstreamLockEnvelope(\n'''
text = replace_once(text, old, new, 'content-bound digest')
p.write_text(text, encoding='utf-8')

# Regression fixture digests must be real hashes of the canonical binding payload.
p = Path('11_验收/cinematic_intent_contract_regression_cases.yaml')
text = p.read_text(encoding='utf-8')
replacements = {
    '"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"': '"a60a9346e6e40a68ee6506e8f2a86605897ee835e7f75c2a83b92694258e0e6f"',
}
for old_value, new_value in replacements.items():
    text = text.replace(old_value, new_value)
# The locked-side fixture appears four times: envelope + trusted digest in two cases.
text = text.replace('"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"', '"8833c812d840f1a0b34b1dbd38a80a30dc91bdb2cfb37c1a2a9ff0735a5af30e"')
# Substitution case: envelope digest is correct for the substituted payload, trusted digest stays bound to original locked-side payload.
sub_old = '''      source_material_digest: "8833c812d840f1a0b34b1dbd38a80a30dc91bdb2cfb37c1a2a9ff0735a5af30e"\n      camera:\n        position: exterior_side\n    trusted_upstream_source_digest: "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"\n'''
sub_new = '''      source_material_digest: "9b6ff06a40ca3ce724a047c47c053647887bc567bb5edfedb2ff0456799fce67"\n      camera:\n        position: exterior_side\n    trusted_upstream_source_digest: "8833c812d840f1a0b34b1dbd38a80a30dc91bdb2cfb37c1a2a9ff0735a5af30e"\n'''
text = replace_once(text, sub_old, sub_new, 'substitution fixture')
p.write_text(text, encoding='utf-8')

# Tests generate correct payload digests for un-enforceable surface attacks so those tests reach the intended gate.
p = Path('tools/learning_retriever/tests/test_cinematic_intent_contract.py')
text = p.read_text(encoding='utf-8')
text = replace_once(text, 'from pathlib import Path\nimport unittest\n\nimport yaml\n', 'from pathlib import Path\nimport hashlib\nimport json\nimport unittest\n\nimport yaml\n', 'test imports')
anchor = '''def _compile_case(case):\n'''
helper = '''def _trusted_binding_digest(source_ref, camera):\n    payload = {"source_authority_ref": source_ref, "camera": camera}\n    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")\n    return hashlib.sha256(canonical).hexdigest()\n\n\n'''
if helper.strip() not in text:
    text = replace_once(text, anchor, helper + anchor, 'test digest helper')
old = '''                    envelope = {\n                        "source_authority_ref": "test_fixture://shot_plan/unrepresentable_camera_lock",\n                        "source_material_digest": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",\n                        "camera": case["camera_lock"],\n                    }\n                    trusted_digest = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"\n'''
new = '''                    source_ref = "test_fixture://shot_plan/unrepresentable_camera_lock"\n                    trusted_digest = _trusted_binding_digest(source_ref, case["camera_lock"])\n                    envelope = {\n                        "source_authority_ref": source_ref,\n                        "source_material_digest": trusted_digest,\n                        "camera": case["camera_lock"],\n                    }\n'''
text = replace_once(text, old, new, 'un-enforceable test binding')
p.write_text(text, encoding='utf-8')

# Documentation says the digest is content-bound, not a caller label.
p = Path('tools/learning_retriever/README.md')
text = p.read_text(encoding='utf-8')
old = 'The downstream proposal cannot carry camera locks. Camera-lock authority enters through a separate upstream envelope, cross-bound to a trusted source digest.'
new = 'The downstream proposal cannot carry camera locks. Camera-lock authority enters through a separate upstream envelope whose canonical `source_authority_ref + camera` payload is SHA-256 hashed by the runtime and must exactly match both the envelope digest and a separately supplied trusted upstream digest.'
text = replace_once(text, old, new, 'README content binding')
p.write_text(text, encoding='utf-8')

print('Trusted lock payload digest hardening applied')
