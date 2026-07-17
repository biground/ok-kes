# ok-kes Convention Evidence

## Automation Placement and Dispatch

`src/config.py` enables `custom_tasks`, while its built-in task list contains only the template task and diagnosis task. The gameplay modes live in `ok_tasks/`:

- `SortieMode.run`, `ChaosMode.run`, and `StoryMode.run` each populate `self.all_texts` once and iterate a mode-specific `PAGE_HANDLERS` list.
- `ok_tasks/utils_sortie.py`, `ok_tasks/utils_chaos.py`, and `ok_tasks/utils_story.py` make handler ordering explicit. Recent history also changes ordering to fix behavior (`2805bff`, `eecbce2`).

Use `utils.py` for behavior reused by more than one mode; use the matching `utils_<mode>.py` for mode-only logic. Preserve the `True`/`False` dispatch contract: `733f5ee` changed a handler to `False` specifically so the next handler could continue.

## OCR and Language Boundary

The mode classes normalize each frame with OpenCC before dispatch. Shared helpers then use `task.all_texts`:

- `utils.py:_simplify_texts`, `_get_config_value`, `find_text`, and `find_box_at_point`
- `utils.py:_get_game_text`, backed by `ok_tasks/assets/game_text_map/zh_tw.py`

Use the mapping only for vocabulary differences that remain after traditional-to-simplified conversion. The same failure has recurred in history: `da8e254` and `d06c55d` fix unnormalized OCR; several earlier commits add missing Traditional-Chinese mappings.

After scrolling or an interaction that changes the screen, refresh OCR and normalize before evaluating subsequent text. `utils.py:select_card` and `utils_sortie.py` demonstrate this pattern.

## Persistent Configuration

`SortieMode` and `ChaosMode` declare user settings in `default_config` and attach the shared import/export callbacks. `config_io.py` base64-encodes user keys, preserves underscore-prefixed runtime state, writes the config file, and refreshes the GUI.

Keep existing setting names stable. If a renamed or reshaped setting is unavoidable, add a deliberate compatibility migration instead of silently discarding the user's saved preference.

## Verification and Packaging

`run_tests.ps1` and `.github/workflows/build.yml` execute each Python unittest file. The release workflow runs on `v*` tags with Python 3.12, inlines dependencies, and packages with PyAppify using `pyappify.yml`.

`BUILD.md` documents a manual PyInstaller procedure, but CI uses PyAppify; treat a requested manual package as a separate choice rather than replacing the tagged release workflow by default.

## Non-rules

- `src/tasks/MyOneTimeTask.py` and `tests/TestMain.py` are framework/demo coverage. Do not copy their English demo configuration fields into gameplay modes as a project convention.
- Existing `.agents/skills/` entries are generic task, i18n, venv, codegen, and release skills. Keep them separate from this project-specific skill.
