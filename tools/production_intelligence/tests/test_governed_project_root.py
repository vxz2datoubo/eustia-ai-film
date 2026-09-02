from pathlib import Path

import pytest
import yaml

from production_intelligence.contracts import GRAPH_PATH, SIGNAL_SCHEMA_PATH, ProductionIntelligenceError, load_yaml
from production_intelligence.runtime import CapabilityAtlas, resolve_expected_observed
from production_intelligence.trusted_adapter import (
    compile_expected_observed_coordination,
    load_trusted_adapter_policy,
)

ROOT = Path(__file__).resolve().parents[3]
SUITE = yaml.safe_load(
    (ROOT / "11_验收/expected_observed_eval_regression_cases.yaml").read_text(encoding="utf-8")
)


def payload(case_id="EOE-EXPLICIT-FAIL-001"):
    return next(item for item in SUITE["cases"] if item["id"] == case_id)["payload"]


def test_initial_atlas_root_cannot_be_caller_selected(tmp_path):
    with pytest.raises(ProductionIntelligenceError) as exc:
        CapabilityAtlas.from_project_root(tmp_path)
    assert exc.value.code == "TRUSTED_ADAPTER_PROJECT_ROOT_FORBIDDEN"


def test_direct_constructor_cannot_attach_canonical_objects_to_alternate_root(tmp_path):
    graph = load_yaml(ROOT / GRAPH_PATH)
    signal = load_yaml(ROOT / SIGNAL_SCHEMA_PATH)
    policy = load_trusted_adapter_policy(ROOT)
    with pytest.raises(ProductionIntelligenceError) as exc:
        CapabilityAtlas(graph, signal, policy, project_root=tmp_path)
    assert exc.value.code == "TRUSTED_ADAPTER_PROJECT_ROOT_FORBIDDEN"


def test_receipt_mint_cannot_use_alternate_project_tree(tmp_path):
    with pytest.raises(ProductionIntelligenceError) as exc:
        compile_expected_observed_coordination(payload(), project_root=tmp_path)
    assert exc.value.code == "TRUSTED_ADAPTER_PROJECT_ROOT_FORBIDDEN"


def test_public_resolve_wrapper_cannot_switch_trust_universe(tmp_path):
    with pytest.raises(ProductionIntelligenceError) as exc:
        resolve_expected_observed(payload(), project_root=tmp_path)
    assert exc.value.code == "TRUSTED_ADAPTER_PROJECT_ROOT_FORBIDDEN"
