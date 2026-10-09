#!/usr/bin/env python3
"""Create GitHub labels and issues from docs/TASKS.md.

Usage:
  python3 scripts/create_issues.py --dry-run   # print what would be created
  python3 scripts/create_issues.py             # create via the gh CLI

Needs `gh auth login` and a GitHub remote. Re-running is safe: issues whose
title already exists are skipped, and checked tasks are ignored.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TASKS = Path(__file__).resolve().parent.parent / "docs" / "TASKS.md"
LINE = re.compile(
    r"^- \[(?P<done>[ x])\] \*\*(?P<id>P(?P<phase>\d)-[A-Z0-9]+-\d+)\*\* · (?P<title>.+?)"
    r" — owner: (?P<owner>[\w-]+) · depends: (?P<depends>.+?) · done when: (?P<done_when>.+)$"
)
LABELS = {
    "phase-0": ("5319e7", "Aligner test (go/no-go)"),
    "phase-1": ("1d76db", "Core Basa flow"),
    "phase-2": ("0e8a16", "Full loop: Sulat, Sanay, class view"),
    "phase-3": ("fbca04", "Numbers, polish, submission"),
    "ai": ("b60205", "AI engineer"),
    "backend-1": ("0052cc", "Backend 1: engine service"),
    "backend-2": ("006b75", "Backend 2: data and logic"),
    "frontend": ("d93f0b", "Frontend"),
    "everyone": ("c5def5", "Whole team"),
}


def parse_tasks():
    tasks = []
    in_code = False
    for n, line in enumerate(TASKS.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("```"):
            in_code = not in_code
        if in_code or not line.startswith("- ["):
            continue
        m = LINE.match(line)
        if not m:
            sys.exit(f"TASKS.md line {n} doesn't match the task format:\n  {line}")
        if m["owner"] not in LABELS:
            sys.exit(f"TASKS.md line {n}: unknown owner '{m['owner']}'")
        tasks.append(m.groupdict())
    return tasks


def issue_body(t):
    deps = [d.strip() for d in t["depends"].split(",") if d.strip() != "none"]
    deps_md = "\n".join(f"- {d}" for d in deps) if deps else "- none"
    return (
        f"**Task:** {t['id']} · **Owner:** {t['owner']} · **Phase:** {t['phase']}\n\n"
        f"### Done when\n- [ ] {t['done_when']}\n\n"
        f"### Depends on\n{deps_md}\n\n"
        "Source: `docs/TASKS.md`. Tick the box there in the PR that finishes this task.\n"
        "Context: `docs/PLAN.md`, API contract: `docs/API.md`."
    )


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    dry = ap.parse_args().dry_run

    todo = [t for t in parse_tasks() if t["done"] == " "]
    if dry:
        for t in todo:
            print(f"[{t['id']}] {t['title']}  (labels: phase-{t['phase']}, {t['owner']})")
        print(f"\n{len(todo)} issues would be created, plus {len(LABELS)} labels.")
        return

    for name, (color, desc) in LABELS.items():
        gh("label", "create", name, "--color", color, "--description", desc, "--force")
    existing = {i["title"] for i in json.loads(gh("issue", "list", "--state", "all", "--limit", "1000", "--json", "title"))}

    created = 0
    for t in todo:
        title = f"[{t['id']}] {t['title']}"
        if title in existing:
            print(f"skip (exists): {title}")
            continue
        gh("issue", "create", "--title", title, "--body", issue_body(t),
           "--label", f"phase-{t['phase']}", "--label", t["owner"])
        print(f"created: {title}")
        created += 1
    print(f"\nDone: {created} created, {len(todo) - created} skipped.")


if __name__ == "__main__":
    main()
