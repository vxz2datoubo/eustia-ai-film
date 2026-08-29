from pathlib import Path

ROOT = Path.cwd()


def after(text: str, anchor: str, addition: str, label: str) -> str:
    if addition.strip() in text:
        return text
    if text.count(anchor) != 1:
        raise SystemExit(f"{label}: anchor count={text.count(anchor)}")
    return text.replace(anchor, anchor + addition, 1)


def before(text: str, anchor: str, addition: str, label: str) -> str:
    if addition.strip() in text:
        return text
    if text.count(anchor) != 1:
        raise SystemExit(f"{label}: anchor count={text.count(anchor)}")
    return text.replace(anchor, addition + anchor, 1)


p = ROOT / "PROJECT_INDEX.yaml"
s = p.read_text(encoding="utf-8")
s = after(s, "  expected_observed_eval_cannot_claim_automatic_media_grading: true\n", "  targeted_repair_runtime_is_execution_only: true\n  targeted_repair_cannot_mutate_prompt_or_canonical_authority: true\n", "project policy")
s = after(s, "  expected_observed_eval_regression_cases: 11_验收/expected_observed_eval_regression_cases.yaml\n", "  targeted_repair_policy: 10_运行时/targeted_repair_policy.yaml\n  targeted_repair_regression_cases: 11_验收/targeted_repair_regression_cases.yaml\n", "canonical entries")
s = after(s, "  10_运行时/learning_recall_index.yaml: github_verified\n", "  10_运行时/targeted_repair_policy.yaml: github_verified\n", "effective policy")
s = after(s, "  11_验收/expected_observed_eval_regression_cases.yaml: github_verified\n", "  11_验收/targeted_repair_regression_cases.yaml: github_verified\n", "effective regression")
p.write_text(s, encoding="utf-8")

p = ROOT / "10_运行时/read_sets.yaml"
s = p.read_text(encoding="utf-8")
s = after(s, "      expected_observed_eval_regression: expected_observed_eval_regression_cases#when_generated_output_reverse_observation_expected_vs_observed_eval_or_targeted_repair_handoff_is_relevant\n", "      targeted_repair_policy: targeted_repair_policy#when_expected_observed_FAIL_or_UNKNOWN_requires_failed_dimension_repair_routing\n      targeted_repair_regression: targeted_repair_regression_cases#when_targeted_repair_routing_preservation_or_authority_boundaries_are_relevant\n", "directing read set")
s = after(s, "      expected_observed_eval_regression: expected_observed_eval_regression_cases#when_reverse_observation_eval_evidence_truthfulness_or_control_status_is_under_review\n", "      targeted_repair_policy: targeted_repair_policy#when_targeted_repair_routing_or_failed_dimension_preservation_is_under_review\n      targeted_repair_regression: targeted_repair_regression_cases#when_targeted_repair_runtime_or_authority_boundary_is_under_review\n", "research read set")
p.write_text(s, encoding="utf-8")

p = ROOT / "10_运行时/write_routes.yaml"
s = p.read_text(encoding="utf-8")
s = after(s, "  expected_observed_eval_regression_case: 11_验收/expected_observed_eval_regression_cases.yaml\n", "  targeted_repair_regression_case: 11_验收/targeted_repair_regression_cases.yaml\n", "write route")
p.write_text(s, encoding="utf-8")

p = ROOT / "tools/learning_retriever/learning_retriever/__init__.py"
s = p.read_text(encoding="utf-8")
s = after(s, "from .runtime import DirectorLearningRuntime\n", "from .targeted_repair import (\n    TargetedRepairPlanError,\n    plan_targeted_repair,\n)\n", "package import")
s = after(s, '    "RouteResolutionError",\n', '    "TargetedRepairPlanError",\n', "error export")
s = after(s, '    "evaluate_expected_vs_observed",\n', '    "plan_targeted_repair",\n', "function export")
p.write_text(s, encoding="utf-8")

p = ROOT / "tools/learning_retriever/README.md"
s = p.read_text(encoding="utf-8")
section = '''## Targeted Repair planner\n\n`learning_retriever.targeted_repair` consumes the verified Expected-vs-Observed result and implements the existing SOAC `TargetedRepair` stage as **routing only**. It protects PASS dimensions, sends UNKNOWN dimensions to evidence acquisition, and routes FAIL dimensions to the existing director/camera/transition/reference/blocking/performance/sound authority surface. It does not decide the creative fix.\n\nThe planner cross-checks `targeted_repair_handoff.items` against the source evaluation results so a caller cannot silently add, remove or substitute repair items. Every canonical reverse-compiler failure category must map to exactly one declared repair surface or the policy fails closed. Control status and observation provenance are carried forward; `CLEAN` means eligible for later causal analysis, not automatic causal truth.\n\nCamera failures route to `UPSTREAM_CAMERA_CONTRACT_REVIEW`, but the planner cannot mint, reconstruct, or mutate camera authority. The upstream CinematicIntent canonical-readback fail-closed boundary remains intact.\n\nRun it on an evaluator result:\n\n```bash\nPYTHONPATH=tools/learning_retriever python -m learning_retriever.targeted_repair_cli \\\n  --project-root . \\\n  --eval-result expected_observed_result.yaml\n```\n\nThe output is an ephemeral repair plan. Prompt mutation, generation, camera-authority mutation, canonical writes, learning writeback and maturity promotion remain unauthorized. Targeted regressions live in `11_验收/targeted_repair_regression_cases.yaml`.\n\n'''
s = before(s, "## CLI\n", section, "README section")
p.write_text(s, encoding="utf-8")

Path("tools/learning_retriever/_tmp_wire_targeted_repair_current.py").unlink()
print("wired targeted repair current stack")