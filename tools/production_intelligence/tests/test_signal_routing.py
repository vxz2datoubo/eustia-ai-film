from pathlib import Path

import pytest

from production_intelligence.runtime import CapabilityAtlas, ProductionIntelligenceError

ROOT = Path(__file__).resolve().parents[3]
WORK_ITEM = "KAIM-SCARF-CLOTHESLINE-CURRENT"


def atlas():
    return CapabilityAtlas.from_project_root(ROOT)


def signal(
    signatures,
    *,
    signal_id="SIG-TEST-001",
    signal_type="DIRECTOR_FEATURE_RECEIPT",
    source_stage="DIRECTOR_FEATURE_COMPILED",
    producer="Director_Feature_Compiler",
    materiality="MATERIAL",
    epistemic_zone="K1_EXPLICIT_USER",
    work_item=WORK_ITEM,
    authority_refs=None,
    payload_extra=None,
):
    payload = {"problem_signatures": list(signatures)}
    payload.update(payload_extra or {})
    return {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "source_stage": source_stage,
        "producer": producer,
        "work_item_id_when_required": work_item,
        "materiality": materiality,
        "epistemic_zone": epistemic_zone,
        "authority_refs": authority_refs or ["10_运行时/director_feature_compiler.yaml"],
        "payload": payload,
        "provenance_chain": [
            {
                "stage": source_stage,
                "producer": producer,
                "signal_or_packet_ref": signal_id,
                "action": "CREATED",
            }
        ],
    }


def test_scarf_topology_signal_routes_material_geometry_stack_without_sound_or_color():
    result = atlas().resolve(
        signal([
            "support_contact_topology_failure",
            "horizontal_trajectory_drift",
            "reference_appearance_contamination",
        ]),
        expected_work_item_id=WORK_ITEM,
    )
    selected = set(result.selected_capabilities)
    assert {
        "CAP-BLOCKING-SPATIAL",
        "CAP-PREVIS-GEOMETRY",
        "CAP-PHYSICS-CONTACT",
        "CAP-ASSET-REFERENCE-PROVENANCE",
        "CAP-MODEL-REFERENCE",
        "CAP-REVERSE-EVAL",
    }.issubset(selected)
    assert "CAP-SOUND" not in selected
    assert "CAP-LIGHT-COLOR" not in selected
    assert result.unmatched_signatures == ()
    assert result.admitted is True
    assert result.as_dict()["authority_boundary"] == "coordination_receipt_only"


def test_exposition_signal_routes_story_editorial_and_sound_without_geometry():
    result = atlas().resolve(signal(["exposition_stall"]))
    selected = set(result.selected_capabilities)
    assert {
        "CAP-STORY-DIRECTOR-INTENT",
        "CAP-EDITORIAL-ATTENTION",
        "CAP-SOUND",
    }.issubset(selected)
    assert "CAP-PREVIS-GEOMETRY" not in selected
    assert "CAP-PHYSICS-CONTACT" not in selected


def test_tacit_preference_signal_routes_elicitation_and_learning_not_director_fact():
    result = atlas().resolve(
        signal(
            ["pairwise_preference_event"],
            signal_type="LEARNING_EVIDENCE",
            source_stage="LEARNING_CAPTURED",
            producer="Learning_Capture",
            epistemic_zone="K2_TACIT_OR_IMPLICIT",
            authority_refs=["10_运行时/learning_application_gate.yaml"],
        )
    )
    selected = set(result.selected_capabilities)
    assert "CAP-TACIT-ELICITATION" in selected
    assert "CAP-LEARNING" in selected
    assert "CAP-STORY-DIRECTOR-INTENT" not in selected


