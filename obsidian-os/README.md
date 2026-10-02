# Claude OS — Obsidian Command Center

Implementation of the **"Claude Code × Obsidian Agentic OS"** workflow (Chase AI,
pub. 2026-08-15) adapted to this machine. Based on the full video script at
`~/Downloads/Video Script_ Claude Code x Obsidian Agentic OS.md`.

The video describes four pillars. This repo implements three; local voice is
deferred (needs GPU/hardware choices and invasive local installs).

| Pillar | Status | Where |
|---|---|---|
| 1. Memory layer (Karpathy raw/wiki/output + index map) | ✅ Built | `memory/` → deployed to `<vault>/Claude Code/` |
| 2. Skills & automation backbone | ✅ Built (3 skills from log analysis) | `../skills/` → `~/.claude/skills/` |
| 3. Custom dashboard plugin | ✅ Scaffold (working, iterate from here) | `plugin/claude-command-center/` → `<vault>/.obsidian/plugins/` |
| 4. Local voice (whisper → Haiku → Kokoro) | ⏸ Deferred | not in this repo |
| (bonus) Session export to Obsidian | ✅ Built | `../scripts/` (not in the video, useful complement) |

## 1. Memory layer

Karpathy's pattern: information flows **`raw/` → `wiki/` → `output/`**, and every
folder has an `index.md` "table of contents". The point is a **navigation map**
for Claude (fewer tokens, faster answers) — not "graph RAG". The map lives in
`Claude Code/CLAUDE.md`; a small `<vault>/CLAUDE.md` pointer makes it
auto-discovered when Claude Code opens in the vault.

## 2. Skills backbone

Scaffolded from real logs (see `LOG-ANALYSIS.md`):

- **`skripsi-latex`** — LaTeX thesis writing, PPKI compliance, consistency checks.
- **`slr-review`** — Systematic Literature Review (PRISMA 2020 / APA 7).
- **`sumber-cek`** — source-verified Q&A in Indonesian.

Per the video: keep as skills first, verify outputs are consistent, then promote
the worthy ones to scheduled **automations** (use the `/schedule` skill).

## 3. Dashboard plugin

A minimal but working Obsidian plugin (plain JS, no build) that reads live data
from `~/.claude`:

- **Usage:** 5h / 7d rate-limit bars (`usage-cache.json`) + session/message/token
  totals (`stats-cache.json`).
- **Exported sessions:** note count in `Claude Code/Sessions`.
- **Skills:** each `~/.claude/skills/*` as a button that copies `/<name>`.

It's a starting point. To take it further the way the video does, use Claude
Design for mockups and the **Hot Reload** community plugin for live iteration.

## Install / update everything

```bash
# memory + plugin + skills (+ root pointer), idempotent:
python3 obsidian-os/install_obsidian_os.py
# options:
python3 obsidian-os/install_obsidian_os.py --vault "/path/to/Vault"
python3 obsidian-os/install_obsidian_os.py --no-root-pointer
python3 obsidian-os/install_obsidian_os.py --uninstall   # removes plugin only
```

Then in Obsidian: reload (**Cmd+R**) and open **Claude Command Center** from the
left ribbon or the command palette.

Safety: memory templates never overwrite existing files; the `CLAUDE.md` map and
any existing root `CLAUDE.md` are backed up before changes; uninstall leaves your
notes/skills untouched.

## Not included (deferred)

**Local voice** (faster-whisper → Haiku 4.5 router → Kokoro TTS, global hotkey).
It depends on your GPU and requires installing local models and granting mic/
hotkey permissions — out of scope for an automated setup. Can be added later as a
step-by-step guide + scripts.
