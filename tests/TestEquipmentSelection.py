import unittest
from unittest.mock import patch

import numpy as np

from ok_tasks import utils


class _Box:

    def __init__(self, name, x, y, width=40, height=20):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class _Task:

    def __init__(self):
        self.width = 1600
        self.height = 900
        self.frame = np.full((self.height, self.width, 3), 30, dtype=np.uint8)
        self.all_texts = []
        self.clicks = []
        self.sleeps = []
        self.logs = []

    def click(self, *coordinates):
        self.clicks.append(coordinates)

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def log_info(self, message):
        self.logs.append(message)


def _level_box(task, center_y):
    return _Box("等级", int(0.62 * task.width), center_y - 10)


def _stat_box(task, name):
    return _Box(name, int(0.20 * task.width), int(0.30 * task.height), 80, 24)


def _fill_equipment_slot(task, row_center_y, slot_index):
    center_x = int(utils._EQUIPMENT_SLOT_X_RATIOS[slot_index] * task.width)
    half_width = int(0.020 * task.width)
    half_height = int(0.032 * task.height)
    task.frame[
        row_center_y - half_height:row_center_y + half_height + 1,
        center_x - half_width:center_x + half_width + 1,
    ] = (35, 90, 190)


class TestEquipmentSelection(unittest.TestCase):

    def setUp(self):
        self.task = _Task()
        self.rows = [
            _level_box(self.task, center_y)
            for center_y in (360, 470, 580)
        ]

    def test_prefers_completely_unequipped_member_with_empty_matching_slot(self):
        self.task.all_texts = [*self.rows, _stat_box(self.task, "防御 +21")]
        _fill_equipment_slot(self.task, 360, 1)
        _fill_equipment_slot(self.task, 580, 0)

        chosen = utils._choose_equipment_combatant(self.task, self.rows)

        self.assertIs(self.rows[1], chosen)
        self.assertIn("优先选择未穿戴防御装备", "".join(self.task.logs))

    def test_empty_current_type_beats_lower_total_with_that_type_filled(self):
        self.task.all_texts = [*self.rows, _stat_box(self.task, "生命值+60")]
        _fill_equipment_slot(self.task, 360, 2)
        _fill_equipment_slot(self.task, 470, 0)
        _fill_equipment_slot(self.task, 470, 1)
        for slot_index in range(3):
            _fill_equipment_slot(self.task, 580, slot_index)

        chosen = utils._choose_equipment_combatant(self.task, self.rows)

        self.assertIs(self.rows[1], chosen)

    def test_unknown_type_prefers_member_without_any_equipment(self):
        self.task.all_texts = list(self.rows)
        _fill_equipment_slot(self.task, 360, 0)
        _fill_equipment_slot(self.task, 580, 1)

        chosen = utils._choose_equipment_combatant(self.task, self.rows)

        self.assertIs(self.rows[1], chosen)
        self.assertIn("优先选择未穿戴任何装备", "".join(self.task.logs))

    def test_all_matching_slots_filled_uses_random_fallback(self):
        self.task.all_texts = [*self.rows, _stat_box(self.task, "防御")]
        for row_center_y in (360, 470, 580):
            _fill_equipment_slot(self.task, row_center_y, 1)

        with patch.object(utils.random, "choice", return_value=self.rows[-1]):
            chosen = utils._choose_equipment_combatant(self.task, self.rows)

        self.assertIs(self.rows[-1], chosen)
        self.assertIn("回退随机选择", "".join(self.task.logs))

    def test_handler_clicks_preferred_member(self):
        self.task.all_texts = [*self.rows, _stat_box(self.task, "攻击+31")]
        _fill_equipment_slot(self.task, 360, 0)
        _fill_equipment_slot(self.task, 580, 0)
        title = _Box("装备", 0, 0)
        hint = _Box("请选择主战员", 0, 0)

        with patch.object(utils, "find_box_at_point", side_effect=[title, hint]), \
                patch.object(utils, "_get_game_text", return_value="请选择主战员"):
            handled = utils.handle_equipment(self.task)

        self.assertFalse(handled)
        self.assertEqual([(0.756, 470 / self.task.height)], self.task.clicks)
        self.assertEqual([1], self.task.sleeps)


if __name__ == "__main__":
    unittest.main()
