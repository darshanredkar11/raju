from pathlib import Path
import importlib.util


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_product_context.py"
SPEC = importlib.util.spec_from_file_location("install_product_context", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def make_fixture(tmp_path: Path):
    repo = tmp_path / "repo"
    context = repo / "harness"
    context.mkdir(parents=True)
    (context / "SANJAY_CHEMICALS_PRODUCT_CONTEXT.md").write_text(
        "## Verified product context\nNever invent product claims.\n", encoding="utf-8")
    (context / "SANJAY_SALES_PLAYBOOK.md").write_text(
        "## RFQ workflow\nCapture quantity and delivery location.\n", encoding="utf-8")
    home = tmp_path / "harvey"
    skills = home / "skills"
    skills.mkdir(parents=True)
    (skills / "product_knowledge.md").write_text("# Existing product skill\nExisting product notes.\n", encoding="utf-8")
    (skills / "sales_methodology.md").write_text("# Existing sales skill\nExisting sales rules.\n", encoding="utf-8")
    return home, repo, skills


def test_installs_into_native_skills_and_preserves_backups(tmp_path: Path):
    home, repo, skills = make_fixture(tmp_path)
    result = MODULE.install(home, repo)

    product = (skills / "product_knowledge.md").read_text(encoding="utf-8")
    sales = (skills / "sales_methodology.md").read_text(encoding="utf-8")
    assert len(result) == 2
    assert "Never invent product claims." in product
    assert "Capture quantity and delivery location." in sales
    assert "Existing product notes." in product
    assert "Existing sales rules." in sales
    assert len(list(skills.glob("product_knowledge.md.backup-*"))) == 1
    assert len(list(skills.glob("sales_methodology.md.backup-*"))) == 1


def test_install_is_idempotent(tmp_path: Path):
    home, repo, skills = make_fixture(tmp_path)
    MODULE.install(home, repo)
    product_after_first = (skills / "product_knowledge.md").read_text(encoding="utf-8")
    sales_after_first = (skills / "sales_methodology.md").read_text(encoding="utf-8")

    result = MODULE.install(home, repo)

    assert result == [
        "product_knowledge.md: already_installed",
        "sales_methodology.md: already_installed",
    ]
    assert (skills / "product_knowledge.md").read_text(encoding="utf-8") == product_after_first
    assert (skills / "sales_methodology.md").read_text(encoding="utf-8") == sales_after_first
    assert len(list(skills.glob("product_knowledge.md.backup-*"))) == 1
    assert len(list(skills.glob("sales_methodology.md.backup-*"))) == 1


def test_missing_native_skill_fails_before_any_change(tmp_path: Path):
    home, repo, skills = make_fixture(tmp_path)
    (skills / "sales_methodology.md").unlink()
    before = (skills / "product_knowledge.md").read_text(encoding="utf-8")

    try:
        MODULE.install(home, repo)
        assert False, "expected missing native skill to fail"
    except FileNotFoundError:
        pass

    assert (skills / "product_knowledge.md").read_text(encoding="utf-8") == before
    assert not list(skills.glob("*.backup-*"))
