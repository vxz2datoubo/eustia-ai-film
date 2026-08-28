from pathlib import Path

src_path = Path(__file__).with_name('_tmp_p1_lock_authority_remediation_v2.py')
lines = src_path.read_text(encoding='utf-8').splitlines()
out = []
replaced = 0
for line in lines:
    if line.startswith("s2, n = re.subn(r'def _validate_trusted_upstream_lock_envelope"):
        out.extend([
            "start = s.find('def _validate_trusted_upstream_lock_envelope(')",
            "end = s.find('def validate_cinematic_intent_contract(', start)",
            "assert start >= 0 and end > start, f'validator bounds start={start} end={end}'",
            "s2, n = s[:start] + s[end:], 1",
        ])
        replaced += 1
    else:
        out.append(line)
assert replaced == 1, f'wrapper source replacement count={replaced}'
source = '\n'.join(out) + '\n'
print('stage: wrapper-rewrite-ok')
exec(compile(source, str(src_path), 'exec'))
