# Finding: ok-kes automation conventions

## Scope

Reviewed repository documentation, local skills, entry/configuration files, custom task modes, shared handlers, language maps, tests, CI, and recent commits.

## Confirmed Rules

- Rule: Keep gameplay modes and page handlers in `ok_tasks/`, using the custom-task loading path.
  Evidence: `src/config.py` enables `custom_tasks`; `SortieMode.py`, `ChaosMode.py`, and `StoryMode.py` live under `ok_tasks/` while the built-in list contains only `MyOneTimeTask` and `DiagnosisTask`.
  Reuse: existing mode classes and `utils.py`/`utils_<mode>.py` modules.
  Avoid: registering a gameplay mode as an unrelated built-in task or creating a parallel handler framework.

- Rule: Preserve one-frame OCR dispatch and ordered handler priority.
  Evidence: each gameplay mode populates `self.all_texts` then iterates `PAGE_HANDLERS`; all three handler modules expose an ordered registry. Commit `733f5ee` changes a return value to preserve later handling.
  Reuse: `task.all_texts`, `find_box_at_point`, `find_text`, and the existing registries.
  Avoid: repeated full-screen OCR inside every handler or returning `True` without consuming the current screen.

- Rule: Normalize OCR and configuration before matching, and map server terminology through the shared language boundary.
  Evidence: mode `_ocr_and_simplify` methods; `utils.py:_get_config_value` and `_get_game_text`; `assets/game_text_map/zh_tw.py`; commits `da8e254` and `d06c55d` fix the same normalization class of defect.
  Reuse: `_simplify_texts`, `_get_config_value`, `_get_game_text`, and language map files.
  Avoid: raw Traditional-Chinese comparisons or local one-off conversion logic.

- Rule: Preserve persisted gameplay configuration keys and use the shared import/export flow.
  Evidence: `SortieMode.py` and `ChaosMode.py` use `default_config` plus `config_io` callbacks; `config_io.py` serializes keys and preserves underscore-prefixed state.
  Reuse: `make_export_callback` and `make_import_callback`.
  Avoid: renaming a stored setting without migration.

- Rule: Treat tagged CI as the normal release path.
  Evidence: `.github/workflows/build.yml` triggers on `v*`, runs tests, and packages with PyAppify; `pyappify.yml` pins Python 3.12.
  Reuse: `$deploy`, `run_tests.ps1`, and CI packaging.
  Avoid: changing `src/config.py` version solely to produce a tag build.

## Candidate Rules

- Candidate: Make the manual PyInstaller command in `BUILD.md` the release source of truth.
  Evidence: `BUILD.md` describes PyInstaller, but CI packages through PyAppify.
  Needs confirmation: whether manual local packages remain a supported release channel.

## Generation Notes

1. Start a page feature by locating the closest shared or mode-specific handler.
2. Reuse the current-frame, normalized-text, and persisted-config helpers.
3. Add the handler at its intended priority and validate the behavior with the existing unittest entry point.
4. Use project-conventions for repository-specific context and compose the existing generic skills instead of copying them.
