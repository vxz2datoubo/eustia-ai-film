from __future__ import annotations

from pathlib import Path
import unittest

from learning_retriever.director_orchestrator import (
    DirectorRuntimeError,
    DirectorRuntimeOrchestrator,
    _validate_blocking,
    _validate_transition,
    _validate_world_state,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def entity(kind: str, position: str, state: str) -> dict:
    return {"kind": kind, "position": position, "state": state}


class DirectorOrchestratorHardeningTests(unittest.TestCase):
    def assert_code(self, expected: str, fn) -> None:
        with self.assertRaises(DirectorRuntimeError) as ctx:
            fn()
        self.assertEqual(expected, ctx.exception.code)

    def test_orchestrator_has_no_constructed_replaceable_learning_runtime_or_root(self):
        runtime = DirectorRuntimeOrchestrator()
        self.assertFalse(hasattr(runtime, "learning_runtime"))
        self.assertFalse(hasattr(runtime, "_project_root"))

    def test_python_constructor_has_no_caller_project_root_port(self):
        with self.assertRaises(TypeError):
            DirectorRuntimeOrchestrator(PROJECT_ROOT)  # type: ignore[call-arg]

    def test_world_invariant_cannot_disappear_by_omission(self):
        packet = {
            "world_state": {
                "entry": {
                    "entities": {"kaim": entity("character", "roof", "moving")},
                    "invariants": ["no_open_sky"],
                },
                "exit": {
                    "entities": {"kaim": entity("character", "roof_left", "moving")},
                    "invariants": [],
                },
                "explicit_exits_or_removals": [],
                "state_changes": ["kaim moves left"],
            }
        }
        self.assert_code(
            "DIRECTOR_WORLD_INVARIANT_DROPPED",
            lambda: _validate_world_state(packet),
        )

    def test_world_state_cannot_implicitly_create_new_entity_in_p0(self):
        packet = {
            "world_state": {
                "entry": {
                    "entities": {"kaim": entity("character", "roof", "moving")},
                    "invariants": ["closed_world"],
                },
                "exit": {
                    "entities": {
                        "kaim": entity("character", "roof_left", "moving"),
                        "ghost": entity("character", "roof_left", "appeared"),
                    },
                    "invariants": ["closed_world"],
                },
                "explicit_exits_or_removals": [],
                "state_changes": ["kaim moves left"],
            }
        }
        self.assert_code(
            "DIRECTOR_WORLD_ENTITY_INVALID",
            lambda: _validate_world_state(packet),
        )

    def test_caller_entry_must_exactly_match_trusted_world_baseline(self):
        trusted = {
            "entities": {
                "kaim": entity("character", "roof", "moving"),
                "scarf": entity("object", "line", "held"),
            },
            "invariants": ["closed_world"],
        }
        packet = {
            "world_state": {
                "entry": {
                    "entities": {
                        "kaim": entity("character", "roof", "moving"),
                        "ghost": entity("character", "roof", "invented"),
                    },
                    "invariants": ["closed_world"],
                },
                "exit": {
                    "entities": {
                        "kaim": entity("character", "roof", "moving"),
                        "ghost": entity("character", "roof", "invented"),
                    },
                    "invariants": ["closed_world"],
                },
                "explicit_exits_or_removals": [],
                "state_changes": [],
            }
        }
        self.assert_code(
            "DIRECTOR_WORLD_ENTRY_BASELINE_MISMATCH",
            lambda: _validate_world_state(packet, canonical_entry_baseline=trusted),
        )

    def test_omitting_real_entity_from_both_entry_and_exit_fails_baseline_match(self):
        trusted = {
            "entities": {
                "kaim": entity("character", "roof", "moving"),
                "scarf": entity("object", "line", "held"),
            },
            "invariants": ["closed_world"],
        }
        packet = {
            "world_state": {
                "entry": {
                    "entities": {"kaim": entity("character", "roof", "moving")},
                    "invariants": ["closed_world"],
                },
                "exit": {
                    "entities": {"kaim": entity("character", "roof", "moving")},
                    "invariants": ["closed_world"],
                },
                "explicit_exits_or_removals": [],
                "state_changes": [],
            }
        }
        self.assert_code(
            "DIRECTOR_WORLD_ENTRY_BASELINE_MISMATCH",
            lambda: _validate_world_state(packet, canonical_entry_baseline=trusted),
        )

    def test_blocking_support_contact_value_must_bind_world_entity(self):
        entry = {
            "kaim": entity("character", "roof", "moving"),
            "wall": entity("environment_anchor", "roof_left", "fixed"),
        }
        packet = {
            "blocking": {
                "initial_positions": {"kaim": "roof"},
                "movement_paths": {"kaim": "roof_to_left"},
                "final_positions": {"kaim": "roof_left"},
                "support_contacts": {"kaim": ["ghost_wall"]},
            }
        }
        self.assert_code(
            "DIRECTOR_BLOCKING_ENTITY_UNBOUND",
            lambda: _validate_blocking(packet, entry_entities=entry, exit_entities=entry),
        )

    def test_transition_entity_classes_must_be_disjoint(self):
        packet = {
            "transition": {
                "inherited_entities": ["kaim"],
                "changed_entities": ["kaim"],
                "explicit_exits_or_removals": [],
                "next_entry_state": {"entities": ["kaim"]},
            }
        }
        self.assert_code(
            "DIRECTOR_TRANSITION_STATE_MISMATCH",
            lambda: _validate_transition(
                packet,
                entry_ids={"kaim"},
                exit_ids={"kaim"},
                explicit_exits=set(),
            ),
        )

    def test_transition_must_classify_every_entry_entity_exactly_once(self):
        packet = {
            "transition": {
                "inherited_entities": ["kaim"],
                "changed_entities": [],
                "explicit_exits_or_removals": [],
                "next_entry_state": {"entities": ["kaim", "scarf"]},
            }
        }
        self.assert_code(
            "DIRECTOR_TRANSITION_STATE_MISMATCH",
            lambda: _validate_transition(
                packet,
                entry_ids={"kaim", "scarf"},
                exit_ids={"kaim", "scarf"},
                explicit_exits=set(),
            ),
        )


if __name__ == "__main__":
    unittest.main()
