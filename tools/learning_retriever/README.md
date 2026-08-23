# Learning Smart Recall / ApplicableLearningSet V1

This tool is an executable retrieval layer for the existing EUSTIA learning canonicals. It is **not** a second learning database.

Runtime order:

1. Task feature extraction
2. hard route resolution (`director_route_index.yaml`)
3. mechanism-first structured semantic recall (`learning_recall_index.yaml`)
4. scope / maturity / model-version / conflict filters
5. `ApplicableLearningSet`
6. prompt compilation by the existing director system
7. retrieval receipt
8. pre-output gate

The compact index stores routing metadata only. Full learning payloads remain authoritative in the referenced canonical files. `--expand` expands only selected Top-K cases for prompt-context use.

V1 uses deterministic weighted structured recall. Future embeddings may add candidate IDs, but candidates still pass authority, scope, maturity, model/version, conflict, negative-example and mandatory-route gates.

## CLI

```bash
python -m learning_retriever.cli --project-root ../.. --validate-index
python -m learning_retriever.cli --project-root ../.. --task task.json --top-k 5 --expand
```

A director task that reaches prompt compilation without a complete retrieval receipt, or misses a mandatory hard-route case, must fail closed and self-revise before output.
