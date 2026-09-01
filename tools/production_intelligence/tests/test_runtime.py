from copy import deepcopy
from pathlib import Path

import pytest

from production_intelligence.runtime import (
    CapabilityAtlas,
    ProductionIntelligenceError,
    validate_handoff_packet,
    validate_handoff_transition,
    validate_project,
)

ROOT = Path(__file__).resolve().parents[3]
WORK_ITEM = "KAIM-SCARF-CLOTHESLINE-CURRENT"


def atlas():
    return CapabilityAtlas.from_project_root(ROOT)


def base_packet():
    return {
        "packet_id": "PHP-TEST-001",
        "task": {"task_id": "T1", "task_class": "COMPILE_MODEL_EXECUTION", "state": "READY"},
        "context": {
            "project_id": "EUSTIA_AI_FILM",
            "work_item_id_when_required": WORK_ITEM,
            "context_level": "SHOT",
        },
        "participant": {"owner_role": "MODEL_ADAPTER"},
        "authority_receipt": {
            "project_index_ref": "PROJECT_INDEX.yaml",
            "canonical_refs_used": ["03_剧本与改编/当前改编剧本.md"],
            "user_explicit_constraints": ["no_open_sky"],
            "inferred_user_constraints": [],
            "external_candidate_refs": [],
        },
        "creative_contract": {
            "dramatic_function_when_material": "expert_escape_motion",
            "audience_knowledge_before_when_material": "Kaim is traversing the gap",
            "audience_knowledge_after_when_material": "scarf traverse remains physically readable",
            "hard_invariants": ["fixed_clothesline", "body_below_line"],
            "guided_constraints": ["expert_efficiency"],
            "free_space": ["micro_balance_corrections"],
            "final_state_when_material": "near_left_building",
        },
        "inputs": {
            "consumed_assets": [],
            "reference_responsibilities": {
                "geometry": {"owner": "WHITE_MODEL"},
                "identity": {"owner": "REFERENCE_IMAGE"},
            },
        },
        "expected_outputs": {
            "output_type": "MODEL_PROMPT",
            "observable_or_audible_expectations": [
                {
                    "expectation_id": "E1",
                    "dimension": "SUPPORT_CONTACT_TOPOLOGY",
                    "description": "scarf and body co-move while line stays fixed",
                    "materiality": "HARD",
                    "evidence_required": True,
                }
            ],
        },
        "acceptance_contract": {
            "material_dimensions": ["SUPPORT_CONTACT_TOPOLOGY", "SPATIAL_RELATION_TRAJECTORY"],
            "measurement_plan": {"inspection_mode": "TEMPORAL_SAMPLE_REVIEW"},
            "pass_logic": {"global_score_overrides_material_failure": False},
        },
        "unresolved_unknowns": [],
        "next_handoff": {"next_owner": "GENERATION_SERVICE", "next_task_class": "GENERATE"},
    }


def material_unknown():
    return {
        "unknown_id_or_local_id": "U-MODEL-CONTROL-001",
        "question": "Does the current target version preserve the required contact relation?",
        "epistemic_zone": "K4_FRONTIER_OR_OPAQUE",
        "materiality": "HIGH",
        "safe_default": "do_not_claim_verified",
        "next_information_action": "targeted final-model probe",
    }


def downstream_packet(*, include_hard=True, include_unknown=True):
    packet = base_packet()
    packet["packet_id"] = "PHP-TEST-002"
    packet["task"] = {"task_id": "T2", "task_class": "GENERATE", "state": "READY"}
    packet["participant"] = {"owner_role": "GENERATION_SERVICE"}
    packet["expected_outputs"]["output_type"] = "GENERATED_VIDEO"
    packet["next_handoff"] = {
        "next_owner": "REVERSE_OBSERVATION_EVAL",
        "next_task_class": "REVERSE_OBSERVE",
    }
    if not include_hard:
        packet["creative_contract"]["hard_invariants"] = ["fixed_clothesline"]
    if include_unknown:
        packet["unresolved_unknowns"] = [material_unknown()]
    return packet


def validate(packet, expected_work_item_id=None):
    return validate_handoff_packet(
        packet,
        project_root=ROOT,
        expected_work_item_id=expected_work_item_id,
    )


