from copy import deepcopy
from pathlib import Path

import pytest

from production_intelligence.contracts import (
    LEARNING_WORKFLOW_PATH,
    PICG_WORKFLOW_PATH,
    RESEARCH_POLICY_PATH,
    SIGNAL_SCHEMA_PATH,
    ProductionIntelligenceError,
    load_yaml,
    validate_research_policy,
    validate_signal_schema,
    validate_workflow_coverage,
)

ROOT = Path(__file__).resolve().parents[3]


def test_signal_schema_identity_and_executable_vocabulary_are_bound():
    schema = load_yaml(ROOT / SIGNAL_SCHEMA_PATH)
    validate_signal_schema(schema)

    broken = deepcopy(schema)
    broken["schema_id"] = "OTHER"
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_signal_schema(broken)
    assert exc.value.code == "SIGNAL_SCHEMA_ID_MISMATCH"

    broken = deepcopy(schema)
    broken["signal_types"].pop("DIRECTOR_FEATURE_RECEIPT")
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_signal_schema(broken)
    assert exc.value.code == "SIGNAL_EXECUTABLE_BINDING_OUT_OF_SYNC"


def test_signal_stage_contract_drift_is_rejected():
    schema = load_yaml(ROOT / SIGNAL_SCHEMA_PATH)
    broken = deepcopy(schema)
    broken["signal_types"]["GENERATION_RESULT"]["valid_source_stages"] = ["NOT_A_STAGE"]
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_signal_schema(broken)
    assert exc.value.code == "SIGNAL_SCHEMA_TYPE_STAGE_CONTRACT_INVALID"


def test_research_policy_identity_authority_and_boundary_are_machine_bound():
    policy = load_yaml(ROOT / RESEARCH_POLICY_PATH)
    validate_research_policy(policy)

    broken = deepcopy(policy)
    broken["authority_boundary"]["rules"].remove(
        "external_research_cannot_self_promote_maturity"
    )
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_research_policy(broken)
    assert exc.value.code == "RESEARCH_POLICY_AUTHORITY_RULES_INCOMPLETE"

    broken = deepcopy(policy)
    broken["research_unit"]["required_fields"].remove("failure_boundary")
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_research_policy(broken)
    assert exc.value.code == "RESEARCH_POLICY_UNIT_FIELDS_INCOMPLETE"


def test_real_repository_workflows_cover_all_picg_safety_files():
    validate_workflow_coverage(ROOT)


def test_workflow_coverage_check_fails_when_signal_or_research_policy_is_omitted(tmp_path):
    picg = tmp_path / PICG_WORKFLOW_PATH
    learning = tmp_path / LEARNING_WORKFLOW_PATH
    picg.parent.mkdir(parents=True, exist_ok=True)

    almost_complete = "\n".join(
        [
            "10_运行时/production_intelligence_capability_graph.yaml",
            "10_运行时/production_intelligence_epistemic_cycle_policy.yaml",
            "10_运行时/production_handoff_packet_schema.yaml",
            "11_验收/production_intelligence_capability_graph_regression_cases.yaml",
            "tools/production_intelligence/**",
        ]
    )
    picg.write_text(almost_complete, encoding="utf-8")
    learning.write_text(almost_complete, encoding="utf-8")

    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_workflow_coverage(tmp_path)
    assert exc.value.code == "PICG_WORKFLOW_COVERAGE_INCOMPLETE"
    missing = set(exc.value.details["missing"])
    assert "10_运行时/production_intelligence_signal_envelope_schema.yaml" in missing
    assert "10_运行时/production_intelligence_research_intake_policy.yaml" in missing