def test_infrastructure_failure_is_separate_from_model_failure():
    result = atlas().resolve(
        signal(
            ["github_dns_failure"],
            signal_type="INFRASTRUCTURE_STATUS",
            source_stage="INFRASTRUCTURE",
            producer="Infrastructure_Tooling",
            epistemic_zone="K4_FRONTIER_OR_OPAQUE",
            work_item=None,
            authority_refs=["infrastructure_runtime_status"],
        )
    )
    selected = set(result.selected_capabilities)
    assert selected == {"CAP-INFRASTRUCTURE-TRANSPORT"}
    assert "CAP-MODEL-REFERENCE" not in selected
    assert "CAP-REVERSE-EVAL" not in selected


def test_rework_signal_routes_cycle_management_not_every_creative_department():
    result = atlas().resolve(signal(["repeated_rework"]))
    selected = set(result.selected_capabilities)
    assert selected == {"CAP-PRODUCTION-CYCLE"}
    assert "CAP-CAMERA-FRAMING" not in selected
    assert "CAP-SOUND" not in selected


def test_unknown_signal_remains_visible_in_receipt_instead_of_fuzzy_guess():
    result = atlas().resolve(signal(["future_unknown_signal_not_in_graph"]))
    assert result.selected_capabilities == ()
    assert result.unmatched_signatures == ("future_unknown_signal_not_in_graph",)


def test_raw_signature_list_cannot_bypass_signal_admission():
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(["support_contact_topology_failure"])
    assert exc.value.code == "SIGNAL_ENVELOPE_REQUIRED"


def test_caller_capability_ids_cannot_mint_selection():
    injected = signal(
        ["future_unknown_signal_not_in_graph"],
        payload_extra={"material_capabilities": ["CAP-LEARNING", "CAP-PROACTIVE-COLLABORATION"]},
    )
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(injected)
    assert exc.value.code == "CALLER_CAPABILITY_SELECTION_FORBIDDEN"


def test_signal_type_stage_mismatch_fails_closed():
    bad = signal(["exposition_stall"], source_stage="EVALUATED")
    bad["provenance_chain"][0]["stage"] = "EVALUATED"
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(bad)
    assert exc.value.code == "SIGNAL_TYPE_STAGE_MISMATCH"


def test_signal_type_producer_mismatch_fails_closed():
    bad = signal(["exposition_stall"], producer="Infrastructure_Tooling")
    bad["provenance_chain"][0]["producer"] = "Infrastructure_Tooling"
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(bad)
    assert exc.value.code == "SIGNAL_PRODUCER_TYPE_MISMATCH"


def test_required_work_item_cannot_be_omitted_or_rebound():
    omitted = signal(["exposition_stall"], work_item=None)
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(omitted)
    assert exc.value.code == "SIGNAL_WORK_ITEM_IDENTITY_REQUIRED"

    stale = signal(["exposition_stall"], work_item="STALE-WORK-ITEM")
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(stale, expected_work_item_id=WORK_ITEM)
    assert exc.value.code == "SIGNAL_WORK_ITEM_IDENTITY_MISMATCH"


def test_provenance_tail_cannot_misrepresent_signal_origin():
    bad = signal(["exposition_stall"])
    bad["provenance_chain"][0]["signal_or_packet_ref"] = "SIG-OTHER"
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(bad)
    assert exc.value.code == "SIGNAL_PROVENANCE_IDENTITY_MISMATCH"


def test_informational_signal_cannot_expand_departments():
    result = atlas().resolve(signal(["exposition_stall"], materiality="INFORMATIONAL"))
    assert result.selected_capabilities == ()
    assert result.unmatched_signatures == ("exposition_stall",)


def test_non_routable_generation_result_must_go_to_existing_observation_path():
    generation = signal(
        ["support_contact_topology_failure"],
        signal_type="GENERATION_RESULT",
        source_stage="GENERATED",
        producer="Generation_Service",
        epistemic_zone="K4_FRONTIER_OR_OPAQUE",
        authority_refs=["generation_receipt"],
    )
    with pytest.raises(ProductionIntelligenceError) as exc:
        atlas().resolve(generation)
    assert exc.value.code == "SIGNAL_NOT_CAPABILITY_ROUTABLE"
