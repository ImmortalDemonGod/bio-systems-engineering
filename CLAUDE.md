# CLAUDE.md — Bio-Systems Engineering

Operational notes for Claude working on this project. Read before making changes.

---

## Commit workflow — always use `aiv`

Raw `git commit` requires GPG pinentry GUI (not available in Claude Code terminal). Always use `aiv commit`:

```bash
aiv commit <file> \
  -m "type(scope): message" \
  -t R0 \                          # R0 = trivial/docs, R1 = standard fix
  -c "Falsifiable claim about the change" \
  -i "https://github.com/..." \    # MUST be a URL — file paths rejected
  --requirement "which requirement this satisfies" \
  -r "why this tier" \
  -s "one-line summary" \
  [--skip-checks --skip-reason "markdown only"]   # R0 only
```

For multi-file change contexts: `aiv begin <name>` → commits → `echo "Y" | aiv close`.

---

## Cron vs launchd — critical

The cron daemon has Full Disk Access on macOS. **launchd agents do not.**

- **All scripts that read `/Volumes/Totallynotaharddrive/`** must be scheduled via `crontab`, not launchd.
- The launchd agent `com.openclaw.daily-running-brief` was broken for this reason — replaced with cron.
- Current crontab entries: wellness-sync (6:43am) + daily running brief (20:00).

---

## `Path(__file__)` path resolution — do not move scripts

`daily_running_brief.py` computes all output paths via `WORKSPACE = Path(__file__).parent.parent`.
This must resolve to `~/.openclaw/workspace/`. The script must run from its canonical location
`~/.openclaw/workspace/scripts/daily_running_brief.py` — do not run it from the biosystems path directly.

`run_brief.sh` auto-syncs from biosystems before each run:
```
/Volumes/.../bio-systems-engineering/daily_running_brief/daily_running_brief.py
     ↓  (cp at run time by run_brief.sh)
~/.openclaw/workspace/scripts/daily_running_brief.py   ← always current, WORKSPACE resolves correctly
```

---

## Two-location script pattern

`daily_running_brief.py` lives in biosystems (source of truth) but runs from openclaw (path-dependent).
`run_brief.sh` copies it automatically. **Never manually copy this file** — edit biosystems only.

---

## GitHub PR size limit

GitHub silently shows "0 files changed" when a PR diff exceeds ~3,000 files or tens of MB.
If a PR shows this, check whether dev artifacts were accidentally committed (`.cache/`, `data/processed/`).
Fix: `git rm --cached` the files, update `.gitignore`, recommit with `--no-verify` if the AIV hook OOMs.

---

## AIV pre-commit hook OOM

When 3,800+ files are staged, the AIV hook's `_write_safety_snapshot()` runs `git diff --cached`
and OOM-kills before completing. Use `--no-verify` only with explicit user approval.

---

## Mock `isinstance` in tests

For FIT parser tests, `isinstance(frame, fitdecode.FitDataMessage)` returns False with bare `MagicMock()`.
Must use `MagicMock(spec=fitdecode.FitDataMessage)` to pass the isinstance check in `parse_fit()`.

---

## Open issues

See `docs/PUBLICATION_CHECKLIST.md` for paper readiness blockers.
See known issues in project memory at `~/.claude/projects/.../memory/project_biosystems_overview.md`.
