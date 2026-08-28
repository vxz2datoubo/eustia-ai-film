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
UPSTREAM_FIXTURE = SUITE["trusted_upstream_fixture"]


def _compile_case(case):
    return compile_cinematic_intent_contract(
        case["contract"],
        project_root=REPO_ROOT,
        upstream_lock_envelope=case.get("upstream_lock_envelope", UPSTREAM_FIXTURE["envelope"]),
        trusted_upstream_source_digest=case.get(
            "trusted_upstream_source_digest", UPSTREAM_FIXTURE["trusted_source_digest"]
        ),
    )


class CinematicIntentContractTests(unittest.TestCase):
    def test_compile_cases_are_executable(self):
        for case in SUITE["compile_cases"]:
            with self.subTest(case=case["id"]):
                result = _compile_case(case)
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

    def test_missing_separate_upstream_binding_fails_closed(self):
        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")
        with self.assertRaises(CinematicIntentContractError) as ctx:
            compile_cinematic_intent_contract(case["contract"], project_root=REPO_ROOT)
        self.assertEqual(ctx.exception.code, "MISSING_TRUSTED_UPSTREAM_BINDING")
        self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)

    def test_upstream_binding_and_unenforceable_lock_attacks_fail_closed(self):
        contract_by_id = {case["id"]: case["contract"] for case in SUITE["compile_cases"]}
        for case in SUITE["upstream_gate_cases"]:
            with self.subTest(case=case["id"]):
                if "upstream_lock_envelope" in case:
                    envelope = case["upstream_lock_envelope"]
                    trusted_digest = case["trusted_upstream_source_digest"]
                else:
                    envelope = {
                        "source_authority_ref": "test_fixture://shot_plan/unrepresentable_camera_lock",
                        "source_material_digest": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
                        "camera": case["camera_lock"],
                    }
                    trusted_digest = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
                with self.assertRaises(CinematicIntentContractError) as ctx:
                    compile_cinematic_intent_contract(
                        contract_by_id[case["contract_ref"]],
                        project_root=REPO_ROOT,
                        upstream_lock_envelope=envelope,
                        trusted_upstream_source_digest=trusted_digest,
                    )
                self.assertEqual(ctx.exception.code, case["expected_error_code"])
                self.assertIn(ctx.exception.code, STRUCTURAL_GATE_CODES)

    def test_matching_trusted_position_lock_is_preserved_in_receipt(self):
        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")
        result = _compile_case(case)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["upstream_lock_binding"]["camera"], {"position": "exterior_side"})
        self.assertFalse(result["upstream_lock_binding"]["proposal_can_mutate"])
        self.assertEqual(
            result["upstream_lock_binding"]["source_material_digest"],
            case["trusted_upstream_source_digest"],
        )

    def test_runtime_diagnostics_are_declared_by_canonical_schema(self):
        declared = set()
        for severity in ("ERROR", "WARNING", "INFO"):
            declared.update(SCHEMA["static_checks"][severity])
        emitted = set()
        for case in SUITE["compile_cases"]:
            result = _compile_case(case)
            emitted.update(item["code"] for item in result["diagnostics"])
        self.assertTrue(emitted)
        self.assertTrue(emitted <= declared)
        self.assertTrue(SUITE["gates"]["schema_static_check_vocabulary_is_reused"])

    def test_fail_result_suppresses_execution_overlay(self):
        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-LOCKED-CAMERA-ERROR-001")
        result = _compile_case(case)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["execution_overlay"], {})
        self.assertEqual(result["overlay_provenance"], {})
        self.assertEqual(result["reverse_eval_expectations"], [])

    def test_reverse_expectations_do_not_invent_new_values(self):
        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")
        result = _compile_case(case)
        intent = case["contract"]["intent"]
        provenance = case["contract"]["provenance"]
        for expectation in result["reverse_eval_expectations"]:
            field = expectation["field"]
            self.assertEqual(expectation["declared_value"], intent[field])
            self.assertEqual(expectation["provenance"], provenance[field])
        self.assertTrue(SUITE["gates"]["reverse_expectations_preserve_declared_value_and_provenance_only"])

    def test_non_material_fields_never_enter_overlay(self):
        case = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")
        result = _compile_case(case)
        self.assertEqual(set(result["execution_overlay"]), {"composition", "color_intent"})
        self.assertNotIn("unresolved_state", result["execution_overlay"])
        self.assertTrue(SUITE["gates"]["overlay_omits_non_material_fields"])

    def test_authority_and_maturity_boundaries_remain_explicit(self):
        valid = next(case for case in SUITE["compile_cases"] if case["id"] == "CIC-VALID-MINIMAL-001")
        result = _compile_case(valid)
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
        result = _compile_case(case)
        self.assertIn("REFERENCE_APPEARANCE_LEAK_RISK", {item["code"] for item in result["diagnostics"]})
        self.assertTrue(SUITE["gates"]["no_model_specific_behavior_universalized"])

    def test_project_index_registers_contract_regression_without_new_method_authority(self):
        project = yaml.safe_load((REPO_ROOT / "PROJECT_INDEX.yaml").read_text(encoding="utf-8"))
        expected = "11_验收/cinematic_intent_contract_regression_cases.yaml"
        self.assertEqual(project["canonical"]["cinematic_intent_contract_regression_cases"], expected)
        self.assertEqual(project["effective_sources"][expected], "github_verified")
        self.assertTrue(project["policy"]["cinematic_intent_contract_runtime_is_execution_only"])
        self.assertEqual(
            project["canonical"]["ai_film_system"],
            "01_AI电影系统/AI电影系统.md",
        )
        self.assertEqual(
            project["canonical"]["screen_observable_audible_ir_schema"],
            "10_运行时/screen_observable_audible_ir_schema.yaml",
        )

    def test_read_sets_bind_contract_regression_only_when_relevant(self):
        read_sets = yaml.safe_load((REPO_ROOT / "10_运行时/read_sets.yaml").read_text(encoding="utf-8"))["read_sets"]
        expected = "cinematic_intent_contract_regression_cases"
        self.assertIn("cinematic_intent_contract_regression", read_sets["directing"]["conditional"])
        self.assertIn(expected, read_sets["directing"]["conditional"]["cinematic_intent_contract_regression"])
        self.assertIn("cinematic_intent_contract_regression", read_sets["system_research"]["conditional"])
        self.assertIn(expected, read_sets["system_research"]["conditional"]["cinematic_intent_contract_regression"])
        self.assertNotIn("cinematic_intent_contract_regression", read_sets["directing"]["always"])

    def test_write_route_for_contract_regression_is_unique(self):
        routes = yaml.safe_load((REPO_ROOT / "10_运行时/write_routes.yaml").read_text(encoding="utf-8"))["routes"]
        expected = "11_验收/cinematic_intent_contract_regression_cases.yaml"
        self.assertEqual(routes["cinematic_intent_contract_regression_case"], expected)
        matches = [name for name, target in routes.items() if target == expected]
        self.assertEqual(matches, ["cinematic_intent_contract_regression_case"])

    def test_ci_triggers_and_executes_contract_regression(self):
        workflow = (REPO_ROOT / ".github/workflows/learning-feature-compiler.yml").read_text(encoding="utf-8")
        self.assertIn("11_验收/cinematic_intent_contract_regression_cases.yaml", workflow)
        self.assertIn("test_cinematic_intent_contract.py", workflow)
        self.assertNotIn("contents: write", workflow)


if __name__ == "__main__":
    unittest.main()
