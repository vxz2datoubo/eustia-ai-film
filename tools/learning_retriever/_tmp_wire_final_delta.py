from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def insert_after(path: str, anchor: str, addition: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if addition.strip() in text:
        return
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"{path}: expected exactly one anchor, got {count}: {anchor!r}")
    text = text.replace(anchor, anchor + addition, 1)
    target.write_text(text, encoding="utf-8")


def append_once(path: str, marker: str, content: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + content.strip() + "\n", encoding="utf-8")


insert_after(
    "PROJECT_INDEX.yaml",
    "  targeted_repair_cannot_mutate_prompt_or_canonical_authority: true\n",
    "  final_delta_learning_runtime_is_execution_only: true\n"
    "  final_delta_learning_cannot_promote_or_writeback: true\n"
    "  final_delta_single_success_cannot_generalize: true\n",
)
insert_after(
    "PROJECT_INDEX.yaml",
    "  targeted_repair_regression_cases: 11_验收/targeted_repair_regression_cases.yaml\n",
    "  final_delta_learning_policy: 10_运行时/final_delta_learning_policy.yaml\n"
    "  final_delta_learning_regression_cases: 11_验收/final_delta_learning_regression_cases.yaml\n",
)
insert_after(
    "PROJECT_INDEX.yaml",
    "  10_运行时/targeted_repair_policy.yaml: github_verified\n",
    "  10_运行时/final_delta_learning_policy.yaml: github_verified\n",
)
insert_after(
    "PROJECT_INDEX.yaml",
    "  11_验收/targeted_repair_regression_cases.yaml: github_verified\n",
    "  11_验收/final_delta_learning_regression_cases.yaml: github_verified\n",
)

insert_after(
    "10_运行时/read_sets.yaml",
    "      targeted_repair_regression: targeted_repair_regression_cases#when_targeted_repair_routing_preservation_or_authority_boundaries_are_relevant\n",
    "      final_delta_learning_policy: final_delta_learning_policy#when_repair_outcome_before_after_final_delta_or_candidate_learning_evidence_is_relevant\n"
    "      final_delta_learning_regression: final_delta_learning_regression_cases#when_repair_outcome_final_delta_or_learning_evidence_regression_is_relevant\n",
)
insert_after(
    "10_运行时/read_sets.yaml",
    "      targeted_repair_regression: targeted_repair_regression_cases#when_targeted_repair_runtime_or_authority_boundary_is_under_review\n",
    "      final_delta_learning_policy: final_delta_learning_policy#when_continual_learning_final_delta_causal_boundary_or_maturity_handoff_is_under_review\n"
    "      final_delta_learning_regression: final_delta_learning_regression_cases#when_final_delta_learning_runtime_or_non_promotion_gates_are_under_review\n",
)
insert_after(
    "10_运行时/write_routes.yaml",
    "  targeted_repair_regression_case: 11_验收/targeted_repair_regression_cases.yaml\n",
    "  final_delta_learning_regression_case: 11_验收/final_delta_learning_regression_cases.yaml\n",
)

append_once(
    "tools/learning_retriever/README.md",
    "## Repair Outcome / Final-Delta learning evidence",
    r'''## Repair Outcome / Final-Delta learning evidence

`learning_retriever.final_delta` closes the evidence bridge after Targeted Repair without turning a successful repair into an automatic rule. It consumes an already evaluated before state, an already evaluated after state, the exact Targeted Repair plan, an explicit change record, and optional human-supplied learning context.

The compiler mechanically reports field transitions such as `RESOLVED`, `PRESERVED`, `REGRESSED`, `PERSISTED`, `EVIDENCE_GAINED_PASS` and `EVIDENCE_LOST`. It also checks whether the before/after pair is actually comparable. A work-item, model, model-version, expectation-field, or expected-value mismatch prevents repair-effect attribution instead of silently pooling evidence.

A `CLEAN` controlled pair with one verified target variable may become `CONTROLLED_SINGLE_VARIABLE_CANDIDATE`, which means only **eligible for causal analysis**. It never means causality is proven. `causal_claim_authorized`, maturity promotion, learning writeback, canonical mutation, prompt mutation, generation and camera-authority mutation all remain false.

Missing alternative explanations or counterfactuals are emitted as `UNKNOWN_NOT_SUPPLIED`; the runtime does not invent them. Candidate learning evidence stays at `candidate`, requires targeted eval, and cannot write a regression case or promote itself.

Run the compiler on a prepared evidence package:

```bash
PYTHONPATH=tools/learning_retriever python -m learning_retriever.final_delta_cli \
  --project-root . \
  --package final_delta.yaml
```

Targeted regressions live in `11_验收/final_delta_learning_regression_cases.yaml`.
''',
)

print("Final-Delta wiring applied")
