from pathlib import Path

import importlib.util


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_product_context.py"
SPEC = importlib.util.spec_from_file_location("install_product_context", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_install_appends_context_and_preserves_backup(tmp_path: Path):
    home = tmp_path / "harvey"
    skills = home / "skills"
    skills.mkdir(parents=True)
    target = skills / "product_knowledge.md"
    target.write_text("# Existing Harvey training\nVerified product notes.\n", encoding="utf-8")
    context = tmp_path / "context.md"
    context.write_text("## Verified company context\nDo not invent product claims.\n", encoding="utf-8")

    result = MODULE.install(home, context)

    updated = target.read_text(encoding="utf-8")
    backups = list(skills.glob("product_knowledge.md.backup-*"))
    assert result.startswith("installed; backup=")
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "# Existing Harvey training\nVerified product notes.\n"
    assert "Verified product notes." in updated
    assert "Do not invent product claims." in updated
    assert updated.count(MODULE.START) == 1
    assert updated.count(MODULE.END) == 1


def test_install_is_idempotent(tmp_path: Path):
    home = tmp_path / "harvey"
    skills = home / "skills"
    skills.mkdir(parents=True)
    target = skills / "product_knowledge.md"
    target.write_text("# Existing Harvey training\n", encoding="utf-8")
    context = tmp_path / "context.md"
    context.write_text("## Context\nNo invented claims.\n", encoding="utf-8")

    first = MODULE.install(home, context)
    after_first = target.read_text(encoding="utf-8")
    second = MODULE.install(home, context)

    assert first.startswith("installed; backup=")
    assert second == "already_installed"
    assert target.read_text(encoding="utf-8") == after_first
    assert len(list(skills.glob("product_knowledge.md.backup-*"))) == 1
