import sys
import types
import unittest
from pathlib import Path


OK_TASKS_PATH = Path(__file__).resolve().parents[1] / "ok_tasks"
sys.path.insert(0, str(OK_TASKS_PATH))
import utils_sortie  # noqa: E402


class _Box:

    def __init__(self, name, x, y, width=80, height=30):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height


class _Task:

    def __init__(self, game_language="繁体中文", flash_text="灵光一闪",
                 hp="80/100", credit="456", threshold="50", include_cost=True):
        self.width = 1000
        self.height = 1000
        self.config = {"生命值大于多少优先闪光(百分比)": threshold}
        self.default_config = {}
        self.node_status = {"flash_or_rest": True, "shop": False}
        self.executor = types.SimpleNamespace(
            global_config=types.SimpleNamespace(
                get_config=lambda _name: {"游戏语言": game_language}
            )
        )
        self.flash_box = _Box(flash_text, 790, 470)
        self.rest_box = _Box("休息", 300, 700)
        self.all_texts = [
            self.flash_box,
            self.rest_box,
            _Box("免费", 320, 760),
            _Box(hp, 175, 20, width=75, height=40),
            _Box(credit, 720, 30, width=100, height=50),
        ]
        if include_cost:
            self.all_texts.append(_Box("30", 800, 540))
        self.clicks = []
        self.sleeps = []
        self.logs = []

    def click_box(self, box):
        self.clicks.append(box)

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def log_info(self, message):
        self.logs.append(message)


class TestSortieRestPriority(unittest.TestCase):

    def test_traditional_client_prioritizes_epiphany_above_hp_threshold(self):
        task = _Task()

        handled = utils_sortie.handle_rest_sortie(task)

        self.assertTrue(handled)
        self.assertEqual([task.flash_box], task.clicks)
        self.assertEqual([2], task.sleeps)
        self.assertFalse(task.node_status["flash_or_rest"])
        self.assertIn("文本=灵光一闪", "".join(task.logs))

    def test_simplified_client_still_prioritizes_flash(self):
        task = _Task(game_language="简体中文", flash_text="闪光")

        utils_sortie.handle_rest_sortie(task)

        self.assertEqual([task.flash_box], task.clicks)

    def test_missing_cost_ocr_does_not_hide_available_flash_option(self):
        task = _Task(include_cost=False)

        utils_sortie.handle_rest_sortie(task)

        self.assertEqual([task.flash_box], task.clicks)
        self.assertIn("费用30识别=False", "".join(task.logs))

    def test_exactly_thirty_credit_is_enough_for_flash(self):
        task = _Task(credit="30")

        utils_sortie.handle_rest_sortie(task)

        self.assertEqual([task.flash_box], task.clicks)

    def test_below_hp_threshold_falls_back_to_rest(self):
        task = _Task(hp="49/100", threshold="50")

        handled = utils_sortie.handle_rest_sortie(task)

        self.assertTrue(handled)
        self.assertEqual([task.rest_box], task.clicks)
        self.assertEqual([1], task.sleeps)
        self.assertIn("不满足闪光条件", "".join(task.logs))


if __name__ == "__main__":
    unittest.main()
