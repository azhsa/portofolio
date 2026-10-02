"use strict";
/*
 * Claude Command Center — a minimal Obsidian command-center panel for a
 * Claude Code OS (inspired by the "Claude Code x Obsidian Agentic OS" workflow).
 *
 * Plain CommonJS so it runs in Obsidian with no build step. Desktop only:
 * it reads JSON that Claude Code writes under ~/.claude via Node's fs.
 *
 * Panels:
 *   - Usage: 5h / 7d rate-limit bars (~/.claude/usage-cache.json) and
 *            session / message / tool totals (~/.claude/stats-cache.json).
 *   - Skills: every ~/.claude/skills/<name>/SKILL.md as a button that copies
 *            "/<name>" to the clipboard, ready to paste into Claude Code.
 *   - Sessions: count of exported notes in "Claude Code/Sessions".
 */
const { Plugin, ItemView, Notice } = require("obsidian");
const fs = require("fs");
const os = require("os");
const path = require("path");

const VIEW_TYPE = "claude-command-center";
const CLAUDE_DIR = path.join(os.homedir(), ".claude");

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    return null;
  }
}

function fmtNum(n) {
  if (n == null || isNaN(n)) return "—";
  if (n >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return String(n);
}

function fmtReset(ts) {
  if (!ts) return "";
  const ms = ts * 1000 - Date.now();
  if (ms <= 0) return "reset due";
  const h = Math.floor(ms / 3.6e6);
  const m = Math.floor((ms % 3.6e6) / 6e4);
  return h > 0 ? `resets in ${h}h ${m}m` : `resets in ${m}m`;
}

function listSkills() {
  const dir = path.join(CLAUDE_DIR, "skills");
  const out = [];
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch (e) {
    return out;
  }
  for (const ent of entries) {
    if (!ent.isDirectory()) continue;
    const skillFile = path.join(dir, ent.name, "SKILL.md");
    if (fs.existsSync(skillFile)) out.push(ent.name);
    else {
      // one level of nesting (e.g. skills/synced/<name>/SKILL.md)
      try {
        for (const sub of fs.readdirSync(path.join(dir, ent.name), { withFileTypes: true })) {
          if (sub.isDirectory() && fs.existsSync(path.join(dir, ent.name, sub.name, "SKILL.md"))) {
            out.push(sub.name);
          }
        }
      } catch (e) { /* ignore */ }
    }
  }
  return out.sort();
}

class CommandCenterView extends ItemView {
  getViewType() { return VIEW_TYPE; }
  getDisplayText() { return "Claude Command Center"; }
  getIcon() { return "bot"; }

  async onOpen() { this.render(); }
  async onClose() {}

  render() {
    const root = this.contentEl;
    root.empty();
    root.addClass("ccc-root");

    const header = root.createDiv({ cls: "ccc-header" });
    header.createEl("h3", { text: "🤖 Claude Command Center" });
    const refresh = header.createEl("button", { text: "↻", cls: "ccc-refresh" });
    refresh.setAttr("aria-label", "Refresh");
    refresh.onclick = () => this.render();

    this.renderUsage(root);
    this.renderSessions(root);
    this.renderPlugins(root);
    this.renderSkills(root);

    root.createEl("div", {
      cls: "ccc-foot",
      text: "Scaffold v0.1 — live data from ~/.claude",
    });
  }

  renderUsage(root) {
    const card = root.createDiv({ cls: "ccc-card" });
    card.createEl("div", { cls: "ccc-card-title", text: "Usage & rate limits" });

    const usage = readJson(path.join(CLAUDE_DIR, "usage-cache.json"));
    if (usage && usage.rate_limits) {
      const rl = usage.rate_limits;
      this.bar(card, "5-hour", rl.five_hour && rl.five_hour.used_percentage,
        rl.five_hour && fmtReset(rl.five_hour.resets_at));
      this.bar(card, "7-day", rl.seven_day && rl.seven_day.used_percentage,
        rl.seven_day && fmtReset(rl.seven_day.resets_at));
    } else {
      card.createEl("div", { cls: "ccc-muted", text: "No usage-cache.json found." });
    }

    const stats = readJson(path.join(CLAUDE_DIR, "stats-cache.json"));
    if (stats) {
      const grid = card.createDiv({ cls: "ccc-grid" });
      this.stat(grid, "Sessions", fmtNum(stats.totalSessions));
      this.stat(grid, "Messages", fmtNum(stats.totalMessages));
      let tokens = 0;
      const dmt = (stats.dailyModelTokens || []);
      for (const d of dmt) for (const k in (d.tokensByModel || {})) tokens += d.tokensByModel[k];
      this.stat(grid, "Tokens", fmtNum(tokens));
    }
  }

  renderSessions(root) {
    const card = root.createDiv({ cls: "ccc-card" });
    card.createEl("div", { cls: "ccc-card-title", text: "Exported sessions" });
    const vaultBase = this.app.vault.adapter.basePath || "";
    const sessionsDir = path.join(vaultBase, "Claude Code", "Sessions");
    let count = 0;
    try {
      count = fs.readdirSync(sessionsDir).filter((f) => f.endsWith(".md")).length;
    } catch (e) { /* folder may not exist yet */ }
    this.stat(card, "Notes in vault", String(count));
  }

  renderPlugins(root) {
    const card = root.createDiv({ cls: "ccc-card" });
    card.createEl("div", { cls: "ccc-card-title", text: "Claude Code plugins" });
    const settings = readJson(path.join(CLAUDE_DIR, "settings.json")) || {};
    const enabled = settings.enabledPlugins || {};
    const names = Object.keys(enabled).filter((k) => enabled[k]).sort();
    if (!names.length) {
      card.createEl("div", { cls: "ccc-muted", text: "No user plugins enabled." });
      return;
    }
    const wrap = card.createDiv({ cls: "ccc-skills" });
    for (const n of names) {
      wrap.createEl("span", { cls: "ccc-plugin-chip", text: n.split("@")[0] });
    }
  }

  renderSkills(root) {
    const card = root.createDiv({ cls: "ccc-card" });
    card.createEl("div", { cls: "ccc-card-title", text: "Skills (click to copy command)" });
    const skills = listSkills();
    if (!skills.length) {
      card.createEl("div", { cls: "ccc-muted", text: "No skills in ~/.claude/skills." });
      return;
    }
    const wrap = card.createDiv({ cls: "ccc-skills" });
    for (const name of skills) {
      const b = wrap.createEl("button", { cls: "ccc-skill-btn", text: "/" + name });
      b.onclick = async () => {
        await navigator.clipboard.writeText("/" + name);
        new Notice("Copied: /" + name);
      };
    }
  }

  bar(parent, label, pct, note) {
    const row = parent.createDiv({ cls: "ccc-bar-row" });
    const top = row.createDiv({ cls: "ccc-bar-top" });
    top.createSpan({ text: label });
    top.createSpan({ cls: "ccc-bar-pct", text: (pct == null ? "—" : pct + "%") });
    const track = row.createDiv({ cls: "ccc-bar-track" });
    const fill = track.createDiv({ cls: "ccc-bar-fill" });
    fill.style.width = Math.min(100, Math.max(0, pct || 0)) + "%";
    if ((pct || 0) >= 80) fill.addClass("ccc-bar-hot");
    if (note) row.createDiv({ cls: "ccc-muted ccc-bar-note", text: note });
  }

  stat(parent, label, value) {
    const el = parent.createDiv({ cls: "ccc-stat" });
    el.createDiv({ cls: "ccc-stat-value", text: value });
    el.createDiv({ cls: "ccc-stat-label", text: label });
  }
}

module.exports = class ClaudeCommandCenter extends Plugin {
  async onload() {
    this.registerView(VIEW_TYPE, (leaf) => new CommandCenterView(leaf));
    this.addRibbonIcon("bot", "Claude Command Center", () => this.activateView());
    this.addCommand({
      id: "open-claude-command-center",
      name: "Open Claude Command Center",
      callback: () => this.activateView(),
    });
  }

  async activateView() {
    const { workspace } = this.app;
    let leaf = workspace.getLeavesOfType(VIEW_TYPE)[0];
    if (!leaf) {
      leaf = workspace.getRightLeaf(false);
      await leaf.setViewState({ type: VIEW_TYPE, active: true });
    }
    workspace.revealLeaf(leaf);
  }

  onunload() {}
};
