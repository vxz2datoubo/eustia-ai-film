from pathlib import Path
import unittest

from learning_retriever.cinematic_intent import (
    CinematicIntentContractError,
    compile_cinematic_intent_contract,
    validate_cinematic_intent_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _compile(raw):
    return compile_cinematic_intent_contract(raw, project_root=REPO_ROOT)


class CinematicIntentContractHardeningTests(unittest.TestCase):
    def test_explicit_false_substrate_is_not_treated_as_declared_capture_style(self):
        raw = {
            "contract_id": "CIC-SUBSTRATE-FALSE-001",
            "intent": {"capture_intent": {"substrate_optional": False}},
            "provenance": {"capture_intent": {"source": "director_capture_plan"}},
            "context": {"material_fields": ["capture_intent"]},
        }
        result = _compile(raw)
        codes = {item["code"] for item in result["diagnostics"]}
        self.assertEqual(result["status"], "PASS")
        self.assertNotIn("CAPTURE_SUBSTRATE_UNMOTIVATED", codes)
        self.assertIn("capture_intent", result["execution_overlay"])

    def test_camera_position_fails_closed_without_canonical_readback(self):
        raw = {
            "contract_id": "CIC-CAMERA-POSITION-GATE-001",
            "intent": {"capture_intent": {"camera_physical_position": "exterior_side"}},
            "provenance": {"capture_intent": {"source": "downstream_adapter_draft"}},
            "context": {"material_fields": ["capture_intent"]},
        }
        with self.assertRaises(CinematicIntentContractError) as ctx:
            _compile(raw)
        self.assertEqual(ctx.exception.code, "MISSING_CANONICAL_UPSTREAM_BINDING")

    def test_lens_intent_fails_closed_without_canonical_readback(self):
        raw = {
            "contract_id": "CIC-LENS-GATE-001",
            "intent": {"capture_intent": {"lens_intent": "35mm_environmental_context"}},
            "provenance": {"capture_intent": {"source": "downstream_adapter_draft"}},
            "context": {"material_fields": ["capture_intent"]},
        }
        with self.assertRaises(CinematicIntentContractError) as ctx:
            _compile(raw)
        self.assertEqual(ctx.exception.code, "MISSING_CANONICAL_UPSTREAM_BINDING")

    def test_empty_material_provenance_fails_closed(self):
        raw = {
            "contract_id": "CIC-EMPTY-PROVENANCE-001",
            "intent": {
                "composition": {
                    "primary_mechanism": "lateral_pressure",
                    "camera_reason": "preserve pursuit direction",
                }
            },
            "provenance": {"composition": {}},
            "context": {"material_fields": ["composition"]},
        }
        with self.assertRaises(CinematicIntentContractError) as ctx:
            validate_cinematic_intent_contract(raw, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "MISSING_PROVENANCE")

    def test_context_gate_flags_require_real_booleans(self):
        raw = {
            "contract_id": "CIC-CONTEXT-BOOL-001",
            "intent": {},
            "provenance": {},
            "context": {
                "material_fields": [],
                "reference_decoupling_applied": "false",
            },
        }
        with self.assertRaises(CinematicIntentContractError) as ctx:
            validate_cinematic_intent_contract(raw, project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "INVALID_CONTRACT_SHAPE")


if __name__ == "__main__":
    unittest.main()
