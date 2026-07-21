import sys
import unittest
from pathlib import Path
from unittest.mock import patch


OK_TASKS_PATH = Path(__file__).resolve().parents[1] / "ok_tasks"
sys.path.insert(0, str(OK_TASKS_PATH))
import utils_sortie  # noqa: E402


class _Box:

    def __init__(self, name, x=0, y=0, width=20, height=20):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class _Task:

    def __init__(self):
        self.clicks = []
        self.clicked_boxes = []
        self.sleeps = []
        self.logs = []

    def click(self, x, y):
        self.clicks.append((x, y))

    def click_box(self, box):
        self.clicked_boxes.append(box)

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def log_info(self, message):
        self.logs.append(message)


class TestSortieGetCard(unittest.TestCase):

    def test_unmatched_priority_clicks_skip_even_when_old_setting_is_false(self):
        task = _Task()
        skip_box = _Box("跳过", 1180, 820, 80, 40)
        boxes = [
            _Box("获得卡牌"),
            _Box("请选择1张获得的卡牌"),
            _Box("普通攻击", 200, 200),
            _Box("防御姿态", 600, 200),
            _Box("治疗术", 1000, 200),
            skip_box,
        ]

        def config_value(_task, key, default=None):
            values = {
                "获得卡牌优先级": ["展开极光"],
                "跳过非优先级卡牌": False,
            }
            return values.get(key, default)

        with patch.object(utils_sortie, "find_box_at_point", side_effect=boxes), \
                patch.object(utils_sortie, "_get_config_value", side_effect=config_value), \
                patch.object(utils_sortie.random, "choice") as random_choice:
            handled = utils_sortie.handle_get_card(task)

        self.assertTrue(handled)
        self.assertEqual([skip_box], task.clicked_boxes)
        self.assertEqual([], task.clicks)
        random_choice.assert_not_called()
        self.assertIn("未命中任何优先级卡牌，点击跳过", "".join(task.logs))

    def test_unmatched_priority_uses_skip_coordinate_when_text_is_missing(self):
        task = _Task()
        boxes = [
            _Box("获得卡牌"),
            _Box("请选择1张获得的卡牌"),
            _Box("普通攻击", 200, 200),
            _Box("防御姿态", 600, 200),
            _Box("治疗术", 1000, 200),
            None,
        ]

        with patch.object(utils_sortie, "find_box_at_point", side_effect=boxes), \
                patch.object(utils_sortie, "_get_config_value", return_value=["展开极光"]):
            handled = utils_sortie.handle_get_card(task)

        self.assertTrue(handled)
        self.assertEqual([(0.749, 0.931)], task.clicks)
        self.assertEqual([], task.clicked_boxes)


if __name__ == "__main__":
    unittest.main()
