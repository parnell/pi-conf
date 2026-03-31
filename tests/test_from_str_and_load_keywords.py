"""Tests for AttrDict.from_str and load_config keyword sources."""

import pytest

from pi_conf import load_config
from pi_conf.attr_dict import AttrDict


def test_from_str_toml():
    cfg = AttrDict.from_str("foo = 1\n[bar]\na = 2", "toml")
    assert cfg.foo == 1
    assert cfg.bar.a == 2


def test_from_str_json():
    cfg = AttrDict.from_str('{"x": {"y": 3}}', "json")
    assert cfg.x.y == 3


def test_from_str_ini():
    cfg = AttrDict.from_str(
        "[section]\nkey = value\n",
        "ini",
    )
    assert cfg.section.key == "value"


def test_from_str_yaml():
    pytest.importorskip("yaml")
    cfg = AttrDict.from_str("a:\n  b: 4\n", "yaml")
    assert cfg.a.b == 4


def test_from_str_unknown_type():
    with pytest.raises(Exception, match="Unknown config_type"):
        AttrDict.from_str("{}", "xml")


def test_load_config_data_keyword():
    cfg = load_config(data={"a": 1, "b": {"c": 2}})
    assert cfg.a == 1
    assert cfg.b.c == 2


def test_load_config_path_keyword(tmp_path):
    p = tmp_path / "cfg.toml"
    p.write_text("k = 9\n")
    cfg = load_config(path=str(p))
    assert cfg.k == 9


def test_load_config_path_keyword_ignore_warnings(tmp_path):
    missing = tmp_path / "nope.toml"
    cfg = load_config(path=str(missing), ignore_warnings=True)
    assert dict(cfg) == {}


def test_load_config_appname_keyword(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    appdir = tmp_path / ".config" / "kwapp"
    appdir.mkdir(parents=True)
    (appdir / "config.toml").write_text("z = 7\n")
    cfg = load_config(appname="kwapp")
    assert cfg.z == 7


def test_load_config_appname_prefers_dot_config_toml(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    appdir = tmp_path / ".config" / "kwapp"
    appdir.mkdir(parents=True)
    (appdir / ".config.toml").write_text("z = 9\n")
    (appdir / "config.toml").write_text("z = 7\n")
    cfg = load_config(appname="kwapp")
    assert cfg.z == 9


def test_load_config_keyword_conflict_raises():
    with pytest.raises(ValueError, match="Only one of data="):
        load_config(data={"a": 1}, path="x.toml")


def test_load_config_positional_plus_keyword_raises(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text("a = 1\n")
    with pytest.raises(ValueError, match="Cannot combine a positional"):
        load_config(str(p), path=str(p))


def test_load_config_file_param_with_appname_keyword(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    appdir = tmp_path / ".config" / "myapp"
    appdir.mkdir(parents=True)
    (appdir / "secrets.toml").write_text("token = \"abc\"\n")
    cfg = load_config(appname="myapp", file="secrets.toml")
    assert cfg.token == "abc"
