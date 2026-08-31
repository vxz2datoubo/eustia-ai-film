from pathlib import Path

from production_intelligence.runtime import CapabilityAtlas

ROOT = Path(__file__).resolve().parents[3]


def atlas():
    return CapabilityAtlas.from_project_root(ROOT)


def test_scarf_topology_signal_routes_material_geometry_stack_without_sound_or_color():
    result = atlas().resolve([
        "support_contact_topology_failure",
        "horizontal_trajectory_drift",
        "reference_appearance_contamination",
    ])
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


def test_exposition_signal_routes_story_editorial_and_sound_without_geometry():
    result = atlas().resolve(["exposition_stall"])
    selected = set(result.selected_capabilities)
    assert {
        "CAP-STORY-DIRECTOR-INTENT",
        "CAP-EDITORIAL-ATTENTION",
        "CAP-SOUND",
    }.issubset(selected)
    assert "CAP-PREVIS-GEOMETRY" not in selected
    assert "CAP-PHYSICS-CONTACT" not in selected


def test_tacit_preference_signal_routes_elicitation_and_learning_not_director_fact():
    result = atlas().resolve(["pairwise_preference_event"])
    selected = set(result.selected_capabilities)
    assert "CAP-TACIT-ELICITATION" in selected
    assert "CAP-LEARNING" in selected
    assert "CAP-STORY-DIRECTOR-INTENT" not in selected


def test_infrastructure_failure_is_separate_from_model_failure():
    result = atlas().resolve(["github_dns_failure"])
    selected = set(result.selected_capabilities)
    assert selected == {"CAP-INFRASTRUCTURE-TRANSPORT"}
    assert "CAP-MODEL-REFERENCE" not in selected
    assert "CAP-REVERSE-EVAL" not in selected


def test_rework_signal_routes_cycle_management_not_every_creative_department():
    result = atlas().resolve(["repeated_rework"])
    selected = set(result.selected_capabilities)
    assert selected == {"CAP-PRODUCTION-CYCLE"}
    assert "CAP-CAMERA-FRAMING" not in selected
    assert "CAP-SOUND" not in selected


def test_unknown_signal_remains_visible_in_receipt_instead_of_fuzzy_guess():
    result = atlas().resolve(["future_unknown_signal_not_in_graph"])
    assert result.selected_capabilities == ()
    assert result.unmatched_signatures == ("future_unknown_signal_not_in_graph",)
