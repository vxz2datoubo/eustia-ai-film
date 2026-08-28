from pathlib import Path
import unittest

import yaml

from learning_retriever.cinematic_intent import (
    CinematicIntentContractError,
    STRUCTURAL_GATE_CODES,
    compile_cinematic_intent_contract,
    validate_cinematic_intent_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SUITE = yaml.safe_load(
    (REPO_ROOT / "11_验收/cinematic_intent_contract_regression_cases.yaml").read_text(encoding="utf-8")
)
SCHEMA = yaml.safe_load(
    (REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8")
)


class CinematicIntentContractTests(unittest.TestCase):
    def test_compile_cases_are_executable(self):
        for case in SUITE["compile_cases"]:
            with self.subTest(case=case["id"]):
                result = compile_cinematic_intent_contract(case["contract"], project_root=REPO_ROOT)
                self.assertEqual(result["status"], case["expected_status"])
                diagnostic_codes = {item["code"] for item in result["diagnostics"]}
                for code in case.get("expected_diagnostics", []):
                    self.assertIn(code, diagnostic_codes)
                for code in case.get("expected_diagnostics_absent", []):
                    self.assertNotIn(code, diagnostic_codes)
                for field in case.get("expected_overlay_fields", []):
                    self.assertIn(field, result["execution_overlay"])
                    self.assertIn(field, result["overlay_provenance"])
                for field in case.get("expected_absent_overlay_fields", []):
                    self.assertNotIn(field, result["execution_overlay"])
                if case.get("expected_overlay_fields") == []:
                    self.assertEqual(result["execution_overlay"], {})

    def test_structural_gate_cases_fail_closed(self):
        for case in SUITE["structural_gate_cases"]:
            with self.subTest(case=case["id"]):
                with self.assertRaises(CinematicIntentContractError) as ctx:
                    validate_cinematic_intent_contract(case["contract"], project_root=REPO_ROOT)
                self.assertEqual(ctx.exception.code, case["expected_error_code"])
                self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)

    def test_runtime_diagnostics_are_declared_by_canonical_schema(self):
        declared = set()
        for severity in ("ERROR", "WARNING", "INFO"):
            declared.update(SCHEMA["static_checks"][severity])
        emitted = set()
        for case in SUITE["compile_cases"]:
            result = compile_cinematic_intent_contract(case["contract"], project_root=REPO_ROOT)
            emitted.update(item["code"] for item in result["diagnostics"])
        self.assertTrue(emitted)
        self.assertTrue(emitted <= declared)
        self.assertTrue(SUITE["gates"]["schema_static_check_vocabulary_is_reused"])

    def test_fail_result_suppresses_execution_overlay(self):
        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-LOCKED-CAMERA-ERROR-001")
        result = compile_cinematic_intent_contract(case["contract"], project_root=REPO_ROOT)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["execution_overlay"], {})
        self.assertEqual(result["overlay_provenance"], {})
        self.assertEqual(result["reverse_eval_expectations"], [])

    def test_reverse_expectations_do_not_invent_new_values(self):
        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")
        result = compile_cinematic_intent_contract(case["contract"], project_root=REPO_ROOT)
        intent = case["contract"]["intent"]
        provenance = case["contract"]["provenance"]
        for expectation in result["reverse_eval_expectations"]:
            field = expectation["field"]
            self.assertEqual(expectation["declared_value"], intent[field])
            self.assertEqual(expectation["provenance"], provenance[field])
        self.assertTrue(SUITE["gates"]["reverse_expectations_preserve_declared_value_and_provenance_only"])

    def test_non_material_fields_never_enter_overlay(self):
        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")
        result = compile_cinematic_intent_contract(case["contract"], project_root=REPO_ROOT)
        self.assertEqual(set(result["execution_overlay"]), {"composition", "color_intent"})
        self.assertNotIn("unresolved_state", result["execution_overlay"])
        self.assertTrue(SUITE["gates"]["overlay_omits_non_material_fields"])

    def test_authority_and_maturity_boundaries_remain_explicit(self):
        valid = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")
        result = compile_cinematic_intent_contract(valid["contract"], project_root=REPO_ROOT)
        self.assertFalse(result["authority_mutation_allowed"])
        self.assertEqual(
            result["schema_authority"],
            "10_运行时/screen_observable_audible_ir_schema.yaml#CinematicIntentIR",
        )
        self.assertEqual(
            result["method_authority"],
            "01_AI电影系统/AI电影系统.md#CINEMATIC-VISUAL-GRAMMAR-001",
        )
        self.assertEqual(SUITE["status"], "candidate")
        self.assertTrue(SUITE["policy"]["learning_maturity_unchanged"])

    def test_reference_risk_stays_model_version_bounded_in_contract_context(self):
        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-REFERENCE-LEAK-WARN-001")
        context = case["contract"]["context"]
        self.assertEqual(context["model"], "C-DANCE")
        self.assertEqual(context["model_version"], "2.5")
        result = compile_cinematic_intent_contract(case["contract"], project_root=REPO_ROOT)
        self.assertIn("REFERENCE_APPEARANCE_LEAK_RISK", {item["code"] for item in result["diagnostics"]})
        self.assertTrue(SUITE["gates"]["no_model_specific_behavior_universalized"])


if __name__ == "__main__":
    unittest.main()
