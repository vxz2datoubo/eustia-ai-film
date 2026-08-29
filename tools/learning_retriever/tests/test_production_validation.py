from __future__ import annotations

from pathlib import Path
import unittest

import yaml

from learning_retriever import DirectorLearningRuntime
from learning_retriever.production_validation import run_production_validation_matrix


REPO_ROOT = Path(__file__).resolve().parents[3]
MATRIX_PATH = REPO_ROOT / "11_验收/learning_smart_recall_production_validation_matrix.yaml"
TRANSFER_PATH = REPO_ROOT / "11_验收/learning_smart_recall_transfer_contract.yaml"
MATRIX = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
TRANSFER = yaml.safe_load(TRANSFER_PATH.read_text(encoding="utf-8"))


class LearningSmartRecallProductionValidationTests(unittest.TestCase):
    def test_matrix_covers_all_required_mechanism_families(self) -> None:
        required = set(MATRIX["required_families"])
        observed = {case["family"] for case in MATRIX["cases"]}
        self.assertEqual(observed, required)
        for family in required:
            family_cases = [case for case in MATRIX["cases"] if case["family"] == family]
            self.assertTrue(any(case["kind"] == "positive" for case in family_cases), family)
            self.assertTrue(any(case["kind"] in {"negative", "fail_closed"} for case in family_cases), family)

    def test_cross_surface_requirements_are_not_exact_phrase_only(self) -> None:
        policy = TRANSFER["variation_policy"]
        allowed_non_wording = set(policy["allowed_non_wording_axes"])
        min_non_wording = int(policy["min_non_wording_axes_per_family"])
        for family in MATRIX["required_families"]:
            positives = [
                case
                for case in MATRIX["cases"]
                if case["family"] == family and case["kind"] == "positive"
            ]
            self.assertGreaterEqual(len(positives), 2, family)
            descriptions = {case["description"] for case in positives}
            self.assertEqual(len(descriptions), len(positives), family)
            contexts = {case.get("production_context") for case in positives}
            self.assertIn("cross_scene", contexts, family)

            axes_map = TRANSFER["families"][family]["positive_case_axes"]
            positive_ids = {case["id"] for case in positives}
            self.assertEqual(set(axes_map), positive_ids, family)
            non_wording_axes: set[str] = set()
            for case_id, axes in axes_map.items():
                axes_set = set(axes)
                self.assertIn("wording", axes_set, case_id)
                self.assertTrue((axes_set - {"wording"}).issubset(allowed_non_wording), case_id)
                non_wording_axes.update((axes_set - {"wording"}) & allowed_non_wording)
            self.assertGreaterEqual(len(non_wording_axes), min_non_wording, family)

    def test_each_family_has_executable_metamorphic_paraphrase_probe(self) -> None:
        required = set(MATRIX["required_families"])
        meta = TRANSFER["metamorphic_cases"]
        observed = {case["family"] for case in meta if case["kind"] == "positive"}
        self.assertEqual(observed, required)
        base_positives = {
            case["id"]: case
            for case in MATRIX["cases"]
            if case["kind"] == "positive"
        }
        self.assertTrue(all(case["metamorphic_of"] in base_positives for case in meta))
        if TRANSFER["variation_policy"].get("metamorphic_description_must_differ_from_parent"):
            for case in meta:
                parent = base_positives[case["metamorphic_of"]]
                self.assertNotEqual(case["description"].strip(), parent["description"].strip(), case["id"])

    def test_matrix_executes_through_canonical_runtime(self) -> None:
        report = run_production_validation_matrix(REPO_ROOT)
        self.assertEqual(report["aggregate"]["verdict"], "PASS", report["aggregate"])
        self.assertEqual(report["aggregate"]["false_positive_routes"], [])
        self.assertEqual(report["aggregate"]["false_negative_mandatory_recalls"], [])
        self.assertEqual(report["aggregate"]["authority_boundary_violations"], [])
        self.assertEqual(report["aggregate"]["missing_required_families"], [])
        self.assertEqual(report["aggregate"]["matrix_contract_violations"], [])
        self.assertEqual(report["aggregate"]["metamorphic_cases"], 6)
        self.assertEqual(report["aggregate"]["metamorphic_passes"], 6)

    def test_first_episode_inputs_are_part_of_the_executable_matrix(self) -> None:
        report = run_production_validation_matrix(REPO_ROOT)
        ep1 = [case for case in report["cases"] if case.get("production_context") == "first_episode"]
        self.assertGreaterEqual(len(ep1), 5)
        self.assertTrue(all(case["verdict"] == "PASS" for case in ep1), ep1)
        self.assertTrue(any("圣女伊莲降临钟楼平台" in case["input"] for case in ep1))
        self.assertTrue(any("爱丽丝用画外音解释羽化病" in case["input"] for case in ep1))
        self.assertTrue(any("凯姆沿建筑外立面攀爬" in case["input"] for case in ep1))
        self.assertTrue(any("诺瓦斯历史闪回" in case["input"] for case in ep1))

    def test_seedance_specific_contact_lesson_does_not_leak_to_h3(self) -> None:
        report = run_production_validation_matrix(REPO_ROOT)
        case = next(item for item in report["cases"] if item["case_id"] == "PVM-CONTACT-MODEL-NEG-003")
        self.assertEqual(case["verdict"], "PASS")
        self.assertNotIn("CD25-KAIM-WINDOW-AB-20260815", case["selected_cases"])
        excluded = {
            item["case_id"]: item["reason"]
            for item in case["excluded_cases"]
            if isinstance(item, dict)
        }
        self.assertEqual(excluded.get("CD25-KAIM-WINDOW-AB-20260815"), "model_version_mismatch")

    def test_runtime_receipt_exposes_compiled_features_without_changing_authority(self) -> None:
        result = DirectorLearningRuntime(REPO_ROOT).retrieve(
            "灾民面对救济教会的反应显得不合理",
            task_id="PVM-RUNTIME-RECEIPT",
        )
        receipt = result["canonical_runtime_receipt"]
        self.assertTrue(receipt["compiler_invoked"])
        self.assertEqual(receipt["flow"], ["director_feature_compiler", "hard_route", "semantic_recall"])
        self.assertEqual(receipt["route_authority"], "10_运行时/director_route_index.yaml")
        self.assertEqual(
            receipt["feature_compiler_receipt"]["authority_boundary"],
            "retrieval_query_only",
        )
        self.assertIn("crowd_reaction", receipt["compiled_features"]["dramatic_function"])
        self.assertIn("motive_tone_mismatch", receipt["compiled_features"]["failure_mechanism"])


if __name__ == "__main__":
    unittest.main()
