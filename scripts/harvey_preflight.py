#!/usr/bin/env python3
"""Read-only readiness checks for an existing upstream Harvey checkout.

This script intentionally does not start Harvey, modify config, call model APIs,
send mail, or reveal secret values.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Run this with Harvey's Python environment.", file=sys.stderr)
    raise SystemExit(2)


PLACEHOLDERS = {
    "", "your company", "your product", "describe what your product does and who it's for",
    "starting at $x/mo",
}


def norm(value: object) -> str:
    return str(value or "").strip().casefold()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harvey-home", required=True, type=Path, help="Path to the existing upstream Harvey checkout")
    args = parser.parse_args()
    home = args.harvey_home.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[dict[str, str]] = []

    def record(name: str, status: str, detail: str) -> None:
        checks.append({"check": name, "status": status, "detail": detail})

    if not home.is_dir():
        print(json.dumps({"ready": False, "error": f"Harvey directory does not exist: {home}"}, indent=2))
        return 2

    required = [home / "pyproject.toml", home / "harvey" / "cli.py", home / "harvey" / "dashboard.py", home / "skills"]
    missing = [str(p.relative_to(home)) for p in required if not p.exists()]
    if missing:
        errors.append("Not an identifiable Harvey checkout; missing: " + ", ".join(missing))
        record("checkout", "fail", "Missing required upstream paths")
    else:
        record("checkout", "pass", "Upstream Harvey source layout found")

    config_path = home / "harvey.local.yaml"
    if not config_path.is_file():
        config_path = home / "harvey.yaml"
    if not config_path.is_file():
        errors.append("No harvey.local.yaml or harvey.yaml found")
        config: dict = {}
        record("configuration", "fail", "No active config file")
    else:
        try:
            loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            if not isinstance(loaded, dict):
                raise ValueError("top-level YAML value must be a mapping")
            config = loaded
            record("configuration", "pass", f"Parsed {config_path.name}")
        except Exception as exc:
            errors.append(f"Could not parse {config_path.name}: {exc}")
            config = {}
            record("configuration", "fail", "Invalid YAML")

    persona = config.get("persona") or {}
    product = config.get("product") or {}
    icp = config.get("icp") or {}
    if norm(persona.get("company")) in PLACEHOLDERS:
        warnings.append("Set persona.company to the verified company name.")
    if norm(product.get("name")) in PLACEHOLDERS or norm(product.get("description")) in PLACEHOLDERS:
        warnings.append("Train Harvey and verify product.name/description against official product documents.")
    if not icp.get("industries") or not icp.get("geography"):
        warnings.append("Define the target industries and geography before prospecting.")
    record("business_training", "warn" if any("persona.company" in x or "product." in x or "target industries" in x for x in warnings) else "pass",
           "Business/product/ICP fields checked; product claims still require human verification")

    channels = config.get("channels") or {}
    email = channels.get("email") or {}
    if email.get("enabled") is not True:
        warnings.append("Native email channel is not enabled; configure it only when ready.")
    if email.get("require_approval") is not True:
        errors.append("Safety gate: channels.email.require_approval must be true for this harness.")
        record("human_approval", "fail", "Email approval is not enabled")
    else:
        record("human_approval", "pass", "Native email approval is enabled")
    if not email.get("provider"):
        warnings.append("Choose a native email provider before testing mailbox connectivity.")

    if (home / ".env").is_file():
        record("secrets_file", "pass", ".env exists; values were not read or displayed")
    else:
        warnings.append("No .env file found; native provider credentials may not be configured.")
        record("secrets_file", "warn", "No .env file")

    if (home / "data" / "harvey.db").exists():
        record("state_store", "pass", "Harvey SQLite database exists")
    else:
        warnings.append("Harvey SQLite database not found yet; this may be normal before the first run.")
        record("state_store", "warn", "No database found yet")

    cli = shutil.which("harvey")
    if not cli:
        local_cli = home / ".venv" / "bin" / "harvey"
        cli = str(local_cli) if local_cli.exists() else None
    if cli:
        record("cli", "pass", "Harvey CLI executable found; runtime health not inferred")
    else:
        warnings.append("Harvey CLI was not found on PATH or in .venv/bin.")
        record("cli", "warn", "CLI not found in this environment")

    result = {
        "ready": not errors,
        "harvey_home": str(home),
        "active_config": str(config_path) if config_path.exists() else None,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "next_step": "Perform a native-dashboard smoke test and verify a draft stays in Outbox; this static check does not prove runtime connectivity.",
    }
    print(json.dumps(result, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
