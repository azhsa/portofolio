#!/usr/bin/env python3
"""Export Claude Code terminal sessions and memory into an Obsidian vault.

Claude Code stores every session as a JSONL transcript under
``~/.claude/projects/<encoded-path>/<session-id>.jsonl``. This script converts
those transcripts into clean, readable, linkable Markdown notes inside an
Obsidian vault, and also copies the CLAUDE.md "memory" files it finds.

Usage
-----
  # Export a single session from a hook (reads JSON on stdin):
  claude_to_obsidian.py --from-hook

  # Export one session explicitly:
  claude_to_obsidian.py --session <session-id>
  claude_to_obsidian.py --transcript /path/to/session.jsonl

  # Backfill every existing session:
  claude_to_obsidian.py --all

The destination vault is resolved in this order:
  1. --vault <path>
  2. $CLAUDE_OBSIDIAN_VAULT
  3. the DEFAULT_VAULT constant below.

Notes land in "<vault>/Claude Code/Sessions" and memory files in
"<vault>/Claude Code/Memory". The script is idempotent: re-running on the same
session overwrites that session's note in place.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import shutil
import datetime as dt
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Set CLAUDE_OBSIDIAN_VAULT (or pass --vault) to point at your vault.
DEFAULT_VAULT = os.environ.get(
    "CLAUDE_OBSIDIAN_VAULT", str(Path.home() / "Documents" / "Obsidian")
)
SUBFOLDER = "Claude Code"
SESSIONS_DIRNAME = "Sessions"
MEMORY_DIRNAME = "Memory"

PROJECTS_DIR = Path.home() / ".claude" / "projects"
GLOBAL_MEMORY = Path.home() / ".claude" / "CLAUDE.md"
LOG_FILE = Path.home() / ".claude" / "obsidian-sync.log"

# Size caps so a 60 MB transcript does not become an unreadable note.
MAX_TEXT = 40_000       # assistant/user plain text per message
MAX_THINKING = 4_000    # reasoning block
MAX_TOOL_INPUT = 1_500  # tool_use input
MAX_TOOL_RESULT = 2_000 # tool_result content

# Characters Obsidian/macOS dislike in filenames.
FILENAME_BAD = re.compile(r'[\\/:*?"<>|#^\[\]]')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    ts = dt.datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {msg}"
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass
    # Also echo to stderr for interactive/backfill runs.
    print(line, file=sys.stderr)


def resolve_vault(cli_vault: str | None) -> Path:
    vault = cli_vault or os.environ.get("CLAUDE_OBSIDIAN_VAULT") or DEFAULT_VAULT
    return Path(vault).expanduser()


def truncate(text: str, limit: int) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n\n*… [truncated {omitted:,} characters]*"


def sanitize_filename(name: str) -> str:
    name = FILENAME_BAD.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:90] if len(name) > 90 else name


def yaml_quote(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_ts(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def iter_records(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_blocks(role: str, content) -> list[str]:
    """Turn a message's content (str or list of blocks) into Markdown lines."""
    out: list[str] = []
    if isinstance(content, str):
        text = content.strip()
        if text:
            out.append(truncate(text, MAX_TEXT))
        return out

    if not isinstance(content, list):
        return out

    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            text = (block.get("text") or "").strip()
            if text:
                out.append(truncate(text, MAX_TEXT))
        elif btype == "thinking":
            think = (block.get("thinking") or "").strip()
            if think:
                out.append(
                    "> [!note]- 💭 Thinking\n"
                    + "\n".join("> " + ln for ln in truncate(think, MAX_THINKING).splitlines())
                )
        elif btype == "tool_use":
            name = block.get("name", "tool")
            tool_input = json.dumps(block.get("input", {}), ensure_ascii=False, indent=2)
            out.append(
                f"> [!info]- 🔧 Tool call: `{name}`\n"
                + "> ```json\n"
                + "\n".join("> " + ln for ln in truncate(tool_input, MAX_TOOL_INPUT).splitlines())
                + "\n> ```"
            )
        elif btype == "tool_result":
            res = block.get("content")
            if isinstance(res, list):
                parts = []
                for r in res:
                    if isinstance(r, dict) and r.get("type") == "text":
                        parts.append(r.get("text", ""))
                res = "\n".join(parts)
            res = str(res or "").strip()
            if res:
                is_err = block.get("is_error")
                label = "⚠️ Tool result (error)" if is_err else "📄 Tool result"
                out.append(
                    f"> [!quote]- {label}\n"
                    + "> ```\n"
                    + "\n".join("> " + ln for ln in truncate(res, MAX_TOOL_RESULT).splitlines())
                    + "\n> ```"
                )
    return out


