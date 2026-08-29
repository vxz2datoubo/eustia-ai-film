# Learning Smart Recall / ApplicableLearningSet V1.1

This tool is the executable retrieval layer for the existing EUSTIA learning canonicals. It is **not** a second learning database.

V1.1 adds a bounded Director Feature Compiler in front of the existing retriever:

`natural-language director task -> dramatic_function -> relation_type -> spatial_action_features -> failure_mechanism -> existing LearningRetriever`

The compiler is query normalization only. It does not create learning rules, copy canonical payloads, change scope/maturity/conflict state, or replace `learning_application_gate.yaml` / `learning_recall_index.yaml` authority.

Its semantic contract is traced to the existing SOAC intermediate representation in `10_运行时/screen_observable_audible_ir_schema.yaml`, especially EventGraphIR, BlockingIR, ShotPlanIR and VisibleIR.

Runtime order:

1. Director Feature Compiler for natural-language tasks
2. hard route resolution (`director_route_index.yaml`)
3. mechanism-first structured semantic recall (`learning_recall_index.yaml`)
4. scope / maturity / model-version / conflict filters
5. `ApplicableLearningSet`
6. prompt compilation by the existing director system
7. retrieval receipt
8. pre-output gate

The compact index stores routing metadata only. Full learning payloads remain authoritative in the referenced canonical files. `--expand` expands only selected Top-K cases for prompt-context use.

V1.1 remains deterministic and fail-closed. An empty or unrecognized natural-language director description raises a feature-compilation failure instead of silently entering retrieval with four empty feature axes. Literal uses of `目标` as a creative objective do not create a locatable spatial target unless a spatial action/relation is also present.

Cross-surface regressions are canonicalized in `11_验收/director_feature_compiler_regression_cases.yaml` and CI executes that file directly, including different characters, scenes and wording that must resolve to compatible mechanisms or the same canonical learning case when such a case exists.

## CinematicIntent contract runtime

When the canonical SOAC schema contains `CinematicIntentIR`, this package also exposes a bounded mechanical contract runtime in `learning_retriever.cinematic_intent`. It does **not** decide how a shot should look. Directing method remains in `01_AI电影系统/AI电影系统.md#CINEMATIC-VISUAL-GRAMMAR-001`; the executable field/static-check vocabulary remains in `10_运行时/screen_observable_audible_ir_schema.yaml#CinematicIntentIR`.

The contract runtime can:

- reject unknown or authority-violating fields before compilation;
- reuse canonical SOAC warning/error IDs for static evaluation;
- fail closed on camera position/lens intent until a canonical machine-readable upstream camera binding can be read back;
- compile only explicitly material visual-intent fields into the current-generation overlay;
- require non-empty provenance for every emitted material field;
- emit reverse-eval expectations by carrying the declared value and provenance forward without inventing new observations.

It cannot mutate Blocking, map, story, character, asset, continuity or learning truth. Aesthetic incompleteness remains a warning; structural authority violations fail closed before overlay compilation.

Example YAML contract:

```yaml
contract_id: DEMO-CINEMATIC-INTENT
intent:
  composition:
    primary_mechanism: lateral_pressure
    camera_reason: 保持右到左逃亡方向清楚可读
  color_intent:
    color_thesis: 阴冷石城中保留人物真实肤色与布料差异
    physical_color_sources: [灰石墙, 阴天自然光, 衣物本色]
provenance:
  composition:
    source: director_visual_plan
  color_intent:
    source: scene_look_plan
context:
  material_fields: [composition, color_intent]
```

The downstream proposal cannot carry camera locks, and no Python/YAML/JSON/CLI invocation surface can supply or mint camera-lock authority. The current project does not yet expose a canonical machine-readable ShotPlan/Blocking camera-lock readback to this runtime. Therefore any `capture_intent` that materially proposes `camera_physical_position` or `lens_intent` fails closed with `MISSING_CANONICAL_UPSTREAM_BINDING`. This is an intentional capability gap, not a hidden token mechanism. Re-opening camera-sensitive compilation requires a later canonical upstream readback integration and regression, not a private Python name, digest, envelope, or caller-provided capability.

CLI note: the standalone contract CLI has no camera-authority input. Camera-sensitive contracts fail closed identically through CLI and Python until canonical readback exists.

Targeted contract regressions live in `11_验收/cinematic_intent_contract_regression_cases.yaml` and are executed explicitly by CI.

## Expected-vs-Observed reverse evaluation

`learning_retriever.expected_observed` executes the existing SOAC chain `ReverseObservation -> ExpectedVsObservedEval -> TargetedRepair`. It compares **supplied** observations with declared `reverse_eval_expectations`; it does not inspect media by itself and must never be described as an automatic video/image/audio grader.

The evaluator consumes expectations already emitted by the trusted CinematicIntent execution path. It does not reconstruct camera-lock authority from observed output, does not mint a replacement upstream lock envelope, and cannot treat reverse observation as a source of canonical intent.

Key evidence rules:

- missing observation becomes `UNKNOWN`, not automatic `FAIL`;
- fixed-interval screenshots, selected frames, contact sheets and sparse sampling stay labeled sampled evidence and cannot claim frame-by-frame review;
- a `FAIL` must use a failure category already declared by `screen_observable_audible_ir_schema.yaml#reverse_compiler`;
- the repair handoff contains only failed/unknown fields and cannot rewrite a prompt by itself;
- the learning handoff is evidence only: it cannot write back or promote maturity;
- an A/B target variable with no recorded confound is still `UNVERIFIED_CONTROL`; `CLEAN` additionally requires explicit non-target-control verification plus provenance; any recorded material confound produces `CONFOUNDED`.

