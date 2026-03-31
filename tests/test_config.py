import os
import sys

import pytest

import pi_conf.config as config_module
from pi_conf import AttrDict, Config, load_config, set_config

basedir = os.path.abspath(os.getcwd())
sys.path.append(basedir)


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


def test_set_config_not_exists(tmpdir):
    bn = os.path.basename(tmpdir)
    set_config(bn, directories=[tmpdir])
    with open(os.path.join(tmpdir, "config.toml"), "w") as f:
        f.write("a = 1")
        f.flush()
    cfg = load_config(bn, directories=[tmpdir])
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


def test_config_load_config_conflict_raises_by_default():
    cfg = Config.from_dict({"a": 1})

    with pytest.raises(ValueError, match="overwrite existing keys: a"):
        cfg.load_config({"a": 2})


def test_config_load_config_overwrite_true_allows_replacement():
    cfg = Config.from_dict({"a": 1})

    cfg.load_config({"a": 2}, overwrite=True)

    assert cfg.a == 2


def test_update_config_conflict_raises_by_default():
    original = Config.from_dict(dict(config_module.cfg))
    original_provenance = list(config_module.cfg.provenance)
    try:
        config_module.cfg.clear()
        config_module.cfg.update({"a": 1}, _add_to_provenance=False)

        with pytest.raises(ValueError, match="overwrite existing keys: a"):
            config_module.update_config({"a": 2}, directories=None)
    finally:
        config_module.cfg.clear()
        config_module.cfg.update(original, _add_to_provenance=False)
        pm = config_module.get_pmanager()
        pm.clear(config_module.cfg)
        pm.extend(config_module.cfg, original_provenance)


def test_update_config_overwrite_true_allows_replacement():
    original = Config.from_dict(dict(config_module.cfg))
    original_provenance = list(config_module.cfg.provenance)
    try:
        config_module.cfg.clear()
        config_module.cfg.update({"a": 1}, _add_to_provenance=False)

        updated = config_module.update_config({"a": 2}, directories=None, overwrite=True)

        assert updated.a == 2
        assert config_module.cfg.a == 2
    finally:
        config_module.cfg.clear()
        config_module.cfg.update(original, _add_to_provenance=False)
        pm = config_module.get_pmanager()
        pm.clear(config_module.cfg)
        pm.extend(config_module.cfg, original_provenance)


if __name__ == "__main__":
    pytest.main([__file__])
