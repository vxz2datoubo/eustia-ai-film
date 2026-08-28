from pathlib import Path

src_path = Path(__file__).with_name('_tmp_p1_lock_authority_remediation_v2.py')
src = src_path.read_text(encoding='utf-8')
src = src.replace(
    "r'def _validate_trusted_upstream_lock_envelope\\(.*?\\n(?=def validate_cinematic_intent_contract)'",
    "r'def _validate_trusted_upstream_lock_envelope\\(.*?(?=\\ndef validate_cinematic_intent_contract)'",
)
exec(compile(src, str(src_path), 'exec'))
