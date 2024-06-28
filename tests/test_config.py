import os
import sys
import tempfile
import pytest

from pi_conf.config import _load_config_file
from pi_conf import Config, load_config, set_config, AttrDict

basedir = os.path.abspath(os.getcwd())
sys.path.append(basedir)


@pytest.fixture(scope="module")
def setup_teardown():
    yield
    # Cleanup code if needed


def test_config_empty_at_start():
    from pi_conf import cfg

    assert len(cfg) == 0


def test_config_from_dict():
    cfg = Config.from_dict({"a": 1})
    assert cfg.a == 1


def test_config_from_raw_dict():
    cfg = Config({"a": 1})
    assert cfg.a == 1


def test_config_from_list_dict_nested():
    cfg = Config.from_dict({"a": 1, "b": [{"c": 2}, {"d": 3}]})
    assert cfg.a == 1
    assert cfg.b[0].c == 2


def test_config_loads_toml():
    s = """
    [a]
    b = 1"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml") as f:
        f.write(s)
        f.flush()
        cfg = _load_config_file(f.name)
        assert cfg["a"]["b"] == 1


def test_config_loads_json():
    s = """
    {
        "a": {
            "b": 1
        }
    }
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as f:
        f.write(s)
        f.flush()
        cfg = _load_config_file(f.name)
        assert cfg["a"]["b"] == 1


def test_config_loads_yaml():
    s = """
    a:
        b: 1
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as f:
        f.write(s)
        f.flush()
        cfg = _load_config_file(f.name)
        assert cfg["a"]["b"] == 1


def test_config_loads_ini():
    s = """
    [a]
    b = 1
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini") as f:
        f.write(s)
        f.flush()
        cfg = _load_config_file(f.name)
        assert cfg["a"]["b"] == "1"


def test_config_dict_init():
    cfg = Config({"a": 1})
    assert cfg.a == 1
    assert cfg["a"] == 1
    assert cfg.get("a") == 1


def test_to_env_list():
    cfg = Config({"a": [{"b": 1}, {"b": 2}]})
    envs = cfg.to_env(overwrite=True)
    assert envs == [("A0_B", "1"), ("A1_B", "2")]


def test_to_env_list_dict():
    cfg = Config({"a": [{"b": 1}, {"b": {"c": 2}}]})
    envs = cfg.to_env(overwrite=True)
    assert envs == [("A0_B", "1"), ("A1_B_C", "2")]


def test_to_env_dict():
    cfg = Config({"a": {"b": 1, "c": {"d": 2}}})
    envs = cfg.to_env(overwrite=True)
    assert envs == [("A_B", "1"), ("A_C_D", "2")]


def test_to_env_str():
    cfg = Config({"a": 1, "b": "2"})
    envs = cfg.to_env(overwrite=True)
    assert envs == [("A", "1"), ("B", "2")]


def test_set_config_not_exists():
    with tempfile.TemporaryDirectory() as d:
        bn = os.path.basename(d)
        set_config(bn, config_directories=[d])
        with open(os.path.join(d, "config.toml"), "w") as f:
            f.write("a = 1")
            f.flush()
        cfg = load_config(bn, config_directories=[d])
        assert cfg.a == 1


def test_update_attrdict_with_attrdict():
    d1 = AttrDict({"a": 1, "b": 2})
    d2 = AttrDict({"a": 2, "c": 3})
    d1.update(d2)
    assert d1.a == 2
    assert d1.b == 2
    assert d1.c == 3


def test_update_attrdict_with_dict():
    d1 = AttrDict({"a": 1, "b": 2})
    d2 = {"b": {"a": 2, "c": 3}}
    d1.update(d2)
    assert d1.a == 1
    assert d1.b.a == 2
    assert d1.b.c == 3

if __name__ == "__main__":
    pytest.main([__file__])