def test_project_schema_bundle_validates_all_machine_contracts():
    receipt = validate_project(ROOT)
    assert receipt["status"] == "PASS"
    assert receipt["epistemic_zone_count"] == 4
    assert receipt["regression_case_count"] >= 20
    assert receipt["capability_count"] >= 15
    assert receipt["signal_type_count"] >= 10
    assert receipt["signal_envelope_bound"] is True
    assert receipt["handoff_nested_contract_bound"] is True
    assert receipt["research_policy_bound"] is True
    assert receipt["workflow_coverage_bound"] is True


@pytest.mark.parametrize(
    "profile,expected",
    [
        ({"primary_factor_known": True, "factor_count": 1}, "COMPARATIVE_AB"),
        ({"factor_count": 5}, "SCREENING"),
        ({"factor_count": 3, "interaction_suspected": True}, "BOUNDED_FACTORIAL"),
        ({"expensive_final_model": True, "valid_proxy_available": True}, "SEQUENTIAL_PROBE"),
        ({"continuous_parameter": True}, "PARAMETER_SEARCH"),
        ({"evaluator_disagreement": True, "decision_impact": "HIGH"}, "MEASUREMENT_SYSTEM_CHECK"),
        ({"external_knowledge_missing": True}, "EXTERNAL_RESEARCH"),
        ({"high_impact_human_choice": True}, "HUMAN_DECISION"),
    ],
)
def test_experiment_strategy(profile, expected):
    assert atlas().select_experiment_strategy(profile) == expected


def test_handoff_work_item_match_passes():
    assert validate(base_packet(), expected_work_item_id=WORK_ITEM)


def test_handoff_work_item_mismatch_fails():
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(base_packet(), expected_work_item_id="KAIM-HIGH-SEARCH-OLD")
    assert exc.value.code == "WORK_ITEM_IDENTITY_MISMATCH"


def test_k2_inference_requires_provenance_and_cannot_self_confirm():
    packet = base_packet()
    packet["authority_receipt"]["inferred_user_constraints"] = [
        {
            "statement": "prefers motivated light",
            "confidence": "HIGH",
            "evidence": ["review-1"],
            "explicit_user_confirmed": True,
        }
    ]
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == "K2_INFERENCE_MASQUERADES_AS_EXPLICIT_USER_FACT"


def test_k3_external_candidate_requires_scope_boundary_and_candidate_maturity():
    packet = base_packet()
    packet["authority_receipt"]["external_candidate_refs"] = [
        {
            "source_ref": "ASC_FDL",
            "supported_claim": "framing intent can be serialized",
            "project_translation": "framing receipt",
            "scope": "cross-department framing handoff",
            "boundary": "not an aesthetic authority",
            "maturity": "candidate",
        }
    ]
    assert validate(packet)


def test_k4_unknown_requires_complete_safe_information_contract():
    packet = base_packet()
    unknown = material_unknown()
    del unknown["next_information_action"]
    packet["unresolved_unknowns"] = [unknown]
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == "K4_UNKNOWN_REQUIRED_FIELD_MISSING"


def test_strong_reference_responsibility_conflict_fails():
    packet = base_packet()
    packet["inputs"]["reference_responsibilities"]["camera"] = {
        "owners": ["WHITE_MODEL", "REFERENCE_VIDEO"],
        "both_declared_strong": True,
        "compatibility_proven": False,
    }
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == "STRONG_REFERENCE_RESPONSIBILITY_CONFLICT"


def test_global_score_cannot_hide_material_failure():
    packet = base_packet()
    packet["acceptance_contract"]["pass_logic"] = {
        "global_score_overrides_material_failure": True
    }
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == "GLOBAL_SCORE_HIDES_MATERIAL_FAILURE"


def test_multifactor_experiment_requires_factor_ledger():
    packet = base_packet()
    packet["experiment_contract"] = {
        "hypothesis": "several mechanisms may explain the failure",
        "strategy": "SCREENING",
        "factors": ["reference", "camera", "contact"],
        "controlled_variables": [],
        "response_dimensions": ["SUPPORT_CONTACT_TOPOLOGY"],
        "confounds": [],
        "proxy_vs_final_role": "final only",
        "stop_condition": "dominant candidates identified",
    }
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == "MULTIFACTOR_EXPERIMENT_WITHOUT_LEDGER"


