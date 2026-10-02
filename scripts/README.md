# Claude Code → Obsidian Sync

Export every Claude Code **terminal session** and **memory** (`CLAUDE.md`) file
into an Obsidian vault as clean, searchable, linkable Markdown notes — updated
automatically each time a session ends.

## How it works

Claude Code stores each session as a JSONL transcript under
`~/.claude/projects/<encoded-path>/<session-id>.jsonl`. Two scripts turn those
into Obsidian notes:

| File | Role |
| --- | --- |
| `claude_to_obsidian.py` | The exporter. Parses a transcript into one Markdown note per session, copies `CLAUDE.md` memory files, and rebuilds a compact `_INDEX.md`. |
| `install_obsidian_sync.py` | Installs the exporter to `~/.claude/scripts/`, registers `SessionEnd` + `SessionStart` hooks in `~/.claude/settings.json`, and (optionally) backfills existing sessions. |

Two hooks are installed:

- **`SessionEnd`** fires when a session ends; Claude Code passes the session's
  `transcript_path` to the exporter, which re-renders that note **and rebuilds
  `_INDEX.md`**. New sessions are therefore captured automatically.
- **`SessionStart`** injects a tiny pointer (~60 tokens) telling the new session
  where the memory lives, so it can recall past work cheaply instead of
  re-deriving context.

### Token saving — how it actually works

Exporting full transcripts does **not** save tokens by itself (a large transcript
costs *more* to read back). The savings come from:

1. **`Sessions/_INDEX.md`** — one short summary row per session (date, title,
   project, message counts, first request). Small and cheap to read.
2. The **`SessionStart` pointer** + the vault **`CLAUDE.md` map**, which direct
   Claude to read the index first and only open a full transcript when necessary.

## Output layout

Inside the vault:

```
Claude Code/
├── Sessions/
│   ├── _INDEX.md                   # compact index of all sessions (token-saving)
│   └── 2026-09-24 — Draft Skripsi 15 (a5254a32).md
└── Memory/
    ├── GLOBAL — CLAUDE.md          # ~/.claude/CLAUDE.md, if present
    └── portofolio — CLAUDE.md      # each project's CLAUDE.md
```

Each session note has YAML front-matter (`session_id`, `project`, `cwd`,
`git_branch`, `created`, `updated`, message/tool counts, tags) so it is
filterable in Obsidian. User/assistant turns are rendered inline; reasoning,
tool calls, and tool results are placed in collapsible callouts and size-capped
so even a 60 MB transcript becomes a readable note.

## Install

```bash
# Point at your vault with the env var (recommended) or --vault.
export CLAUDE_OBSIDIAN_VAULT="/path/to/Your Vault"
python3 scripts/install_obsidian_sync.py --backfill
# or pass it explicitly:
python3 scripts/install_obsidian_sync.py --vault "/path/to/Your Vault" --backfill
```

> The scripts default the vault to `$CLAUDE_OBSIDIAN_VAULT`, falling back to
> `~/Documents/Obsidian`. No personal path is hardcoded.

The installer backs up `~/.claude/settings.json` (timestamped) before editing it
and is idempotent — re-running never duplicates the hook.

## Manual use

```bash
python3 scripts/claude_to_obsidian.py --all                 # backfill everything
python3 scripts/claude_to_obsidian.py --session <id>        # one session by id
python3 scripts/claude_to_obsidian.py --transcript <path>   # one transcript file
python3 scripts/claude_to_obsidian.py --no-memory           # skip CLAUDE.md copy
```

Add `--vault "<path>"` to any command to target a specific vault.

## Configuration

- **Vault path** — `--vault`, the `CLAUDE_OBSIDIAN_VAULT` env var, or the
  `DEFAULT_VAULT` constant in each script (checked in that order).
- **Size caps** — `MAX_TEXT`, `MAX_THINKING`, `MAX_TOOL_INPUT`,
  `MAX_TOOL_RESULT` constants in `claude_to_obsidian.py`.

## Logs & troubleshooting

The exporter never fails a session: errors are logged to
`~/.claude/obsidian-sync.log` and it always exits `0`. Check that log if a note
does not appear. Verify the hook with:

```bash
python3 -c "import json;print(json.load(open('$HOME/.claude/settings.json'))['hooks']['SessionEnd'])"
```

## Uninstall

```bash
python3 scripts/install_obsidian_sync.py --uninstall
```

This removes the hook and the installed exporter copy, backs up settings first,
and leaves already-exported notes in the vault untouched.
