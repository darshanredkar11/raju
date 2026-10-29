#!/usr/bin/env python3
"""Idempotently install Sanjay Chemicals sales guidance into Harvey's native skills.

Writes only two explicitly named Markdown skills inside the supplied Harvey
checkout. Each original file gets a timestamped backup. No network, model API,
configuration, credentials, database, dashboard or messaging side effects.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

BLOCKS = (
    ("product_knowledge.md", "SANJAY_CHEMICALS_PRODUCT_CONTEXT.md", "PRODUCT CONTEXT"),
    ("sales_methodology.md", "SANJAY_SALES_PLAYBOOK.md", "SALES PLAYBOOK"),
)


def install_one(skills_dir: Path, target_name: str, source_path: Path, label: str, stamp: str) -> str:
    target = skills_dir / target_name
    if not target.is_file():
        raise FileNotFoundError(f"{target} not found; refusing to create a replacement for a native Harvey skill.")

    start = f"<!-- BEGIN SANJAY CHEMICALS {label} -->"
    end = f"<!-- END SANJAY CHEMICALS {label} -->"
    original = target.read_text(encoding="utf-8")
    if start in original or end in original:
        if start in original and end in original and original.index(start) < original.index(end):
            return f"{target_name}: already_installed"
        raise ValueError(f"{target_name}: incomplete harness marker; refusing to overwrite the skill.")

    context = source_path.read_text(encoding="utf-8").strip()
    block = f"{start}\n\n{context}\n\n{end}"
    backup = target.with_name(f"{target_name}.backup-{stamp}")
    backup.write_text(original, encoding="utf-8")
    separator = "" if not original or original.endswith("\n") else "\n"
    target.write_text(original + separator + "\n" + block + "\n", encoding="utf-8")
    return f"{target_name}: installed; backup={backup.name}"


def install(harvey_home: Path, repo_root: Path) -> list[str]:
    skills_dir = harvey_home / "skills"
    if not skills_dir.is_dir():
        raise FileNotFoundError(f"{skills_dir} not found; not an identifiable Harvey skills directory.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    context_dir = repo_root / "harness"
    # Validate both source and destination files before changing either file.
    for target_name, source_name, _ in BLOCKS:
        if not (skills_dir / target_name).is_file():
            raise FileNotFoundError(f"{skills_dir / target_name} not found; no files changed.")
        if not (context_dir / source_name).is_file():
            raise FileNotFoundError(f"{context_dir / source_name} not found; no files changed.")
    results = []
    for target_name, source_name, label in BLOCKS:
        results.append(install_one(skills_dir, target_name, context_dir / source_name, label, stamp))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harvey-home", required=True, type=Path)
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    try:
        for result in install(args.harvey_home.expanduser().resolve(), repo_root):
            print(result)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
