from pathlib import Path
import unittest

from learning_retriever.entity_semantics import bounded_animate_agent_leader, load_canonical_character_terms


REPO_ROOT = Path(__file__).resolve().parents[3]
KNOWN = ("群众", "卫兵", "凯姆", "蒂娅", "圣女")
CANONICAL_CHARACTER_TERMS = load_canonical_character_terms(REPO_ROOT)


def modifier_tail(value: str) -> bool:
    residual = value.strip()
    if not residual:
        return True
    if residual.endswith("地"):
        stem = residual[:-1]
        return 2 <= len(stem) <= 8 and all("\u4e00" <= char <= "\u9fff" for char in stem)
    for token in ("缓缓", "慢慢", "迅速", "突然", "纷纷", "共同", "一起", "一同", "全都", "都"):
        if residual == token:
            return True
    return False


class EntitySemanticsTests(unittest.TestCase):
    def prove(self, leader: str, action: str = "面向", *, canonical: bool = False) -> bool:
        known = KNOWN + (CANONICAL_CHARACTER_TERMS if canonical else ())
        return bounded_animate_agent_leader(
            leader,
            action=action,
            known_actor_terms=known,
            modifier_tail_validator=modifier_tail,
        )

    def test_canonical_character_terms_are_read_from_project_index_route(self):
        self.assertIn("菲奥奈", CANONICAL_CHARACTER_TERMS)
        self.assertIn("格兰", CANONICAL_CHARACTER_TERMS)
        self.assertIn("凯姆", CANONICAL_CHARACTER_TERMS)
        self.assertIn("蒂娅", CANONICAL_CHARACTER_TERMS)

    def test_unseen_human_roles_are_positive_without_name_whitelist(self):
        for leader in ("贵族", "骑士", "医生", "调查员", "工程师", "研究者"):
            with self.subTest(leader=leader):
                self.assertTrue(self.prove(leader))

    def test_scene_prefix_plus_unseen_human_role_and_manner_is_positive(self):
        self.assertTrue(self.prove("礼拜堂中央年轻祭司十分郑重地"))

    def test_project_proper_name_requires_canonical_identity_not_body_verb(self):
        self.assertFalse(self.prove("菲奥奈", "面向"))
        self.assertFalse(self.prove("菲奥奈", "转身面向"))
        self.assertTrue(self.prove("菲奥奈", "面向", canonical=True))
        self.assertTrue(self.prove("菲奥奈缓缓地", "回身面向", canonical=True))
        self.assertFalse(self.prove("虚构专名甲", "转身面向", canonical=True))

    def test_open_nonagent_categories_fail_closed(self):
        for leader in ("钟楼", "教堂", "雕像", "塔楼", "马车", "广场", "石桥", "长街", "房屋", "旗帜"):
            with self.subTest(leader=leader):
                self.assertFalse(self.prove(leader, canonical=True))

    def test_embodied_verb_never_launders_unknown_object_identity(self):
        for leader in ("钟楼", "教堂", "雕像", "塔楼", "祭坛", "石碑"):
            with self.subTest(leader=leader):
                self.assertFalse(self.prove(leader, "转身面向", canonical=True))


if __name__ == "__main__":
    unittest.main()
