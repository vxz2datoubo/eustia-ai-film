from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from production_intelligence.contracts import ProductionIntelligenceError
from production_intelligence.trusted_adapter import (
    GRAPH_PATH,
    LEARNING_WORKFLOW_PATH,
    PICG_WORKFLOW_PATH,
    TARGETED_REPAIR_POLICY_PATH,
    TRUSTED_ADAPTER_POLICY_PATH,
    validate_trusted_adapter_policy,
)

ROOT = Path(__file__).resolve().parents[3]


def read_yaml(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def materialize_minimal_root(tmp_path, *, adapter=None, repair=None, graph=None):
    documents = {
        TRUSTED_ADAPTER_POLICY_PATH: adapter or read_yaml(TRUSTED_ADAPTER_POLICY_PATH),
        TARGETED_REPAIR_POLICY_PATH: repair or read_yaml(TARGETED_REPAIR_POLICY_PATH),
        GRAPH_PATH: graph or read_yaml(GRAPH_PATH),
    }
    for path, payload in documents.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    for path in (PICG_WORKFLOW_PATH, LEARNING_WORKFLOW_PATH):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((ROOT / path).read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def test_real_trusted_adapter_policy_is_exactly_bound_to_current_repair_policy():
    result = validate_trusted_adapter_policy(ROOT)
    assert result["status"] == "PASS"
    assert result["serialized_route_authority"] is False
    assert result["failure_category_count"] >= 20


def test_category_cannot_route_to_capability_outside_canonical_repair_surface(tmp_path):
    adapter = deepcopy(read_yaml(TRUSTED_ADAPTER_POLICY_PATH))
    adapter["failure_category_consumer_map"]["camera"] = ["CAP-SOUND"]
    root = materialize_minimal_root(tmp_path, adapter=adapter)
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_trusted_adapter_policy(root)
    assert exc.value.code == "TRUSTED_ADAPTER_CONSUMER_ESCAPES_REPAIR_SURFACE"


def test_adapter_cannot_silently_ignore_new_canonical_failure_category(tmp_path):
    repair = deepcopy(read_yaml(TARGETED_REPAIR_POLICY_PATH))
    repair["failure_category_routes"]["future_new_failure"] = "UPSTREAM_CAMERA_CONTRACT_REVIEW"
    root = materialize_minimal_root(tmp_path, repair=repair)
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_trusted_adapter_policy(root)
    assert exc.value.code == "TRUSTED_ADAPTER_CATEGORY_COVERAGE_MISMATCH"


def test_adapter_cannot_create_second_repair_surface(tmp_path):
    adapter = deepcopy(read_yaml(TRUSTED_ADAPTER_POLICY_PATH))
    adapter["repair_surface_capability_allowlist"]["PICG_PRIVATE_REPAIR"] = ["CAP-SOUND"]
    root = materialize_minimal_root(tmp_path, adapter=adapter)
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_trusted_adapter_policy(root)
    assert exc.value.code == "TRUSTED_ADAPTER_SURFACE_COVERAGE_MISMATCH"


def test_learning_capability_is_forbidden_from_eval_adapter(tmp_path):
    adapter = deepcopy(read_yaml(TRUSTED_ADAPTER_POLICY_PATH))
    adapter["repair_surface_capability_allowlist"]["UPSTREAM_CAMERA_CONTRACT_REVIEW"].append(
        "CAP-LEARNING"
    )
    root = materialize_minimal_root(tmp_path, adapter=adapter)
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_trusted_adapter_policy(root)
    assert exc.value.code == "TRUSTED_ADAPTER_FORBIDDEN_CONSUMER"


def test_serialized_signal_envelope_can_never_be_promoted_by_policy_flag(tmp_path):
    adapter = deepcopy(read_yaml(TRUSTED_ADAPTER_POLICY_PATH))
    adapter["authority_boundary"]["serialized_signal_envelope_accepted_as_route_authority"] = True
    root = materialize_minimal_root(tmp_path, adapter=adapter)
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_trusted_adapter_policy(root)
    assert exc.value.code == "TRUSTED_ADAPTER_SERIALIZED_AUTHORITY_LEAK"
