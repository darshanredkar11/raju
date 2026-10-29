from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "harvey_preflight.py"
SPEC = importlib.util.spec_from_file_location("harvey_preflight", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_preflight_never_allows_email_without_human_approval(tmp_path: Path, monkeypatch, capsys):
    home = tmp_path / "harvey"
    (home / "harvey").mkdir(parents=True)
    (home / "skills").mkdir()
    (home / "data").mkdir()
    (home / "pyproject.toml").write_text("[project]\nname='harvey'\n", encoding="utf-8")
    (home / "harvey" / "cli.py").write_text("", encoding="utf-8")
    (home / "harvey" / "dashboard.py").write_text("", encoding="utf-8")
    (home / "harvey.yaml").write_text(yaml.safe_dump({
        "persona": {"company": "Sanjay Chemicals"},
        "product": {"name": "Verified product", "description": "Verified from official TDS"},
        "icp": {"industries": ["chemical distribution"], "geography": ["India"]},
        "channels": {"email": {"enabled": True, "provider": "smtp", "require_approval": False}},
    }), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["harvey_preflight.py", "--harvey-home", str(home)])
    assert MODULE.main() == 1
    output = capsys.readouterr().out
    assert "human_approval" in output
    assert "must be true" in output


def test_preflight_accepts_approval_enabled(tmp_path: Path, monkeypatch, capsys):
    home = tmp_path / "harvey"
    (home / "harvey").mkdir(parents=True)
    (home / "skills").mkdir()
    (home / "pyproject.toml").write_text("[project]\nname='harvey'\n", encoding="utf-8")
    (home / "harvey" / "cli.py").write_text("", encoding="utf-8")
    (home / "harvey" / "dashboard.py").write_text("", encoding="utf-8")
    (home / "harvey.local.yaml").write_text(yaml.safe_dump({
        "persona": {"company": "Sanjay Chemicals"},
        "product": {"name": "Verified product", "description": "Verified from official TDS"},
        "icp": {"industries": ["chemical distribution"], "geography": ["India"]},
        "channels": {"email": {"enabled": True, "provider": "smtp", "require_approval": True}},
    }), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["harvey_preflight.py", "--harvey-home", str(home)])
    assert MODULE.main() == 0
    output = capsys.readouterr().out
    assert '"ready": true' in output
    assert "Sanjay Chemicals" not in output  # output avoids echoing business config values
