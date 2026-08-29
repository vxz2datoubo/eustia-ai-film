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
    target.write_text(text.replace(anchor, anchor + addition, 1), encoding="utf-8")


def append_once(path: str, marker: str, content: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + content.strip() + "\n", encoding="utf-8")


insert_after(
    "PROJECT_INDEX.yaml",
    "  final_delta_single_success_cannot_generalize: true\n",
    "  post_final_delta_validation_runtime_is_execution_only: true\n"
    "  post_final_delta_validation_cannot_promote_or_write: true\n"
    "  post_final_delta_cross_version_pooling_forbidden: true\n",
)
insert_after(
    "PROJECT_INDEX.yaml",
    "  final_delta_learning_regression_cases: 11_验收/final_delta_learning_regression_cases.yaml\n",
    "  post_final_delta_validation_policy: 10_运行时/post_final_delta_validation_policy.yaml\n"
    "  post_final_delta_validation_regression_cases: 11_验收/post_final_delta_validation_regression_cases.yaml\n",
)
insert_after(
    "PROJECT_INDEX.yaml",
    "  10_运行时/final_delta_learning_policy.yaml: github_verified\n",
    "  10_运行时/post_final_delta_validation_policy.yaml: github_verified\n",
)
insert_after(
    "PROJECT_INDEX.yaml",
    "  11_验收/final_delta_learning_regression_cases.yaml: github_verified\n",
    "  11_验收/post_final_delta_validation_regression_cases.yaml: github_verified\n",
)

insert_after(
    "10_运行时/read_sets.yaml",
    "      final_delta_learning_regression: final_delta_learning_regression_cases#when_repair_outcome_final_delta_or_learning_evidence_regression_is_relevant\n",
    "      post_final_delta_validation_policy: post_final_delta_validation_policy#when_final_delta_evidence_cohort_regression_proposal_or_maturity_assessment_is_relevant\n"
    "      post_final_delta_validation_regression: post_final_delta_validation_regression_cases#when_post_final_delta_partition_conflict_or_maturity_gate_is_relevant\n",
)
insert_after(
    "10_运行时/read_sets.yaml",
    "      final_delta_learning_regression: final_delta_learning_regression_cases#when_final_delta_learning_runtime_or_non_promotion_gates_are_under_review\n",
    "      post_final_delta_validation_policy: post_final_delta_validation_policy#when_evidence_aggregation_regression_proposal_or_maturity_governance_is_under_review\n"
    "      post_final_delta_validation_regression: post_final_delta_validation_regression_cases#when_post_final_delta_validation_runtime_is_under_review\n",
)
insert_after(
    "10_运行时/write_routes.yaml",
    "  final_delta_learning_regression_case: 11_验收/final_delta_learning_regression_cases.yaml\n",
    "  post_final_delta_validation_regression_case: 11_验收/post_final_delta_validation_regression_cases.yaml\n",
)

append_once(
    "tools/learning_retriever/README.md",
    "## Post-Final-Delta evidence validation",
    r'''## Post-Final-Delta evidence validation

`learning_retriever.post_final_delta` operates after Final-Delta. It does not discover or semantically cluster hypotheses. The caller supplies an explicit `hypothesis_id`; evidence is then partitioned by exact model, model version, and exact candidate-lesson payload before any summary is produced.

Each Final-Delta record is classified as `SUPPORTING`, `CONTRADICTORY`, or `INCONCLUSIVE`. A support/contradiction pair inside the same exact cohort remains an explicit conflict; there is no latest-wins resolution. Different model versions stay in separate cohorts.

Eligible supporting Final-Delta records may produce an ephemeral regression proposal, but the proposal has no canonical target and `write_authorized: false`. It is evidence for a later governed regression decision, not an automatic test insertion.

Maturity assessment is also non-authoritative. `scene_verified` requires a trusted user/canonical confirmation binding that this runtime cannot mint from caller-supplied fields. `project_verified` and `general_stable` always route through the governed high-impact promotion gate. All promotion/write/mutation flags remain false.

Run an assessment:

```bash
PYTHONPATH=tools/learning_retriever python -m learning_retriever.post_final_delta_cli \
  --project-root . \
  --assessment post_final_delta.yaml
```

Targeted regressions live in `11_验收/post_final_delta_validation_regression_cases.yaml`.
''',
)

print("post-Final-Delta wiring applied")