def test_proxy_pass_cannot_equal_final_pass():
    packet = base_packet()
    packet["experiment_contract"] = {
        "hypothesis": "cheap proxy can screen event order",
        "strategy": "SEQUENTIAL_PROBE",
        "factors": ["model_stage"],
        "factor_ledger": ["proxy_vs_final"],
        "controlled_variables": [],
        "response_dimensions": ["EVENT_ORDER_CAUSALITY"],
        "confounds": [],
        "proxy_vs_final_role": "proxy screens structure only",
        "proxy_pass_equals_final_pass": True,
        "stop_condition": "structural screen complete",
    }
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == "PROXY_FINAL_CONFUSION"


@pytest.mark.parametrize(
    "section,replacement,expected_code",
    [
        ("task", {}, "HANDOFF_TASK_REQUIRED_FIELD_MISSING"),
        ("participant", {}, "HANDOFF_PARTICIPANT_REQUIRED_FIELD_MISSING"),
        ("authority_receipt", {}, "HANDOFF_AUTHORITY_REQUIRED_FIELD_MISSING"),
        ("creative_contract", {}, "HANDOFF_CREATIVE_REQUIRED_FIELD_MISSING"),
        ("inputs", {}, "HANDOFF_INPUTS_REQUIRED_FIELD_MISSING"),
        ("expected_outputs", {}, "HANDOFF_EXPECTED_OUTPUT_REQUIRED_FIELD_MISSING"),
        ("next_handoff", {}, "HANDOFF_NEXT_REQUIRED_FIELD_MISSING"),
    ],
)
def test_authority_critical_nested_subtree_deletion_fails_closed(section, replacement, expected_code):
    packet = base_packet()
    packet[section] = replacement
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == expected_code


def test_measurement_plan_deletion_fails_closed():
    packet = base_packet()
    packet["acceptance_contract"]["measurement_plan"] = {}
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == "HANDOFF_MEASUREMENT_REQUIRED_FIELD_MISSING"


def test_consumed_asset_shape_and_role_are_machine_validated():
    packet = base_packet()
    packet["inputs"]["consumed_assets"] = [
        {"asset_ref": "EUS-AST-000010", "authority_status": "active"}
    ]
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == "HANDOFF_CONSUMED_ASSET_FIELD_MISSING"


def test_expected_dimension_must_exist_in_graph_registry():
    packet = base_packet()
    packet["acceptance_contract"]["material_dimensions"] = ["FAKE_GLOBAL_QUALITY"]
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == "HANDOFF_MATERIAL_DIMENSION_UNKNOWN"


def test_high_impact_change_cannot_bypass_existing_human_gate():
    packet = base_packet()
    packet["next_handoff"]["high_impact_change_classes"] = ["WORLD_TOPOLOGY"]
    packet["next_handoff"]["approval_required"] = False
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate(packet)
    assert exc.value.code == "HIGH_IMPACT_GATE_BYPASS"

    packet["next_handoff"]["approval_required"] = True
    packet["next_handoff"]["approval_gate_ref"] = "Project Instructions / human gate"
    assert validate(packet)


def test_handoff_transition_preserves_owner_task_work_item_and_hard_invariants():
    upstream = base_packet()
    downstream = downstream_packet(include_unknown=False)
    assert validate_handoff_transition(
        upstream,
        downstream,
        project_root=ROOT,
        expected_work_item_id=WORK_ITEM,
    )


def test_handoff_transition_cannot_drop_live_hard_invariant():
    upstream = base_packet()
    downstream = downstream_packet(include_hard=False, include_unknown=False)
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_handoff_transition(
            upstream,
            downstream,
            project_root=ROOT,
            expected_work_item_id=WORK_ITEM,
        )
    assert exc.value.code == "HANDOFF_TRANSITION_HARD_INVARIANT_DROPPED"


def test_handoff_transition_cannot_drop_material_unknown():
    upstream = base_packet()
    upstream["unresolved_unknowns"] = [material_unknown()]
    downstream = downstream_packet(include_unknown=False)
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_handoff_transition(
            upstream,
            downstream,
            project_root=ROOT,
            expected_work_item_id=WORK_ITEM,
        )
    assert exc.value.code == "HANDOFF_TRANSITION_MATERIAL_UNKNOWN_DROPPED"


def test_handoff_transition_must_reach_declared_next_owner_and_task():
    upstream = base_packet()
    downstream = downstream_packet(include_unknown=False)
    downstream["participant"]["owner_role"] = "MODEL_ADAPTER"
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_handoff_transition(
            upstream,
            downstream,
            project_root=ROOT,
            expected_work_item_id=WORK_ITEM,
        )
    assert exc.value.code == "HANDOFF_TRANSITION_OWNER_MISMATCH"
