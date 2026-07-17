# batch-000

Status: pending

## Purpose

Analyze these files for reusable project conventions. Record evidence-backed findings before marking the batch complete.

## Bucket Mix

- repo-rules-docs: 11
- source-ui: 1
- tests: 1
- other-text: 35

## Files

- `.agents/skills/deploy/SKILL.md` (4561 bytes, repo-rules-docs)
- `.agents/skills/ok-script-codegen/SKILL.md` (8220 bytes, repo-rules-docs)
- `.agents/skills/ok-script-i18n/SKILL.md` (3610 bytes, repo-rules-docs)
- `.agents/skills/ok-script-tasks/SKILL.md` (4082 bytes, repo-rules-docs)
- `.agents/skills/ok-script-tasks/references/task-api.md` (5766 bytes, repo-rules-docs)
- `.agents/skills/ok-script-tasks/references/templates.md` (4936 bytes, repo-rules-docs)
- `.agents/skills/use-local-venv/SKILL.md` (1518 bytes, repo-rules-docs)
- `BUILD.md` (3793 bytes, repo-rules-docs)
- `README.md` (7191 bytes, repo-rules-docs)
- `README_en.md` (7773 bytes, repo-rules-docs)
- `prompt/cn.md` (0 bytes, repo-rules-docs)
- `src/ui/MyTab.py` (1489 bytes, source-ui)
- `tests/TestMain.py` (10592 bytes, tests)
- `.agents/skills/deploy/agents/openai.yaml` (205 bytes, other-text)
- `.agents/skills/deploy/scripts/next_tag.py` (3596 bytes, other-text)
- `.agents/skills/ok-script-codegen/agents/openai.yaml` (213 bytes, other-text)
- `.agents/skills/ok-script-i18n/agents/openai.yaml` (192 bytes, other-text)
- `.agents/skills/ok-script-i18n/scripts/task_i18n_helper.py` (5389 bytes, other-text)
- `.agents/skills/ok-script-tasks/agents/openai.yaml` (189 bytes, other-text)
- `.agents/skills/use-local-venv/agents/openai.yaml` (268 bytes, other-text)
- `.github/workflows/build.yml` (4111 bytes, other-text)
- `.github/workflows/mirrorchyan_release_note.yml` (607 bytes, other-text)
- `.github/workflows/mirrorchyan_uploading.yml` (661 bytes, other-text)
- `.gitignore` (664 bytes, other-text)
- `.update_repo_gitignore` (52 bytes, other-text)
- `deploy.txt` (86 bytes, other-text)
- `main.py` (743 bytes, other-text)
- `main_debug.py` (153 bytes, other-text)
- `ok_tasks/ChaosMode.py` (3276 bytes, other-text)
- `ok_tasks/GetMengbian.py` (1254 bytes, other-text)
- `ok_tasks/SortieMode.py` (3379 bytes, other-text)
- `ok_tasks/StoryMode.py` (1821 bytes, other-text)
- `ok_tasks/TestTrigger.py` (7875 bytes, other-text)
- `ok_tasks/assets/coco_annotations.json` (6894 bytes, other-text)
- `ok_tasks/assets/game_text_map/__init__.py` (317 bytes, other-text)
- `ok_tasks/assets/game_text_map/zh_tw.py` (1550 bytes, other-text)
- `ok_tasks/config_io.py` (3860 bytes, other-text)
- `ok_tasks/utils.py` (53530 bytes, other-text)
- `ok_tasks/utils_chaos.py` (11931 bytes, other-text)
- `ok_tasks/utils_sortie.py` (42255 bytes, other-text)
- `ok_tasks/utils_story.py` (4065 bytes, other-text)
- `pyappify.yml` (489 bytes, other-text)
- `requirements.txt` (1639 bytes, other-text)
- `src/config.py` (6128 bytes, other-text)
- `src/globals.py` (187 bytes, other-text)
- `src/tasks/MyBaseTask.py` (152 bytes, other-text)
- `src/tasks/MyOneTimeTask.py` (6318 bytes, other-text)
- `src/tasks/MyTriggerTask.py` (429 bytes, other-text)

## Analysis Checklist

- Identify base classes, shared helpers, lifecycle conventions, and naming rules.
- Prefer repeated evidence over one-off local choices.
- Record candidate rules separately from confirmed rules.
- Note generation steps for new files when a pattern is clear.
