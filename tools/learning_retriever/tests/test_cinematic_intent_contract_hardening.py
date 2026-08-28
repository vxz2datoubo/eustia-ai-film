from pathlib import Path
import hashlib
import json
import unittest

from learning_retriever.cinematic_intent import (
    CinematicIntentContractError,
    compile_cinematic_intent_contract,
    validate_cinematic_intent_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _binding(source_ref, camera):
    payload = {"source_authority_ref": source_ref, "camera": camera}
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return {
        "source_authority_ref": source_ref,
        "source_material_digest": digest,
        "camera": camera,
    }, digest


def _compile(raw, *, camera=None, source_ref="test_fixture://shot_plan/no_camera_lock"):
    envelope, digest = _binding(source_ref, camera or {})
    return compile_cinematic_intent_contract(
        raw,
        project_root=REPO_ROOT,
        upstream_lock_envelope=envelope,
        trusted_upstream_source_digest=digest,
    )


class CinematicIntentContractHardeningTests(unittest.TestCase):
    def test_explicit_false_substrate_is_not_treated_as_declared_capture_style(self):
        raw = {
            "contract_id": "CIC-SUBSTRATE-FALSE-001",
            "intent": {
                "capture_intent": {
                    "substrate_optional": False,
                    "camera_physical_position": "exterior_side",
                }
            },
            "provenance": {
                "capture_intent": {"source": "director_camera_plan"},
            },
            "context": {"material_fields": ["capture_intent"]},
        }
        result = _compile(raw)
        codes = {item["code"] for item in result["diagnostics"]}
        self.assertEqual(result["status"], "PASS")
        self.assertNotIn("CAPTURE_SUBSTRATE_UNMOTIVATED", codes)
        self.assertIn("capture_intent", result["execution_overlay"])

    def test_locked_lens_intent_conflict_fails_closed(self):
        raw = {
            "contract_id": "CIC-LOCKED-LENS-ERROR-001",
            "intent": {
                "capture_intent": {
                    "lens_intent": "35mm_environmental_context",
                }
            },
            "provenance": {
                "capture_intent": {"source": "downstream_adapter_draft"},
            },
            "context": {"material_fields": ["capture_intent"]},
        }
        result = _compile(
            raw,
            camera={"lens_intent": "85mm_compressed_distance"},
            source_ref="test_fixture://shot_plan/locked_lens_camera",
        )
        codes = {item["code"] for item in result["diagnostics"]}
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("CAMERA_SCOPE_CONFLICT", codes)
        self.assertEqual(result["execution_overlay"], {})
        self.assertEqual(result["reverse_eval_expectations"], [])

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
