import sys
import unittest
from pathlib import Path
from unittest.mock import patch


OK_TASKS_PATH = Path(__file__).resolve().parents[1] / "ok_tasks"
sys.path.insert(0, str(OK_TASKS_PATH))
import utils_sortie  # noqa: E402


class _Box:

    def __init__(self, name):
        self.name = name


class _Task:

    def __init__(self):
        self.disable_calls = 0
        self.clicks = []
        self.sleeps = []
        self.logs = []

    def disable(self):
        self.disable_calls += 1

    def click(self, *coordinates):
        self.clicks.append(coordinates)

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def log_info(self, message):
        self.logs.append(message)


class TestSortieSupply(unittest.TestCase):

    def test_ether_supply_stops_task_without_clicking_dialog(self):
        task = _Task()

        with patch.object(utils_sortie, "find_box_at_point", return_value=_Box("以太补充")), \
                patch.object(utils_sortie, "_get_game_text", return_value="以太补充"):
            handled = utils_sortie.handle_ether_supply(task)

        self.assertTrue(handled)
        self.assertEqual(1, task.disable_calls)
        self.assertEqual([], task.clicks)
        self.assertEqual([], task.sleeps)
        self.assertIn("体力不足", "".join(task.logs))

    def test_other_page_does_not_stop_task(self):
        task = _Task()

        with patch.object(utils_sortie, "find_box_at_point", return_value=_Box("其他页面")), \
                patch.object(utils_sortie, "_get_game_text", return_value="以太补充"):
            handled = utils_sortie.handle_ether_supply(task)

        self.assertFalse(handled)
        self.assertEqual(0, task.disable_calls)

    def test_ether_supply_handler_runs_before_generic_confirm(self):
        self.assertLess(
            utils_sortie.PAGE_HANDLERS.index(utils_sortie.handle_ether_supply),
            utils_sortie.PAGE_HANDLERS.index(utils_sortie.handle_confirm),
        )


if __name__ == "__main__":
    unittest.main()
