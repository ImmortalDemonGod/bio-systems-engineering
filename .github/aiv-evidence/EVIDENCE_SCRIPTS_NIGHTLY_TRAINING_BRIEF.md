# AIV Evidence — scripts/nightly_training_brief.py (deletion)

## Change
Deleted `scripts/nightly_training_brief.py` (586 lines, 1 commit: e9ef3ae).

## Rationale
Superseded ancestor of the canonical brief. Operational brief lives at
`~/.openclaw/workspace/scripts/daily_running_brief.py` (1909 lines),
scheduled via launchd at 20:00, and contains all capabilities of the
deleted file plus dual G/A/R, walk analysis, EF_GAP quality suppression,
wellness dual-signal, sleep debt, fitness arc, and LLM synthesis pipeline.

## Risk
R0 — deletion of dead code. No production logic altered. No tests reference
this file. No imports in the biosystems package depend on it.

## Verification
- grep -r "nightly_training_brief" src/ tests/ → 0 matches
- File had 0 importers in the codebase
