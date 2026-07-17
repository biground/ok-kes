---
name: project-conventions
description: Follow ok-kes conventions for image-recognition game automation. Use when modifying a mode or page handler, OCR or Traditional-Chinese text matching, task configuration/import-export, custom files under ok_tasks, tests, packaging, or a release in this repository.
---

# ok-kes Project Conventions

Use the existing focused skills as needed:

- `$ok-script-tasks` for ok-script task lifecycle and APIs.
- `$ok-script-i18n` for gettext catalogs.
- `$use-local-venv` before Python commands.
- `$deploy` for a requested release.

## Core Automation Flow

- Put gameplay automation in `ok_tasks/`; `src/config.py` enables `custom_tasks` and does not register the gameplay modes as built-ins.
- Each mode performs one simplified OCR scan into `task.all_texts`, then walks its module's ordered `PAGE_HANDLERS`. Handler order is behavior.
- Consume `task.all_texts` through the helpers in `utils.py`. Refresh OCR only after an action changes the view or scrolls; assign the simplified result back to `task.all_texts`.
- Return `True` only when a handler has consumed the current screen or action. Return `False` for observers and when a later handler must still act.
- When adding a mutually exclusive mode, update its `enable()` coordination with the existing gameplay modes.

## Text and Configuration

- Treat simplified Chinese as the canonical matching text. Use `_get_game_text(task, text)` for server terminology that differs after OCR normalization; add only the differing term to `ok_tasks/assets/game_text_map/`.
- Read persisted user settings with `_get_config_value` or its existing wrappers. Do not rename an existing setting key without a migration: `config_io.py` serializes those keys into user configuration files.
- Keep mode export/import buttons on the existing `make_export_callback` and `make_import_callback` path when the mode exposes shareable user configuration.

## Change Path

1. Put shared page behavior in `ok_tasks/utils.py`; keep a mode-only handler in its `utils_<mode>.py` module.
2. Reuse coordinate, OCR, config, and language helpers before adding new logic.
3. Add the handler at the intended priority in that mode's `PAGE_HANDLERS`, then inspect adjacent handlers for conflicts.
4. Update a text map or configuration default only when the behavior needs it.
5. Run the focused unittest path after source changes.

## Verification and Releases

- Use the repository interpreter selected by `$use-local-venv`, then run `python -m unittest tests/TestMain.py` (or `./run_tests.ps1` on Windows) for the existing test entry point.
- A `v*` tag triggers the Windows Python 3.12 CI build and PyAppify packaging. Do not manually bump `src/config.py`'s version solely for that release path.

Read [references/conventions.md](references/conventions.md) before changing handler priority, text normalization, configuration persistence, or packaging behavior.
