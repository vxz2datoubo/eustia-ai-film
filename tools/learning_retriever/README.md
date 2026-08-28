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
- compare a declared camera position against a locked camera contract;
- compile only explicitly material visual-intent fields into the current-generation overlay;
- require provenance for every emitted material field;
- emit reverse-eval expectations by carrying the declared value and provenance forward without inventing new observations.

It cannot mutate Blocking, map, story, character, asset, continuity or learning truth. Aesthetic incompleteness remains a warning unless a canonical or locked contract is actually violated.

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
    source: director_locked_camera_plan
  color_intent:
    source: scene_look_plan
context:
  material_fields: [composition, color_intent]
```

The downstream proposal cannot carry camera locks. Camera-lock authority enters through a separate upstream envelope whose canonical `source_authority_ref + camera` payload is SHA-256 hashed by the runtime and must exactly match both the envelope digest and a separately supplied trusted upstream digest. Current canonical `capture_intent` can mechanically propose only camera physical position and lens intent, so those are the only accepted lock surfaces in this runtime. Orientation, shot size, camera height and camera motion remain owned by upstream ShotPlan/Visible camera state and fail closed here rather than being accepted inertly.

Example upstream lock envelope:

```yaml
source_authority_ref: shot_plan://current_generation/camera_state
source_material_digest: <sha256-of-trusted-upstream-source-material>
camera:
  position: exterior_side
  lens_intent: side_profile_readability
```

Run it directly:

```bash
PYTHONPATH=tools/learning_retriever python -m learning_retriever.cinematic_intent \
  --project-root . \
  --contract cinematic_intent.yaml \
  --upstream-lock-envelope upstream_camera_lock.yaml \
  --trusted-upstream-source-digest <trusted-sha256-from-upstream-orchestration>
```

Targeted contract regressions live in `11_验收/cinematic_intent_contract_regression_cases.yaml` and are executed explicitly by CI.

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
