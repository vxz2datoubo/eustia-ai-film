from pathlib import Path

import pytest

from production_intelligence.runtime import (
    CapabilityAtlas,
    ProductionIntelligenceError,
    validate_handoff_packet,
    validate_project,
)

ROOT = Path(__file__).resolve().parents[3]


def atlas():
    return CapabilityAtlas.from_project_root(ROOT)


def base_packet():
    return {
        "packet_id": "PHP-TEST-001",
        "task": {"task_id": "T1", "task_class": "COMPILE_MODEL_EXECUTION", "state": "READY"},
        "context": {
            "project_id": "EUSTIA_AI_FILM",
            "work_item_id_when_required": "KAIM-SCARF-CLOTHESLINE-CURRENT",
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


def test_project_schema_bundle_validates():
    receipt = validate_project(ROOT)
    assert receipt["status"] == "PASS"
    assert receipt["epistemic_zone_count"] == 4
    assert receipt["regression_case_count"] >= 20
    assert receipt["capability_count"] >= 15


def test_sparse_resolution_does_not_recursively_expand_every_department():
    result = atlas().resolve(["support_contact_topology_failure"])
    assert "CAP-BLOCKING-SPATIAL" not in result.selected_capabilities or result.sparse_expansion
    assert "CAP-SOUND" not in result.selected_capabilities
    assert result.sparse_expansion is True


def test_material_expansion_is_explicit_and_validated():
    result = atlas().resolve(
        ["support_contact_topology_failure"],
        material_capabilities=["CAP-BLOCKING-SPATIAL", "CAP-PHYSICS-CONTACT", "CAP-REVERSE-EVAL"],
    )
    assert "CAP-PHYSICS-CONTACT" in result.selected_capabilities
    assert "CAP-SOUND" not in result.selected_capabilities


def test_unknown_material_capability_fails_closed():
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(["x"], material_capabilities=["CAP-NOT-REAL"])
    assert exc.value.code == "PICG_CAPABILITY_UNKNOWN"


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
    assert validate_handoff_packet(
        base_packet(), expected_work_item_id="KAIM-SCARF-CLOTHESLINE-CURRENT"
    )


def test_handoff_work_item_mismatch_fails():
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_handoff_packet(base_packet(), expected_work_item_id="KAIM-HIGH-SEARCH-OLD")
    assert exc.value.code == "WORK_ITEM_IDENTITY_MISMATCH"


def test_k2_inference_requires_provenance_and_cannot_self_confirm():
    packet = base_packet()
    packet["authority_receipt"]["inferred_user_constraints"] = [
        {"statement": "prefers motivated light", "confidence": "HIGH", "evidence": ["review-1"], "explicit_user_confirmed": True}
    ]
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_handoff_packet(packet)
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
    assert validate_handoff_packet(packet)


def test_k4_high_material_unknown_requires_next_information_action():
    packet = base_packet()
    packet["unresolved_unknowns"] = [
        {
            "question": "exact current model negative-prompt semantics",
            "epistemic_zone": "K4_FRONTIER_OR_OPAQUE",
            "materiality": "HIGH",
        }
    ]
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_handoff_packet(packet)
    assert exc.value.code == "K4_MATERIAL_UNKNOWN_MISSING_NEXT_ACTION"


def test_strong_reference_responsibility_conflict_fails():
    packet = base_packet()
    packet["inputs"]["reference_responsibilities"]["camera"] = {
        "owners": ["WHITE_MODEL", "REFERENCE_VIDEO"],
        "both_declared_strong": True,
        "compatibility_proven": False,
    }
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_handoff_packet(packet)
    assert exc.value.code == "STRONG_REFERENCE_RESPONSIBILITY_CONFLICT"


def test_global_score_cannot_hide_material_failure():
    packet = base_packet()
    packet["acceptance_contract"]["pass_logic"] = {
        "global_score_overrides_material_failure": True
    }
    with pytest.raises(ProductionIntelligenceError) as exc:
        validate_handoff_packet(packet)
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
        validate_handoff_packet(packet)
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
        validate_handoff_packet(packet)
    assert exc.value.code == "PROXY_FINAL_CONFUSION"
