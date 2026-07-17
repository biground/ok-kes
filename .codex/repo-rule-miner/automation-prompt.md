Use $repo-rule-miner in /Volumes/ExtremeSSD/WorkSpace/ok-kes.

Goal:
Incrementally analyze this repository, discover team coding conventions, and synthesize repository-local Codex guidance. Continue from existing progress if present. Do not rely on previous chat history.

Required loop:
1. Work in /Volumes/ExtremeSSD/WorkSpace/ok-kes.
2. Run:
   python3 "/Users/biground/.codex/skills/repo-rule-miner/scripts/repo_rule_miner.py" status --repo "/Volumes/ExtremeSSD/WorkSpace/ok-kes"
3. If the miner has not been initialized, run:
   python3 "/Users/biground/.codex/skills/repo-rule-miner/scripts/repo_rule_miner.py" init --repo "/Volumes/ExtremeSSD/WorkSpace/ok-kes"
4. Read .codex/repo-rule-miner/progress.md and the next pending batch under .codex/repo-rule-miner/batches/.
5. Analyze only that next pending batch unless progress says synthesis is ready.
6. Record evidence-backed findings under .codex/repo-rule-miner/findings/.
7. Mark the batch complete with:
   python3 "/Users/biground/.codex/skills/repo-rule-miner/scripts/repo_rule_miner.py" complete-batch --repo "/Volumes/ExtremeSSD/WorkSpace/ok-kes" --batch-id "<BATCH_ID>" --summary "<one sentence summary>"
8. When all batches are complete, synthesize:
   - .codex/AGENTS.md
   - .codex/skills/project-conventions/SKILL.md
   - .codex/skills/project-conventions/references/conventions.md
9. If synthesis is already complete, report completion and make no changes.

Rules:
- Preserve user changes and existing .codex files.
- Do not scan node_modules, .git, library, temp, build, or dist.
- Only promote conventions to mandatory rules when evidence supports them.
- Keep progress.md up to date every run.