Example evaluation:

```yaml
eval_id: DEMO-EOE
expectations:
  - field: attention_handoff
    declared_value:
      reveal_on_return: subject_already_absent
    provenance:
      source: cinematic_intent_contract
reverse_observation:
  fields:
    observed_attention_handoff:
      return_master_first_sample: subject_absent
  expectation_observations:
    attention_handoff:
      comparison_mode: explicit_observation_judgment
      match_state: MATCH
      observed_value:
        return_master_first_sample: subject_absent
      evidence_refs: [sample_24, sample_25]
  provenance:
    evidence_source: fixed_interval_screenshot_archive
    inspection_mode: fixed_interval_sampling
    temporal_coverage:
      type: full_duration_sampled
      sample_interval_seconds: 0.25
    confidence: MEDIUM
    media_refs: [screenshot_archive_001]
    claimed_frame_by_frame_review: false
context:
  model: C-DANCE
  model_version: "2.5"
```

Run it directly:

```bash
PYTHONPATH=tools/learning_retriever python -m learning_retriever.expected_observed_cli \
  --project-root . \
  --eval expected_observed.yaml
```

Exit code is `0` for complete PASS, `2` for FAIL/structural rejection, and `3` for an INCOMPLETE evaluation containing one or more `UNKNOWN` expectations. Targeted regression cases live in `11_验收/expected_observed_eval_regression_cases.yaml`.

## Expected-vs-Observed reverse evaluation

`learning_retriever.expected_observed` executes the existing SOAC chain `ReverseObservation -> ExpectedVsObservedEval -> TargetedRepair`. It compares **supplied** observations with declared `reverse_eval_expectations`; it does not inspect media by itself and must never be described as an automatic video/image/audio grader.

The evaluator consumes expectations already emitted by the CinematicIntent execution path. It does not reconstruct camera authority from observed output, does not mint a replacement upstream binding, and cannot treat reverse observation as a source of canonical intent. Camera-sensitive upstream intent remains subject to the canonical-readback fail-closed gate described above.

Key evidence rules:

- missing observation becomes `UNKNOWN`, not automatic `FAIL`;
- fixed-interval screenshots, selected frames, contact sheets and sparse sampling stay labeled sampled evidence and cannot claim frame-by-frame review;
- a `FAIL` must use a failure category already declared by `screen_observable_audible_ir_schema.yaml#reverse_compiler`;
- the repair handoff contains only failed/unknown fields and cannot rewrite a prompt by itself;
- the learning handoff is evidence only: it cannot write back or promote maturity;
- an A/B target variable with no recorded confound is still `UNVERIFIED_CONTROL`; `CLEAN` additionally requires explicit non-target-control verification plus provenance; any recorded material confound produces `CONFOUNDED`.

Example evaluation:

```yaml
eval_id: DEMO-EOE
expectations:
  - field: attention_handoff
    declared_value:
      reveal_on_return: subject_already_absent
    provenance:
      source: cinematic_intent_contract
reverse_observation:
  fields:
    observed_attention_handoff:
      return_master_first_sample: subject_absent
  expectation_observations:
    attention_handoff:
      comparison_mode: explicit_observation_judgment
      match_state: MATCH
      observed_value:
        return_master_first_sample: subject_absent
      evidence_refs: [sample_24, sample_25]
  provenance:
    evidence_source: fixed_interval_screenshot_archive
    inspection_mode: fixed_interval_sampling
    temporal_coverage:
      type: full_duration_sampled
      sample_interval_seconds: 0.25
    confidence: MEDIUM
    media_refs: [screenshot_archive_001]
    claimed_frame_by_frame_review: false
context:
  model: C-DANCE
  model_version: "2.5"
```

Run it directly:

```bash
PYTHONPATH=tools/learning_retriever python -m learning_retriever.expected_observed_cli \
  --project-root . \
  --eval expected_observed.yaml
```

Exit code is `0` for complete PASS, `2` for FAIL/structural rejection, and `3` for an INCOMPLETE evaluation containing one or more `UNKNOWN` expectations. Targeted regression cases live in `11_验收/expected_observed_eval_regression_cases.yaml`.

## CLI

Validate the existing recall index:

```bash
PYTHONPATH=tools/learning_retriever python -m learning_retriever.cli --project-root . --validate-index
```

Validate the compiler's SOAC / EventGraphIR / BlockingIR / VisibleIR dependencies:

```bash
PYTHONPATH=tools/learning_retriever python -m learning_retriever.cli --project-root . --validate-feature-compiler
```

Retrieve from a natural-language director task:

```bash
PYTHONPATH=tools/learning_retriever python -m learning_retriever.cli \
  --project-root . \
  --description "城堡大厅里卫兵面向门口逃犯追击，人物朝向不能和目标方向打架" \
  --task-id DEMO-TARGET-BINDING \
  --top-k 5 \
  --expand
```

Structured JSON tasks remain supported unchanged:

```bash
PYTHONPATH=tools/learning_retriever python -m learning_retriever.cli --project-root . --task task.json --top-k 5 --expand
```

A structured JSON task may also contain `director_task_description`; the compiler unions compiled features with any explicit structured features instead of replacing them.

A director task that reaches prompt compilation without a complete retrieval receipt, misses a mandatory hard-route case, or fails natural-language feature compilation must fail closed before output.
