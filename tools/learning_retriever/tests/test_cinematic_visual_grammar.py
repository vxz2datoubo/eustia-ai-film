from pathlib import Path
import unittest

import yaml

from learning_retriever import DirectorLearningRuntime
from learning_retriever.feature_compiler import compile_director_features, validate_semantic_dependencies


REPO_ROOT = Path(__file__).resolve().parents[3]
ROUTES = yaml.safe_load((REPO_ROOT / "10_运行时/director_route_index.yaml").read_text(encoding="utf-8"))


class CinematicVisualGrammarCompilerTests(unittest.TestCase):
    def _runtime(self, description: str, task_id: str):
        result = DirectorLearningRuntime(REPO_ROOT).retrieve(description, task_id=task_id, top_k=5)
        self.assertEqual(result["status"], "PASS")
        self.assertIn("CINEMATIC_VISUAL_GRAMMAR", result["canonical_runtime_receipt"]["hard_routes"])
        self.assertIn("CINEMATIC_VISUAL_GRAMMAR", result["retrieval_receipt"]["hard_routes"])
        return result

    def test_cinematic_failure_language_compiles_to_existing_feature_families_and_route(self):
        cases = [
            (
                "composition-pressure",
                "这镜头构图漂亮但没意思，人物和空间没关系，机位没有理由。",
                "failure_mechanism",
                "composition_without_pressure",
                "relation_pressure_composition",
            ),
            (
                "attention-flow",
                "女人扯下衣服后切回来找不到凯姆原来的位置，注意力落点乱了。",
                "failure_mechanism",
                "attention_flow_break",
                "attentional_flow",
            ),
            (
                "color-filter",
                "这个调色像统一滤镜，颜色没有物理来源。",
                "failure_mechanism",
                "color_as_filter",
                "color_thesis",
            ),
            (
                "density-overload",
                "画面纹理太多，所有区域都又锐又亮又复杂，细节抢戏。",
                "failure_mechanism",
                "visual_density_overload",
                "visual_density_budget",
            ),
            (
                "reference-contamination",
                "动作参考图太脏，把错误纹理和光线带进成片，参考图影响画质。",
                "failure_mechanism",
                "reference_appearance_contamination",
                "reference_signal_decoupling",
            ),
            (
                "template-repetition",
                "这几个镜头都一样，总是同一种构图和重复机位。",
                "failure_mechanism",
                "template_composition_repetition",
                "anti_template_composition",
            ),
            (
                "capture-unmotivated",
                "只是为了高级感乱加胶片和35mm，没有成像理由。",
                "failure_mechanism",
                "unmotivated_capture_style",
                "motivated_capture_substrate",
            ),
            (
                "generic-style-stack",
                "只会堆电影感质量词，结果像广告和CG。",
                "failure_mechanism",
                "generic_cinematic_style_stacking",
                "cinematic_visual_design",
            ),
        ]
        for task_id, description, field, value, matched_rule in cases:
            with self.subTest(task_id=task_id):
                compiled = compile_director_features(description)
                self.assertIn(value, getattr(compiled, field))
                self.assertIn(matched_rule, compiled.matched_rules)
                self._runtime(description, f"REG-CVG-{task_id}")

    def test_positive_visual_intent_routes_without_inventing_failure(self):
        cases = [
            (
                "capture-motivated",
                "角色记忆段使用35mm胶片作为成像介质，保持真实光学限制。",
                "capture_substrate",
                "unmotivated_capture_style",
            ),
            (
                "reference-role",
                "参考图只负责人物身份，白模负责动作和空间关系。",
                "reference_responsibility_split",
                "reference_appearance_contamination",
            ),
            (
                "cinematic-goal",
                "希望这个场景有电影感，但先从人物关系和空间设计出发。",
                "motivated_composition",
                "generic_cinematic_style_stacking",
            ),
        ]
        for task_id, description, expected_spatial, forbidden_failure in cases:
            with self.subTest(task_id=task_id):
                compiled = compile_director_features(description)
                self.assertIn(expected_spatial, compiled.spatial_action_features)
                self.assertNotIn(forbidden_failure, compiled.failure_mechanism)
                self._runtime(description, f"REG-CVG-{task_id}")

    def test_visual_grammar_keeps_four_feature_authority_keys(self):
        route = next(route for route in ROUTES["routes"] if route["id"] == "CINEMATIC_VISUAL_GRAMMAR")
        allowed = {"dramatic_function", "relation_type", "spatial_action_features", "failure_mechanism"}
        machine = route["machine_triggers"]["any_of"]
        self.assertEqual(set(machine), allowed)
        compiler = yaml.safe_load((REPO_ROOT / "10_运行时/director_feature_compiler.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            set(compiler["cinematic_visual_vocabulary"]["failure_mechanisms"]),
            {
                "generic_cinematic_style_stacking",
                "composition_without_pressure",
                "attention_flow_break",
                "color_as_filter",
                "visual_density_overload",
                "reference_appearance_contamination",
                "template_composition_repetition",
                "unmotivated_capture_style",
            },
        )
        self.assertEqual(
            set(compiler["output"]),
            allowed,
        )

    def test_cinematic_intent_ir_is_between_blocking_and_shot_plan(self):
        schema = yaml.safe_load((REPO_ROOT / "10_运行时/screen_observable_audible_ir_schema.yaml").read_text(encoding="utf-8"))
        chain = schema["compiler_chain"]
        blocking = chain.index("BlockingIR")
        cinematic = chain.index("CinematicIntentIR")
        shot = chain.index("ShotPlanIR")
        self.assertLess(blocking, cinematic)
        self.assertLess(cinematic, shot)
        layer = schema["ir_layers"]["CinematicIntentIR"]
        for field in (
            "unresolved_state",
            "viewer_position",
            "relation_pressure",
            "attention_flow",
            "composition",
            "color_intent",
            "capture_intent",
            "visual_density",
            "reference_signal_roles",
            "anti_template_signature",
            "attention_handoff",
        ):
            self.assertIn(field, layer["fields"])

    def test_compiler_semantic_dependencies_include_cinematic_intent(self):
        self.assertEqual(validate_semantic_dependencies(REPO_ROOT), [])

    def test_route_does_not_create_second_learning_authority(self):
        route = next(route for route in ROUTES["routes"] if route["id"] == "CINEMATIC_VISUAL_GRAMMAR")
        self.assertEqual(route["maturity"], "candidate")
        self.assertIn("10_运行时/screen_observable_audible_ir_schema.yaml#CinematicIntentIR", route["mandatory_reads"])
        self.assertIn("01_AI电影系统/AI电影系统.md#CINEMATIC-VISUAL-GRAMMAR-001", route["mandatory_reads"])
        self.assertFalse(any("导演反馈学习案例" in ref for ref in route["mandatory_reads"]))


if __name__ == "__main__":
    unittest.main()
