import importlib.util
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _OpenCC:
    def __init__(self, _config):
        pass

    def convert(self, text):
        return text


class TestGameTextMap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ok_module = types.ModuleType('ok')
        ok_module.TriggerTask = object
        cls.module_patch = patch.dict(sys.modules, {
            'ok': ok_module,
            'opencc': types.SimpleNamespace(OpenCC=_OpenCC),
        })
        cls.module_patch.start()

        module_name = '_game_text_utils_under_test'
        spec = importlib.util.spec_from_file_location(
            module_name,
            Path(__file__).resolve().parents[1] / 'ok_tasks' / 'utils.py',
        )
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        cls.module_patch.stop()

    def setUp(self):
        self.module._LOADED_MAPS.clear()

    def test_source_layout_loads_traditional_chinese_map(self):
        mapping = self.module._load_game_text_map('繁体中文')

        self.assertEqual('战斗员配置', mapping['主战员配置'])

    def test_frozen_top_level_module_loads_map_from_ok_tasks_data(self):
        source_map = (
            Path(__file__).resolve().parents[1]
            / 'ok_tasks' / 'assets' / 'game_text_map' / 'zh_tw.py'
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir)
            bundled_map = (
                bundle_root / 'ok_tasks' / 'assets' / 'game_text_map' / 'zh_tw.py'
            )
            bundled_map.parent.mkdir(parents=True)
            shutil.copy2(source_map, bundled_map)

            with patch.object(self.module, '__file__', str(bundle_root / 'utils.py')):
                with patch.object(sys, '_MEIPASS', str(bundle_root), create=True):
                    mapping = self.module._load_game_text_map('繁体中文')

        self.assertEqual('战斗员配置', mapping['主战员配置'])

    def test_frozen_mapping_is_used_by_page_matcher(self):
        task = types.SimpleNamespace(
            executor=types.SimpleNamespace(
                global_config=types.SimpleNamespace(
                    get_config=lambda name: {'游戏语言': '繁体中文'}
                )
            )
        )

        self.assertEqual(
            '战斗员配置',
            self.module._get_game_text(task, '主战员配置'),
        )


if __name__ == '__main__':
    unittest.main()
