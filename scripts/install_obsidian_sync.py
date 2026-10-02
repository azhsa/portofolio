#!/usr/bin/env python3
"""Install the Claude Code -> Obsidian session/memory sync.

What it does (all idempotent):
  1. Copies the exporter to ~/.claude/scripts/claude_to_obsidian.py so the hook
     does not depend on this repo's location.
  2. Registers a SessionEnd hook in ~/.claude/settings.json that exports each
     finished session to the Obsidian vault. Existing settings are preserved and
     a timestamped backup is written first.
  3. Optionally backfills every existing session (--backfill).

Usage:
  install_obsidian_sync.py [--vault PATH] [--backfill] [--uninstall]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_SCRIPT = Path(__file__).resolve().parent / "claude_to_obsidian.py"
CLAUDE_DIR = Path.home() / ".claude"
INSTALL_DIR = CLAUDE_DIR / "scripts"
INSTALLED_SCRIPT = INSTALL_DIR / "claude_to_obsidian.py"
SETTINGS = CLAUDE_DIR / "settings.json"
DEFAULT_VAULT = os.environ.get(
    "CLAUDE_OBSIDIAN_VAULT", str(Path.home() / "Documents" / "Obsidian")
)

# Stable token used to recognize our own hook entry on re-runs / uninstall.
HOOK_MARKER = "claude_to_obsidian.py"


def load_settings() -> dict:
    if SETTINGS.exists():
        try:
            return json.loads(SETTINGS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"! {SETTINGS} is not valid JSON; aborting.", file=sys.stderr)
            sys.exit(1)
    return {}


def backup_settings() -> Path | None:
    if not SETTINGS.exists():
        return None
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = SETTINGS.with_name(f"settings.json.bak-{stamp}")
    shutil.copyfile(SETTINGS, dest)
    return dest


def end_command(vault: str) -> str:
    return f'/usr/bin/env python3 "{INSTALLED_SCRIPT}" --from-hook --vault "{vault}"'


def start_command(vault: str) -> str:
    return f'/usr/bin/env python3 "{INSTALLED_SCRIPT}" --session-start --vault "{vault}"'


def strip_our_hooks(settings: dict) -> None:
    """Remove our own hook entries from every event, so re-runs don't duplicate."""
    hooks = settings.get("hooks", {})
    for event in ("SessionEnd", "SessionStart"):
        entries = hooks.get(event)
        if not isinstance(entries, list):
            continue
        cleaned = []
        for entry in entries:
            sub = entry.get("hooks", []) if isinstance(entry, dict) else []
            sub = [h for h in sub if HOOK_MARKER not in str(h.get("command", ""))]
            if sub:
                entry["hooks"] = sub
                cleaned.append(entry)
        if cleaned:
            hooks[event] = cleaned
        else:
            hooks.pop(event, None)
    if not hooks:
        settings.pop("hooks", None)


def install(vault: str, backfill: bool) -> None:
    if not REPO_SCRIPT.exists():
        print(f"! exporter not found at {REPO_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_SCRIPT, INSTALLED_SCRIPT)
    INSTALLED_SCRIPT.chmod(0o755)
    print(f"✓ exporter installed -> {INSTALLED_SCRIPT}")

    settings = load_settings()
    bak = backup_settings()
    if bak:
        print(f"✓ settings backed up -> {bak}")

    strip_our_hooks(settings)  # avoid duplicate entries on re-run
    hooks = settings.setdefault("hooks", {})
    hooks.setdefault("SessionEnd", []).append(
        {"hooks": [{"type": "command", "command": end_command(vault)}]})
    hooks.setdefault("SessionStart", []).append(
        {"hooks": [{"type": "command", "command": start_command(vault)}]})

    SETTINGS.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    print(f"✓ SessionEnd + SessionStart hooks registered in {SETTINGS}")
    print(f"  vault: {vault}")

    if backfill:
        print("• backfilling existing sessions …")
        subprocess.run(
            [sys.executable, str(INSTALLED_SCRIPT), "--all", "--vault", vault],
            check=False,
        )


def uninstall() -> None:
    settings = load_settings()
    bak = backup_settings()
    if bak:
        print(f"✓ settings backed up -> {bak}")
    strip_our_hooks(settings)
    SETTINGS.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    print(f"✓ SessionEnd + SessionStart hooks removed from {SETTINGS}")
    if INSTALLED_SCRIPT.exists():
        INSTALLED_SCRIPT.unlink()
        print(f"✓ removed {INSTALLED_SCRIPT}")
    print("Note: exported notes in your vault were left untouched.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", default=DEFAULT_VAULT, help="Obsidian vault path.")
    ap.add_argument("--backfill", action="store_true",
                    help="Export all existing sessions after installing.")
    ap.add_argument("--uninstall", action="store_true",
                    help="Remove the hook and installed exporter.")
    args = ap.parse_args()

    if args.uninstall:
        uninstall()
    else:
        install(args.vault, args.backfill)
    return 0


if __name__ == "__main__":
    sys.exit(main())
