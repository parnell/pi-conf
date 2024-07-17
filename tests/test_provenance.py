import os
import sys
import tempfile
import pytest

import pi_conf.config as config
from pi_conf import Config
from pi_conf.provenance import ProvenanceOp

basedir = os.path.abspath(os.getcwd())
sys.path.append(basedir)

def test_provenance_of_config_provenance_disabled():
    from pi_conf.provenance import _provenance_manager

    cfg = Config({"a": 1}, enable_provenance=False)

    assert len(cfg.provenance) == 0
    oid = id(cfg)
    assert oid not in _provenance_manager._enabled

def test_provenance_from_dict_directly():
    cfg = Config({"a": 1})
    assert cfg.provenance[-1].source == "dict"
    assert cfg.provenance[-1].operation == ProvenanceOp.set
    assert len(cfg.provenance) == 1

def test_provenance_from_dict():
    cfg = Config.from_dict({"a": 1})
    assert cfg.provenance[-1].source == "dict"
    assert cfg.provenance[-1].operation == ProvenanceOp.set
    assert len(cfg.provenance) == 1

def test_provenance_from_dict2():
    cfg = Config.from_dict({"a": 1})
    assert cfg.provenance[-1].source == "dict"
    assert cfg.provenance[-1].operation == ProvenanceOp.set
    cfg.update({"b": 2})
    assert cfg.provenance[-1].source == "dict"
    assert cfg.provenance[-1].operation == ProvenanceOp.update
    assert len(cfg.provenance) == 2

def test_provenance_from_set_config():
    s = """
    [a]
    b = 1"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml") as f:
        f.write(s)
        f.flush()

        cfg = config.set_config(f.name)

        assert len(cfg.provenance) == 1
        assert cfg.provenance[0].source == f.name
        assert cfg.provenance[0].operation == ProvenanceOp.set

def test_provenance_from_load_config():
    s = """
    [a]
    b = 1"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml") as f:
        f.write(s)
        f.flush()

        cfg = config.load_config(f.name)

        assert len(cfg.provenance) == 1
        assert cfg.provenance[0].source == f.name

def test_provenance_from_load_config_twice():
    s = """
    [a]
    b = 1"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml") as f:
        f.write(s)
        f.flush()

        cfg = config.load_config(f.name)
        cfg = config.load_config(f.name)

        assert len(cfg.provenance) == 1
        assert cfg.provenance[0].source == f.name
        pm = config.get_pmanager()
        pm._provenance

if __name__ == "__main__":
    pytest.main([__file__])