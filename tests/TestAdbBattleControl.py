import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


OK_TASKS_PATH = Path(__file__).resolve().parents[1] / "ok_tasks"
sys.path.insert(0, str(OK_TASKS_PATH))
import utils_sortie  # noqa: E402


class _Feature:
    name = "finishturn"


class _TextBox:

    def __init__(self, name, x, y, width=20, height=20, confidence=0.9):
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.confidence = confidence


class _BattleTask:

    def __init__(self, adb=True, ep_full=False):
        self._adb = adb
        self.width = 1600
        self.height = 900
        self.frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.all_texts = []
        if ep_full:
            ep_x = int(0.032 * self.width)
            ep_y = int(0.947 * self.height)
            self.frame[ep_y - 2:ep_y + 3, ep_x - 2:ep_x + 3, :3] = (255, 255, 193)
        self.sent_keys = []
        self.swipes = []
        self.clicked_boxes = []
        self.sleeps = []
        self.logs = []
        self.ocr_results = []
        self.ocr_calls = []

    def is_adb(self):
        return self._adb

    def send_key(self, key):
        self.sent_keys.append(key)

    def swipe_relative(self, from_x, from_y, to_x, to_y, duration):
        self.swipes.append((from_x, from_y, to_x, to_y, duration))

    def click_box(self, box, **kwargs):
        self.clicked_boxes.append((box, kwargs))

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def log_info(self, message):
        self.logs.append(message)

    def ocr(self, *coordinates, **kwargs):
        self.ocr_calls.append((coordinates, kwargs))
        return list(self.ocr_results)

    @staticmethod
    def box_of_screen(*coordinates):
        return coordinates

    @staticmethod
    def find_feature(**_kwargs):
        return [_Feature()]


