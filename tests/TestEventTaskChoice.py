import unittest
from unittest.mock import patch

from ok_tasks import utils


class _Box:

    def __init__(self, name, x=0, y=0, width=100, height=20):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height


class _Task:

    def __init__(self, titles, name="自动出击模式", priority=None, treasure=False):
        self.width = 1000
        self.height = 1000
        self.name = name
        self.config = {"任务优先级": priority or []}
        descriptions = {
            "询问是谁": "确认【星之流浪者】资讯",
            "请求演奏": "随机命运从3条分支中选择1条获得",
            "请求共鸣之曲": "获得预见的命运【朝圣者之路】",
            "追问是谁": "确认【星之流浪者】资讯",
        }
        title_xs = (150, 400, 650)
        title_boxes = [
            _Box(title, x, 780)
            for title, x in zip(titles, title_xs)
        ]
        description_boxes = [
            _Box(descriptions[title], x, 830, width=210)
            for title, x in zip(titles, title_xs)
        ]
        self.all_texts = [*title_boxes, *description_boxes]
        self.treasure = _Box("treasure", 500, 400) if treasure else None
        self.clicks = []
        self.clicked_boxes = []
        self.sleeps = []
        self.logs = []

    def find_feature(self, feature_name, **_kwargs):
        if feature_name == "treasure" and self.treasure is not None:
            return [self.treasure]
        return []

    def box_of_screen(self, *_coordinates):
        return _Box("region")

    def click(self, *coordinates):
        self.clicks.append(coordinates)

    def click_box(self, box):
        self.clicked_boxes.append(box)

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def log_info(self, message):
        self.logs.append(message)


class TestEventTaskChoice(unittest.TestCase):

    def test_specific_three_options_force_request_performance(self):
        task = _Task(
            ["询问是谁", "请求演奏", "请求共鸣之曲"],
            priority=["获得预见的命运"],
        )

        with patch.object(utils.random, "choice") as random_choice:
            handled = utils.handle_event_task(task)

        self.assertTrue(handled)
        self.assertEqual([(0.45, 0.832), (0.45, 0.952)], task.clicks)
        self.assertEqual([], task.clicked_boxes)
        random_choice.assert_not_called()
        self.assertIn("强制选择: 请求演奏", "".join(task.logs))

    def test_forced_request_performance_runs_before_treasure(self):
        task = _Task(
            ["询问是谁", "请求演奏", "请求共鸣之曲"],
            priority=["获得预见的命运"],
            treasure=True,
        )

        utils.handle_event_task(task)

        self.assertEqual([(0.45, 0.832), (0.45, 0.952)], task.clicks)
        self.assertEqual([], task.clicked_boxes)

    def test_forced_choice_follows_title_when_display_order_changes(self):
        task = _Task(
            ["请求共鸣之曲", "询问是谁", "请求演奏"],
            priority=["获得预见的命运"],
        )

        utils.handle_event_task(task)

        self.assertEqual([(0.70, 0.832), (0.70, 0.952)], task.clicks)

    def test_other_combination_keeps_configured_description_priority(self):
        task = _Task(
            ["追问是谁", "请求演奏", "请求共鸣之曲"],
            priority=["获得预见的命运"],
        )

        utils.handle_event_task(task)

        self.assertEqual([(0.70, 0.832), (0.70, 0.952)], task.clicks)
        self.assertNotIn("强制选择", "".join(task.logs))

    def test_chaos_mode_keeps_configured_description_priority(self):
        task = _Task(
            ["询问是谁", "请求演奏", "请求共鸣之曲"],
            name="自动卡厄思模式",
            priority=["获得预见的命运"],
        )

        utils.handle_event_task(task)

        self.assertEqual([(0.70, 0.832), (0.70, 0.952)], task.clicks)
        self.assertNotIn("强制选择", "".join(task.logs))


if __name__ == "__main__":
    unittest.main()
