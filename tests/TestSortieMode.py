import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _Box:
    def __init__(self, name, confidence=0.99):
        self.name = name
        self.confidence = confidence


class _Config(dict):
    def __init__(self, language):
        super().__init__({'游戏语言': language})
        self.write_calls = []

    def __setitem__(self, key, value):
        self.write_calls.append((key, value))
        super().__setitem__(key, value)


class _GlobalConfig:
    def __init__(self, config):
        self.config = config

    def get_config(self, name):
        if name != '游戏语言':
            raise AssertionError(name)
        return self.config


class _Signal:
    def __init__(self):
        self.calls = 0

    def emit(self):
        self.calls += 1


class _TriggerTask:
    def fix_texts(self, boxes):
        for box in boxes:
            box.name = box.name.replace('擊', '击')


class _OpenCC:
    def __init__(self, _config):
        pass

    def convert(self, text):
        return text


class TestSortieLanguageDetection(unittest.TestCase):
    def setUp(self):
        self.signal = _Signal()
        ok_module = types.ModuleType('ok')
        ok_module.__path__ = []
        ok_module.TriggerTask = _TriggerTask
        ok_module.og = types.SimpleNamespace()
        gui_module = types.ModuleType('ok.gui')
        gui_module.__path__ = []
        communicate_module = types.ModuleType('ok.gui.Communicate')
        communicate_module.communicate = types.SimpleNamespace(task_list_updated=self.signal)
        self.module_patch = patch.dict(sys.modules, {
            'ok': ok_module,
            'ok.gui': gui_module,
            'ok.gui.Communicate': communicate_module,
            'utils_sortie': types.SimpleNamespace(PAGE_HANDLERS=[]),
            'config_io': types.SimpleNamespace(
                make_export_callback=lambda task: None,
                make_import_callback=lambda task: None,
            ),
            'opencc': types.SimpleNamespace(OpenCC=_OpenCC),
        })
        self.module_patch.start()
        module_name = '_sortie_mode_under_test'
        spec = importlib.util.spec_from_file_location(
            module_name,
            Path(__file__).resolve().parents[1] / 'ok_tasks' / 'SortieMode.py',
        )
        self.module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = self.module
        spec.loader.exec_module(self.module)

    def tearDown(self):
        self.module_patch.stop()

    def _task(self, language, boxes):
        config = _Config(language)
        task = self.module.SortieMode.__new__(self.module.SortieMode)
        task.executor = types.SimpleNamespace(global_config=_GlobalConfig(config))
        task.logs = []
        task.log_info = task.logs.append
        task.ocr_calls = []

        def ocr(*args, **kwargs):
            task.ocr_calls.append((args, kwargs))
            results = [_Box(box.name, box.confidence) for box in boxes]
            task.fix_texts(results)
            return results

        task.ocr = ocr
        return task, config

    def test_exact_simplified_sortie_title_updates_global_language(self):
        task, config = self._task('繁体中文', [_Box('出击')])

        task._detect_game_language()

        self.assertEqual('简体中文', config['游戏语言'])
        self.assertEqual([('游戏语言', '简体中文')], config.write_calls)
        self.assertEqual(1, self.signal.calls)
        self.assertEqual(((0.65, 0.10, 0.75, 0.18), {'threshold': 0.8}), task.ocr_calls[0])
        self.assertIn('出击', ''.join(task.logs))
        self.assertIn('繁体中文', ''.join(task.logs))
        self.assertIn('简体中文', ''.join(task.logs))

    def test_exact_traditional_sortie_title_updates_global_language_before_simplification(self):
        task, config = self._task('简体中文', [_Box('出擊')])

        task._detect_game_language()

        self.assertEqual('繁体中文', config['游戏语言'])
        self.assertEqual([('游戏语言', '繁体中文')], config.write_calls)
        self.assertEqual(1, self.signal.calls)

    def test_no_unambiguous_high_confidence_title_keeps_existing_language(self):
        for boxes in ([_Box('出击模式')], [_Box('出击'), _Box('出擊')], [_Box('出击', 0.79)]):
            with self.subTest(boxes=[box.name for box in boxes]):
                task, config = self._task('日文', boxes)

                task._detect_game_language()

                self.assertEqual('日文', config['游戏语言'])
                self.assertEqual([], config.write_calls)
                self.assertEqual(0, self.signal.calls)

    def test_repeated_same_language_detection_does_not_write_or_rescan(self):
        task, config = self._task('简体中文', [_Box('出击')])

        task._detect_game_language()
        task._detect_game_language()

        self.assertEqual('简体中文', config['游戏语言'])
        self.assertEqual([], config.write_calls)
        self.assertEqual(0, self.signal.calls)
        self.assertEqual(1, len(task.ocr_calls))


if __name__ == '__main__':
    unittest.main()