class TestAdbBattleControl(unittest.TestCase):

    def test_targeted_hand_ocr_recovers_card_missed_by_fullscreen_ocr(self):
        task = _BattleTask(adb=True)
        task.all_texts = [_TextBox("剑幕", 760, 675, width=45, height=25)]
        sword_rain = _TextBox("剑之雨", 850, 675, width=70, height=25, confidence=0.99)
        task.ocr_results = [sword_rain]

        cards = utils_sortie._hand_card_names(task)

        self.assertEqual(["剑幕", "剑之雨"], [card.name for card in cards])
        self.assertEqual(
            [((0.150, 0.640, 0.840, 0.870), {"threshold": 0.5})],
            task.ocr_calls,
        )
        self.assertIn("手牌局部OCR识别到1张卡牌", "".join(task.logs))

    def test_sword_rain_alias_matches_configured_short_name(self):
        self.assertTrue(utils_sortie._card_name_matches("剑雨", "剑之雨"))
        self.assertTrue(utils_sortie._card_name_matches("剑雨", "劍之雨"))
        self.assertFalse(utils_sortie._card_name_matches("剑雨", "剑幕"))

    def test_adb_card_uses_coordinate_swipe_without_keys(self):
        task = _BattleTask(adb=True)
        card = {"name": "极光剑", "key": "7", "touch_x": 0.62, "touch_y": 0.76}

        handled = utils_sortie._play_card(task, card)

        self.assertTrue(handled)
        self.assertEqual([(0.62, 0.76, 0.65, 0.45, 0.35)], task.swipes)
        self.assertEqual([], task.sent_keys)

    def test_adb_card_targets_leftmost_enemy_action_counter(self):
        task = _BattleTask(adb=True)
        task.all_texts = [
            _TextBox("8", 890, 260),
            _TextBox("8", 1280, 270),
            _TextBox("654", 1000, 245),
        ]
        card = {"name": "极光剑", "key": None, "touch_x": 0.62, "touch_y": 0.76}

        handled = utils_sortie._play_card(task, card)

        self.assertTrue(handled)
        target_x = (890 + 10) / 1600
        target_y = (260 + 10) / 900 + 0.18
        self.assertEqual([(0.62, 0.76, target_x, target_y, 0.35)], task.swipes)
        self.assertEqual([], task.sent_keys)

    def test_windows_card_keeps_keyboard_control(self):
        task = _BattleTask(adb=False)
        card = {"name": "极光剑", "key": "7", "touch_x": 0.62, "touch_y": 0.76}

        handled = utils_sortie._play_card(task, card)

        self.assertTrue(handled)
        self.assertEqual(["7", "enter"], task.sent_keys)
        self.assertEqual([], task.swipes)

    def test_adb_fallback_plays_only_rightmost_card_then_refreshes(self):
        task = _BattleTask(adb=True)
        cards = [
            {"name": "左侧牌", "key": "1", "touch_x": 0.25, "touch_y": 0.76},
            {"name": "右侧牌", "key": "2", "touch_x": 0.72, "touch_y": 0.76},
        ]

        handled = utils_sortie._try_cards_fallback(task, cards, 2)

        self.assertTrue(handled)
        self.assertEqual([(0.72, 0.76, 0.65, 0.45, 0.35)], task.swipes)
        self.assertEqual([], task.sent_keys)

    def test_adb_finish_turn_clicks_detected_button_without_keys(self):
        task = _BattleTask(adb=True)
        feature = _Feature()

        handled = utils_sortie._finish_turn(task, feature)

        self.assertTrue(handled)
        self.assertEqual([(feature, {"after_sleep": 0})], task.clicked_boxes)
        self.assertEqual([], task.sent_keys)

    def test_windows_finish_turn_clicks_detected_button_without_keys(self):
        task = _BattleTask(adb=False)
        feature = _Feature()

        handled = utils_sortie._finish_turn(task, feature)

        self.assertTrue(handled)
        self.assertEqual([(feature, {"after_sleep": 0})], task.clicked_boxes)
        self.assertEqual([], task.sent_keys)

    def test_adb_battle_with_full_ep_never_sends_f_or_number_keys(self):
        task = _BattleTask(adb=True, ep_full=True)
        card = {"name": "极光剑", "key": None, "touch_x": 0.61, "touch_y": 0.77}

        with patch.object(utils_sortie, "_read_hand_count", return_value=1), \
                patch.object(utils_sortie, "is_frame_stuck", return_value=False), \
                patch.object(utils_sortie, "_hand_card_names", return_value=[object()]), \
                patch.object(utils_sortie, "_hand_cards", return_value=[card]), \
                patch.object(utils_sortie, "_get_card_list", return_value=["极光剑"]):
            handled = utils_sortie.handle_battle_page(task)

        self.assertTrue(handled)
        self.assertEqual([(0.61, 0.77, 0.65, 0.45, 0.35)], task.swipes)
        self.assertEqual([], task.sent_keys)

    def test_adb_battle_plays_sword_rain_when_priority_uses_short_alias(self):
        task = _BattleTask(adb=True)
        card = {"name": "剑之雨", "key": None, "touch_x": 0.55, "touch_y": 0.76}

        with patch.object(utils_sortie, "_read_hand_count", return_value=7), \
                patch.object(utils_sortie, "is_frame_stuck", return_value=False), \
                patch.object(utils_sortie, "_hand_card_names", return_value=[object()]), \
                patch.object(utils_sortie, "_hand_cards", return_value=[card]), \
                patch.object(utils_sortie, "_get_card_list", return_value=["剑雨"]):
            handled = utils_sortie.handle_battle_page(task)

        self.assertTrue(handled)
        self.assertEqual([(0.55, 0.76, 0.65, 0.45, 0.35)], task.swipes)
        self.assertIn("出牌优先级匹配: 卡牌「剑之雨」", "".join(task.logs))

    def test_adb_battle_without_cards_clicks_finish_turn(self):
        task = _BattleTask(adb=True)

        with patch.object(utils_sortie, "_read_hand_count", return_value=0), \
                patch.object(utils_sortie, "is_frame_stuck", return_value=False), \
                patch.object(utils_sortie, "_hand_card_names", return_value=[]), \
                patch.object(utils_sortie, "_hand_cards", return_value=[]):
            handled = utils_sortie.handle_battle_page(task)

        self.assertTrue(handled)
        self.assertEqual(1, len(task.clicked_boxes))
        self.assertEqual([], task.sent_keys)


if __name__ == "__main__":
    unittest.main()
