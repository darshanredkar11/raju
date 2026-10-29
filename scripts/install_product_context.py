#!/usr/bin/env python3
"""Idempotently add the Sanjay Chemicals guardrails to Harvey's native product skill.

This modifies only skills/product_knowledge.md in the explicitly supplied Harvey
checkout. It makes a timestamped backup first. It does not install dependencies,
call the network, invoke a model, edit Harvey code/config, or send messages.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

START = "<!-- BEGIN SANJAY CHEMICALS HARNESS -->"
END = "<!-- END SANJAY CHEMICALS HARNESS -->"


def install(harvey_home: Path, context_path: Path) -> str:
    skills_dir = harvey_home / "skills"
    target = skills_dir / "product_knowledge.md"
    if not target.is_file():
        raise FileNotFoundError(
            f"{target} not found. Run Harvey's native training first."
        )
    original = target.read_text(encoding="utf-8")
    if START in original or END in original:
        if START in original and END in original and original.index(START) < original.index(END):
            return "already_installed"
        raise ValueError("Found an incomplete harness marker; refusing to overwrite the skill.")

    context = context_path.read_text(encoding="utf-8").strip()
    block = f"{START}\n\n{context}\n\n{END}"
    backup_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = target.with_name(f"product_knowledge.md.backup-{backup_stamp}")
    backup.write_text(original, encoding="utf-8")
    separator = "" if not original or original.endswith("\n") else "\n"
    target.write_text(original + separator + "\n" + block + "\n", encoding="utf-8")
    return f"installed; backup={backup.name}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harvey-home", required=True, type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    context_path = repo_root / "harness" / "SANJAY_CHEMICALS_PRODUCT_CONTEXT.md"
    home = args.harvey_home.expanduser().resolve()
    try:
        result = install(home, context_path)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