def build_note(path: Path) -> dict | None:
    """Parse one transcript file into a note dict, or None if nothing useful."""
    title = None
    session_id = path.stem
    cwd = None
    git_branch = None
    version = None
    first_ts = None
    last_ts = None
    n_user = 0
    n_assistant = 0
    n_tools = 0
    body: list[str] = []
    summary: str | None = None
    files: set[str] = set()

    for rec in iter_records(path):
        rtype = rec.get("type")

        if rtype in ("ai-title", "agent-name"):
            title = title or rec.get("aiTitle") or rec.get("agentName")
            continue
        if rtype == "summary":
            title = title or rec.get("summary")
            continue

        if rtype not in ("user", "assistant"):
            continue

        msg = rec.get("message", {})
        if not isinstance(msg, dict):
            continue

        ts = parse_ts(rec.get("timestamp"))
        if ts:
            first_ts = first_ts or ts
            last_ts = ts
        cwd = rec.get("cwd", cwd)
        git_branch = rec.get("gitBranch", git_branch)
        version = rec.get("version", version)

        rendered = render_blocks(rtype, msg.get("content"))
        if not rendered:
            continue

        content = msg.get("content")
        if rtype == "user":
            n_user += 1
            heading = "### 👤 User"
            if summary is None:
                txt = content if isinstance(content, str) else " ".join(
                    b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
                txt = (txt or "").strip().replace("\n", " ")
                if txt and not txt.startswith("<"):
                    summary = txt[:220]
        else:
            n_assistant += 1
            heading = "### 🤖 Assistant"

        for b in (content or []):
            if isinstance(b, dict) and b.get("type") == "tool_use":
                n_tools += 1
                if b.get("name") in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
                    fp = (b.get("input") or {}).get("file_path")
                    if fp:
                        files.add(fp)

        stamp = ts.strftime("%H:%M:%S") if ts else ""
        body.append(f"{heading}  <small>{stamp}</small>\n\n" + "\n\n".join(rendered))

    if n_user == 0 and n_assistant == 0:
        return None

    if not title:
        title = f"Session {session_id[:8]}"

    return {
        "title": title,
        "session_id": session_id,
        "cwd": cwd,
        "git_branch": git_branch,
        "version": version,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "n_user": n_user,
        "n_assistant": n_assistant,
        "n_tools": n_tools,
        "summary": summary or "",
        "files": files,
        "body": body,
        "source": str(path),
    }


def write_note(note: dict, sessions_dir: Path) -> Path:
    first = note["first_ts"]
    date_str = first.strftime("%Y-%m-%d") if first else "undated"
    created = first.isoformat() if first else ""
    updated = note["last_ts"].isoformat() if note["last_ts"] else ""
    sid8 = note["session_id"][:8]

    fname = sanitize_filename(f"{date_str} — {note['title']} ({sid8})") + ".md"
    dest = sessions_dir / fname

    project = ""
    if note["cwd"]:
        project = Path(note["cwd"]).name

    fm = [
        "---",
        f"title: {yaml_quote(note['title'])}",
        f"session_id: {note['session_id']}",
        f"project: {yaml_quote(project)}",
        f"cwd: {yaml_quote(note['cwd'] or '')}",
        f"git_branch: {yaml_quote(note['git_branch'] or '')}",
        f"created: {created}",
        f"updated: {updated}",
        f"messages_user: {note['n_user']}",
        f"messages_assistant: {note['n_assistant']}",
        f"tool_calls: {note['n_tools']}",
        f"summary: {yaml_quote(note['summary'])}",
        f"files_touched: {yaml_quote(', '.join(sorted(note['files'])[:20]))}",
        f"claude_version: {yaml_quote(note['version'] or '')}",
        "tags:",
        "  - claude-code",
        "  - session",
    ]
    if project:
        fm.append(f"  - project/{sanitize_filename(project).replace(' ', '-')}")
    fm.append("---")

    header = [
        f"# {note['title']}",
        "",
        f"> **Project:** {project or '—'}  ·  **Branch:** {note['git_branch'] or '—'}  "
        f"·  **Created:** {date_str}",
        f"> **Session:** `{note['session_id']}`",
        f"> **Messages:** {note['n_user']} user / {note['n_assistant']} assistant  "
        f"·  **Tool calls:** {note['n_tools']}",
        "",
    ]
    if note["summary"]:
        header += [f"**Ringkasan awal:** {note['summary']}", ""]
    header += ["---", ""]

    content = "\n".join(fm) + "\n\n" + "\n".join(header) + "\n\n---\n\n".join(note["body"]) + "\n"
    dest.write_text(content, encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# Compact session index (the token-saving layer)
# ---------------------------------------------------------------------------
def parse_frontmatter(md: Path) -> dict:
    """Minimal YAML front-matter reader for the keys we write ourselves."""
    out: dict = {}
    try:
        text = md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    if not text.startswith("---"):
        return out
    end = text.find("\n---", 3)
    if end == -1:
        return out
    for line in text[3:end].splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
            val = val[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        out[key.strip()] = val
    return out


def write_index(sessions_dir: Path) -> Path | None:
    """Rebuild _INDEX.md: one compact summary row per exported session.

    This is what a new session should read to recall past work cheaply,
    instead of re-deriving context or reopening full transcripts.
    """
    rows = []
    for md in sessions_dir.glob("*.md"):
        if md.name.startswith("_"):
            continue
        fm = parse_frontmatter(md)
        if not fm:
            continue
        fm["_file"] = md.name
        rows.append(fm)
    if not rows:
        return None

    rows.sort(key=lambda r: r.get("created", ""), reverse=True)

    lines = [
        "---",
        "title: Session Index",
        "type: index",
        "tags: [claude-code, index]",
        "---",
        "",
        "# 🗂️ Indeks Sesi Claude Code",
        "",
        f"> Ringkas, hemat token. {len(rows)} sesi. Dibuat ulang otomatis tiap "
        "sesi berakhir. Baca ini dulu untuk mengingat pekerjaan lampau; buka "
        "transkrip lengkap hanya bila perlu.",
        "",
        "| Tanggal | Judul | Proyek | Pesan | Ringkasan |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        date = (r.get("created", "") or "")[:10] or "—"
        title = r.get("title", "—")
        link = f"[[{r['_file'][:-3]}\\|{title}]]"
        proj = r.get("project", "") or "—"
        msgs = f"{r.get('messages_user','?')}/{r.get('messages_assistant','?')}"
        summ = (r.get("summary", "") or "").replace("|", "\\|")
        if len(summ) > 120:
            summ = summ[:120] + "…"
        lines.append(f"| {date} | {link} | {proj} | {msgs} | {summ} |")

    dest = sessions_dir / "_INDEX.md"
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def session_start_context(vault: Path) -> str:
    """Short pointer injected at SessionStart so new sessions use the memory."""
    base = vault / SUBFOLDER
    return (
        "🧠 Memory Obsidian aktif (hemat token). Sebelum menanyakan ulang "
        "konteks atau mengeksplorasi dari nol, konsultasikan dulu:\n"
        f"- Indeks sesi lampau (ringkas): {base / SESSIONS_DIRNAME / '_INDEX.md'}\n"
        f"- Peta & aturan navigasi vault: {base / 'CLAUDE.md'}\n"
        "Buka transkrip penuh di folder Sessions/ hanya bila benar-benar perlu."
    )


# ---------------------------------------------------------------------------
# Memory export
# ---------------------------------------------------------------------------
def export_memory(memory_dir: Path, cwds: set[str]) -> list[Path]:
    written: list[Path] = []
    memory_dir.mkdir(parents=True, exist_ok=True)

    if GLOBAL_MEMORY.exists():
        dest = memory_dir / "GLOBAL — CLAUDE.md"
        shutil.copyfile(GLOBAL_MEMORY, dest)
        written.append(dest)

    for cwd in sorted(c for c in cwds if c):
        src = Path(cwd) / "CLAUDE.md"
        if src.exists():
            dest = memory_dir / f"{sanitize_filename(Path(cwd).name)} — CLAUDE.md"
            shutil.copyfile(src, dest)
            written.append(dest)
    return written


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------
def find_transcript_by_session(session_id: str) -> Path | None:
    if not PROJECTS_DIR.exists():
        return None
    for p in PROJECTS_DIR.rglob(f"{session_id}.jsonl"):
        return p
    return None


def all_transcripts() -> list[Path]:
    if not PROJECTS_DIR.exists():
        return []
    return sorted(PROJECTS_DIR.rglob("*.jsonl"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def export_one(path: Path, sessions_dir: Path) -> tuple[Path | None, str | None]:
    note = build_note(path)
    if not note:
        return None, note_cwd(path)
    dest = write_note(note, sessions_dir)
    return dest, note["cwd"]


def note_cwd(path: Path) -> str | None:
    for rec in iter_records(path):
        if rec.get("type") in ("user", "assistant") and rec.get("cwd"):
            return rec["cwd"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--from-hook", action="store_true",
                   help="Read a Claude Code hook JSON payload from stdin.")
    g.add_argument("--session", help="Export a single session by id.")
    g.add_argument("--transcript", help="Export a single transcript file path.")
    g.add_argument("--all", action="store_true", help="Backfill every session.")
    g.add_argument("--session-start", action="store_true",
                   help="Print SessionStart context (points new sessions at the memory).")
    ap.add_argument("--vault", help="Destination Obsidian vault path.")
    ap.add_argument("--no-memory", action="store_true", help="Skip CLAUDE.md memory export.")
    args = ap.parse_args()

    vault = resolve_vault(args.vault)
    sessions_dir = vault / SUBFOLDER / SESSIONS_DIRNAME
    memory_dir = vault / SUBFOLDER / MEMORY_DIRNAME

    # SessionStart: emit a tiny context pointer as JSON, then exit (no export).
    if args.session_start:
        ctx = session_start_context(vault)
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": ctx,
        }}))
        return 0

    if not vault.exists():
        log(f"ERROR: vault not found: {vault}")
        return 0  # never break the session

    sessions_dir.mkdir(parents=True, exist_ok=True)

    targets: list[Path] = []

    if args.from_hook:
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        tp = payload.get("transcript_path")
        sid = payload.get("session_id")
        if tp and Path(tp).exists():
            targets = [Path(tp)]
        elif sid:
            found = find_transcript_by_session(sid)
            if found:
                targets = [found]
        if not targets:
            log(f"from-hook: no transcript resolved (session_id={sid})")
            return 0
    elif args.session:
        found = find_transcript_by_session(args.session)
        if not found:
            log(f"session not found: {args.session}")
            return 0
        targets = [found]
    elif args.transcript:
        p = Path(args.transcript)
        if not p.exists():
            log(f"transcript not found: {p}")
            return 0
        targets = [p]
    elif args.all:
        targets = all_transcripts()
        if not targets:
            log("no transcripts found to backfill")
    else:
        ap.print_help()
        return 1

    cwds: set[str] = set()
    exported = 0
    for path in targets:
        try:
            dest, cwd = export_one(path, sessions_dir)
            if cwd:
                cwds.add(cwd)
            if dest:
                exported += 1
                log(f"exported {path.name} -> {dest.name}")
        except Exception as exc:  # never break the session on one bad file
            log(f"ERROR exporting {path}: {exc!r}")

    if not args.no_memory:
        try:
            mem = export_memory(memory_dir, cwds)
            if mem:
                log(f"memory: {len(mem)} file(s) exported")
        except Exception as exc:
            log(f"ERROR exporting memory: {exc!r}")

    # Always rebuild the compact index from all exported notes (token-saving layer).
    try:
        idx = write_index(sessions_dir)
        if idx:
            log(f"index rebuilt -> {idx.name}")
    except Exception as exc:
        log(f"ERROR building index: {exc!r}")

    log(f"done: {exported}/{len(targets)} session note(s) written to {sessions_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
