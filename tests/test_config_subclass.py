import os
import sys
from dataclasses import dataclass, field

import pytest
from pi_conf import AttrDict, Config

basedir = os.path.abspath(os.getcwd())
sys.path.append(basedir)

@pytest.fixture
def myconfig():
    @dataclass
    class MyConfig(Config):
        a: int = 1
    return MyConfig

def test_dataclass_subclass(myconfig):
    cfg = myconfig()
    assert cfg.a == 1

def test_dataclass_subclass_from_dict(myconfig):
    cfg = myconfig.from_dict({"a": 1})
    assert cfg.a == 1
    assert type(cfg) == myconfig

def test_config_dict_init():
    @dataclass
    class MyConfig(Config):
        a: int = 1
        b: int = 2

    cfg = MyConfig(**{"a": 1, "b": 2})
    assert cfg.a == 1
    assert cfg["a"] == 1
    assert cfg.get("a") == 1
    assert cfg.b == 2
    assert cfg["b"] == 2
    assert cfg.get("b") == 2

def test_dataclass_subclass_from_dict_recursive_nested_false():
    @dataclass
    class MyConfig(Config):
        a: int = 1
        b: AttrDict = field(default_factory=AttrDict)

    cfg = MyConfig.from_dict({"a": 1, "b": {"c": 2}})
    assert cfg.a == 1
    assert cfg["a"] == 1
    assert cfg.b.c == 2
    assert cfg["b"]["c"] == 2
    assert type(cfg) == MyConfig
    assert type(cfg.a) == int
    assert type(cfg.b) == AttrDict


if __name__ == "__main__":
    pytest.main([__file__])