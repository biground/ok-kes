import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _Box:
    def __init__(self, name, x, y, width=100, height=30):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height


class _OpenCC:
    def __init__(self, _config):
        pass

    def convert(self, text):
        return text.translate(str.maketrans({"調": "调", "節": "节", "靈": "灵", "詛": "诅"}))


class _Task:
    def __init__(self, titles, priority, name="自动出击模式", descriptions=()):
        self.width = 1000
        self.height = 1000
        self.name = name
        self.config = {"命运优先级": priority}
        self.all_texts = [
            _Box("请选择你的命运", 450, 920),
            *[_Box(title, x, 480) for title, x in zip(titles, (160, 450, 740))],
            *[_Box(description, x, 650) for description, x in zip(descriptions, (160, 450, 740))],
        ]
        self.clicked_boxes = []
        self.sleeps = []
        self.logs = []

    def click_box(self, box):
        self.clicked_boxes.append(box)

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def log_info(self, message):
        self.logs.append(message)


class TestDestinyChoice(unittest.TestCase):
    def setUp(self):
        ok_module = types.ModuleType("ok")
        ok_module.TriggerTask = object
        opencc_module = types.ModuleType("opencc")
        opencc_module.OpenCC = _OpenCC
        self.module_patch = patch.dict(sys.modules, {
            "ok": ok_module,
            "opencc": opencc_module,
            "cv2": types.ModuleType("cv2"),
            "numpy": types.ModuleType("numpy"),
        })
        self.module_patch.start()
        module_name = "_utils_destiny_under_test"
        spec = importlib.util.spec_from_file_location(
            module_name,
            Path(__file__).resolve().parents[1] / "ok_tasks" / "utils.py",
        )
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = self.module
        spec.loader.exec_module(self.module)

    def tearDown(self):
        sys.modules.pop("_utils_destiny_under_test", None)
        self.module_patch.stop()

    def test_chooses_highest_priority_title_not_display_order(self):
        task = _Task(
            ["最终幕", "丢弃诅咒", "红色命运"],
            ["红色命运", "丢弃诅咒", "最终幕"],
        )

        with patch.object(self.module.random, "choice") as choice:
            handled = self.module.handle_destiny_choice(task)

        self.assertTrue(handled)
        self.assertEqual(["红色命运"], [box.name for box in task.clicked_boxes])
        choice.assert_not_called()
        self.assertEqual([2, 1], task.sleeps)

    def test_normalizes_punctuation_whitespace_and_traditional_title(self):
        task = _Task(
            ["精通　：　調節", "最终幕", "红色命运"],
            ["精通调节", "红色命运"],
        )

        with patch.object(self.module.random, "choice") as choice:
            self.module.handle_destiny_choice(task)

        self.assertEqual(["精通　：　調節"], [box.name for box in task.clicked_boxes])
        choice.assert_not_called()

    def test_description_text_does_not_match_destiny_priority(self):
        task = _Task(
            ["未知命运", "最终幕", "红色命运"],
            ["丢弃诅咒"],
            descriptions=["丢弃诅咒", "无关描述", "无关描述"],
        )

        with patch.object(self.module.random, "choice", side_effect=lambda titles: titles[0]) as choice:
            self.module.handle_destiny_choice(task)

        self.assertEqual(["未知命运"], [box.name for box in task.clicked_boxes])
        choice.assert_called_once()

    def test_uses_random_choice_only_when_no_title_matches(self):
        task = _Task(
            ["未知命运", "最终幕", "红色命运"],
            ["丢弃诅咒"],
        )

        with patch.object(self.module.random, "choice", side_effect=lambda titles: titles[1]) as choice:
            self.module.handle_destiny_choice(task)

        self.assertEqual(["最终幕"], [box.name for box in task.clicked_boxes])
        choice.assert_called_once()

    def test_chaos_mode_keeps_existing_random_choice(self):
        task = _Task(
            ["最终幕", "丢弃诅咒", "红色命运"],
            ["红色命运"],
            name="自动卡厄思模式",
        )

        with patch.object(self.module.random, "choice", side_effect=lambda titles: titles[0]) as choice:
            self.module.handle_destiny_choice(task)

        self.assertEqual(["最终幕"], [box.name for box in task.clicked_boxes])
        choice.assert_called_once()


if __name__ == "__main__":
    unittest.main()
