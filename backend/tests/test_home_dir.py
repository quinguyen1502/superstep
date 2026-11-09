"""the default data directory moved to ~/.superstep; a v0.1.0 ~/.langgraph-studio is still used."""
from app.core import config


def test_home_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config.home_dir() == str(tmp_path / ".superstep")       # fresh install
    (tmp_path / ".langgraph-studio").mkdir()
    assert config.home_dir() == str(tmp_path / ".langgraph-studio")  # only the old one exists: keep its secret.key
    (tmp_path / ".superstep").mkdir()
    assert config.home_dir() == str(tmp_path / ".superstep")       # both: the new one wins
