#!/usr/bin/env python3
"""Deploy the Claude OS (memory layer + dashboard plugin + skills) into place.

Idempotent and conservative:
  * Memory templates are copied into "<vault>/Claude Code/" but NEVER overwrite a
    file that already exists (your edits are safe). Only the CLAUDE.md map is
    refreshed, after backing up any existing copy.
  * The dashboard plugin is copied into "<vault>/.obsidian/plugins/..." and
    enabled in community-plugins.json (code is always overwritten to update it).
  * Skills are copied into "~/.claude/skills/<name>/" (overwritten to update).
  * A root "<vault>/CLAUDE.md" pointer is created only if none exists
    (disable with --no-root-pointer).

Usage:
  install_obsidian_os.py [--vault PATH] [--no-root-pointer] [--uninstall]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
MEMORY_SRC = HERE / "memory"
PLUGIN_SRC = HERE / "plugin" / "claude-command-center"
SKILLS_SRC = REPO_ROOT / "skills"

CLAUDE_DIR = Path.home() / ".claude"
SKILLS_DEST = CLAUDE_DIR / "skills"
DEFAULT_VAULT = os.environ.get(
    "CLAUDE_OBSIDIAN_VAULT", str(Path.home() / "Documents" / "Obsidian")
)
PLUGIN_ID = "claude-command-center"
OS_FOLDER = "Claude Code"

ROOT_POINTER = """# CLAUDE.md — Vault root

Peta & aturan navigasi vault ada di **[[Claude Code/CLAUDE.md]]**.
Claude Code: baca file itu lebih dulu, lalu `index.md` tiap folder.
"""


def backup(p: Path) -> Path | None:
    if not p.exists():
        return None
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = p.with_name(p.name + f".bak-{stamp}")
    shutil.copyfile(p, dest)
    return dest


def copy_tree_no_overwrite(src: Path, dst: Path) -> list[Path]:
    created = []
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            if item.name == "CLAUDE.md":
                continue  # handled separately (refreshed w/ backup)
            if target.exists():
                continue  # never clobber user content
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target)
            created.append(target)
    return created


def deploy_memory(vault: Path) -> None:
    os_dir = vault / OS_FOLDER
    os_dir.mkdir(parents=True, exist_ok=True)
    created = copy_tree_no_overwrite(MEMORY_SRC, os_dir)
    print(f"✓ memory layer: {len(created)} new file(s) under {os_dir}")

    # Refresh the navigation map (back up any existing one first).
    map_dst = os_dir / "CLAUDE.md"
    bak = backup(map_dst)
    if bak:
        print(f"  • backed up existing map -> {bak.name}")
    shutil.copyfile(MEMORY_SRC / "CLAUDE.md", map_dst)
    print(f"  • navigation map -> {map_dst}")


def deploy_plugin(vault: Path) -> None:
    dst = vault / ".obsidian" / "plugins" / PLUGIN_ID
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "main.js", "styles.css"):
        shutil.copyfile(PLUGIN_SRC / name, dst / name)
    print(f"✓ plugin installed -> {dst}")

    # Enable in community-plugins.json
    cfg = vault / ".obsidian" / "community-plugins.json"
    enabled = []
    if cfg.exists():
        try:
            enabled = json.loads(cfg.read_text())
        except json.JSONDecodeError:
            enabled = []
    if PLUGIN_ID not in enabled:
        enabled.append(PLUGIN_ID)
        cfg.write_text(json.dumps(enabled, indent=2) + "\n")
        print(f"  • enabled in {cfg.name}")
    else:
        print("  • already enabled")


def deploy_skills() -> None:
    SKILLS_DEST.mkdir(parents=True, exist_ok=True)
    count = 0
    for skill_dir in sorted(SKILLS_SRC.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        dest = SKILLS_DEST / skill_dir.name
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(skill_file, dest / "SKILL.md")
        count += 1
        print(f"  • skill -> {dest}")
    print(f"✓ {count} skill(s) installed into {SKILLS_DEST}")


def deploy_root_pointer(vault: Path) -> None:
    p = vault / "CLAUDE.md"
    if p.exists():
        print(f"• root CLAUDE.md already exists — left untouched ({p})")
        return
    p.write_text(ROOT_POINTER)
    print(f"✓ root pointer created -> {p}")


def uninstall(vault: Path) -> None:
    plug = vault / ".obsidian" / "plugins" / PLUGIN_ID
    if plug.exists():
        shutil.rmtree(plug)
        print(f"✓ removed plugin {plug}")
    cfg = vault / ".obsidian" / "community-plugins.json"
    if cfg.exists():
        try:
            enabled = json.loads(cfg.read_text())
            if PLUGIN_ID in enabled:
                enabled.remove(PLUGIN_ID)
                cfg.write_text(json.dumps(enabled, indent=2) + "\n")
                print(f"✓ disabled plugin in {cfg.name}")
        except json.JSONDecodeError:
            pass
    print("Note: memory notes, skills, and exported sessions were left in place.")
    print("      Remove them manually if you want them gone.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    ap.add_argument("--no-root-pointer", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser()
    if not vault.exists():
        print(f"! vault not found: {vault}", file=sys.stderr)
        return 1

    if args.uninstall:
        uninstall(vault)
        return 0

    print(f"Vault: {vault}\n")
    deploy_memory(vault)
    deploy_plugin(vault)
    deploy_skills()
    if not args.no_root_pointer:
        deploy_root_pointer(vault)
    print("\nDone. In Obsidian: reload (Cmd+R) or toggle the plugin, then open "
          "'Claude Command Center' from the ribbon or command palette.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
