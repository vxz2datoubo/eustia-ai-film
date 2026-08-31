import unittest

from learning_retriever.entity_semantics import bounded_animate_agent_leader


KNOWN = ("群众", "卫兵", "凯姆", "蒂娅", "圣女")


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
    def prove(self, leader: str, action: str = "面向") -> bool:
        return bounded_animate_agent_leader(
            leader,
            action=action,
            known_actor_terms=KNOWN,
            modifier_tail_validator=modifier_tail,
        )

    def test_unseen_human_roles_are_positive_without_name_whitelist(self):
        for leader in ("贵族", "骑士", "医生", "调查员", "工程师", "研究者"):
            with self.subTest(leader=leader):
                self.assertTrue(self.prove(leader))

    def test_scene_prefix_plus_unseen_human_role_and_manner_is_positive(self):
        self.assertTrue(self.prove("礼拜堂中央年轻祭司十分郑重地"))

    def test_unseen_proper_name_requires_embodied_transition(self):
        self.assertFalse(self.prove("菲奥奈", "面向"))
        self.assertTrue(self.prove("菲奥奈", "转身面向"))
        self.assertTrue(self.prove("菲奥奈缓缓地", "回身面向"))

    def test_open_nonagent_categories_fail_closed(self):
        for leader in ("钟楼", "教堂", "雕像", "塔楼", "马车", "广场", "石桥", "长街", "房屋", "旗帜"):
            with self.subTest(leader=leader):
                self.assertFalse(self.prove(leader))

    def test_embodied_verb_does_not_launder_structural_subject(self):
        for leader in ("钟楼", "教堂", "雕像", "塔楼"):
            with self.subTest(leader=leader):
                self.assertFalse(self.prove(leader, "转身面向"))


if __name__ == "__main__":
    unittest.main()
