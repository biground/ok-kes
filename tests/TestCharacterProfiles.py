import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


OK_TASKS_PATH = Path(__file__).resolve().parents[1] / "ok_tasks"
sys.path.insert(0, str(OK_TASKS_PATH))
import character_profiles  # noqa: E402
import config_io  # noqa: E402
import utils  # noqa: E402


def _profile(name, alias_prefix, card_prefix):
    return {
        "name": name,
        "aliases": [f"{alias_prefix}亚", f"{alias_prefix}娅"],
        "cards": [f"{card_prefix}{index}" for index in range(1, 9)],
    }


class _Config(dict):

    def __init__(self, config_file, values):
        super().__init__(values)
        self.config_file = str(config_file)


class _Task:

    def __init__(self, config_file, values, profiles=None):
        self.config = _Config(config_file, values)
        if profiles is not None:
            self.character_profiles = profiles
        self.logs = []

    def log_info(self, message):
        self.logs.append(message)


class TestCharacterProfiles(unittest.TestCase):

    def test_profile_document_parses_chinese_commas_and_requires_eight_cards(self):
        document = character_profiles.normalize_profile_document({
            "characters": [{
                "name": "妮娅",
                "aliases": "尼亚，妮娅",
                "cards": "卡1,卡2，卡3,卡4,卡5,卡6,卡7,卡8",
            }],
        })

        self.assertEqual(["尼亚", "妮娅"], document["characters"][0]["aliases"])
        self.assertEqual(8, len(document["characters"][0]["cards"]))

        with self.assertRaisesRegex(character_profiles.CharacterProfileError, "8 张卡牌"):
            character_profiles.normalize_profile_document({
                "characters": [{
                    "name": "妮娅",
                    "aliases": "尼亚,妮娅",
                    "cards": "卡1,卡2,卡3",
                }],
            })

    def test_profile_file_round_trip_uses_config_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "SortieMode.json"
            task = _Task(config_file, {})
            profiles = [_profile("角色A", "A", "A卡")]

            character_profiles.write_profile_file(
                character_profiles.profile_file_path(task), profiles
            )
            loaded = character_profiles.load_task_profiles(task)

            self.assertEqual(profiles, loaded)
            self.assertEqual(
                Path(temp_dir) / character_profiles.PROFILE_FILE_NAME,
                Path(character_profiles.profile_file_path(task)),
            )

    def test_regular_config_export_keeps_base64_format_and_excludes_internal_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "SortieMode.json"
            config_file.write_text(json.dumps({
                "主战员优先级": ["角色A"],
                "配置卡牌": ["角色卡1"],
                "_角色卡牌来源": {"角色A": ["角色卡1"]},
            }, ensure_ascii=False), encoding="utf-8")
            task = _Task(config_file, {})

            encoded = config_io._export_config_to_text(task)
            exported = json.loads(base64.b64decode(encoded).decode("utf-8"))

            self.assertEqual(["角色A"], exported["主战员优先级"])
            self.assertEqual(["角色卡1"], exported["配置卡牌"])
            self.assertNotIn("_角色卡牌来源", exported)

    def test_alias_matching_uses_profile_recognition_names_and_free_text_fallback(self):
        task = _Task("SortieMode.json", {}, [{
            "name": "客户端角色",
            "aliases": ["尼亚", "妮娅"],
            "cards": [f"卡{index}" for index in range(1, 9)],
        }])

        self.assertTrue(character_profiles.member_name_matches(task, "客户端角色", "SSR妮娅"))
        self.assertTrue(character_profiles.member_name_matches(task, "任意输入", "任意输入角色"))
        self.assertFalse(character_profiles.member_name_matches(task, "客户端角色", "客户端角色"))

    def test_selected_profiles_append_cards_and_removed_profile_clears_its_cards(self):
        profiles = [_profile("角色A", "A", "A卡"), _profile("角色B", "B", "B卡")]
        task = _Task("SortieMode.json", {
            character_profiles.MAIN_MEMBER_KEY: ["自由输入", "角色A"],
            character_profiles.BATTLE_MEMBER_KEY: [],
            character_profiles.CONFIGURED_CARDS_KEY: ["手工卡"],
            character_profiles.PROFILE_CARD_SOURCES_KEY: {},
        }, profiles)

        character_profiles.sync_task_character_cards(task)
        self.assertEqual(
            ["手工卡", *profiles[0]["cards"]],
            task.config[character_profiles.CONFIGURED_CARDS_KEY],
        )

        task.config[character_profiles.BATTLE_MEMBER_KEY] = ["角色B"]
        character_profiles.sync_task_character_cards(task)
        self.assertEqual(
            ["手工卡", *profiles[0]["cards"], *profiles[1]["cards"]],
            task.config[character_profiles.CONFIGURED_CARDS_KEY],
        )

        task.config[character_profiles.MAIN_MEMBER_KEY] = ["自由输入"]
        character_profiles.sync_task_character_cards(task)
        self.assertEqual(
            ["手工卡", *profiles[1]["cards"]],
            task.config[character_profiles.CONFIGURED_CARDS_KEY],
        )

    def test_configured_profile_is_mutually_exclusive_between_member_lists(self):
        profiles = [_profile("角色A", "A", "A卡")]
        task = _Task("SortieMode.json", {
            character_profiles.MAIN_MEMBER_KEY: ["角色A"],
            character_profiles.BATTLE_MEMBER_KEY: ["自由输入", "角色A"],
            character_profiles.CONFIGURED_CARDS_KEY: [],
            character_profiles.PROFILE_CARD_SOURCES_KEY: {},
        }, profiles)

        character_profiles.sync_task_character_cards(task)

        self.assertEqual(["自由输入"], task.config[character_profiles.BATTLE_MEMBER_KEY])

    def test_operation_priority_keeps_manual_order_then_appends_profile_cards(self):
        task = _Task("SortieMode.json", {
            "闪光卡牌列表": ["手动优先", "角色卡2"],
            "配置卡牌": ["角色卡1", "角色卡2"],
        })

        self.assertEqual(
            ["手动优先", "角色卡2", "角色卡1"],
            utils._get_card_list(task, "闪光卡牌列表"),
        )

    def test_discard_selection_uses_discard_priority_configuration(self):
        task = _Task("SortieMode.json", {})
        prompt = type("Prompt", (), {"name": "请选择1张丢弃的卡牌"})()

        with patch.object(utils, "find_box_at_point", side_effect=[prompt, None]), \
                patch.object(utils, "select_card") as select_card:
            handled = utils.handle_select_card(task)

        self.assertTrue(handled)
        select_card.assert_called_once_with(
            task, [], fallback_delete=True, count=1, action="丢弃"
        )


if __name__ == "__main__":
    unittest.main()
