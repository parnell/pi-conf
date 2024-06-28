import os
import sys
import tempfile
import pytest

import pi_conf.config as config
from pi_conf import Config
from pi_conf.provenance import ProvenanceOp

basedir = os.path.abspath(os.getcwd())
sys.path.append(basedir)

@pytest.fixture(scope="module")
def setup_module():
    # Any setup before tests run can be done here
    yield
    # Any teardown after tests run can be done here

def test_provenance_of_config_provenance_disabled(setup_module):
    from pi_conf.provenance import _provenance_manager

    cfg = Config({"a": 1}, enable_provenance=False)

    assert len(cfg.provenance) == 0
    oid = id(cfg)
    assert oid not in _provenance_manager._enabled

def test_provenance_from_dict_directly(setup_module):
    cfg = Config({"a": 1})
    assert cfg.provenance[-1].source == "dict"
    assert cfg.provenance[-1].operation == ProvenanceOp.set
    assert len(cfg.provenance) == 1

def test_provenance_from_dict(setup_module):
    cfg = Config.from_dict({"a": 1})
    assert cfg.provenance[-1].source == "dict"
    assert cfg.provenance[-1].operation == ProvenanceOp.set
    assert len(cfg.provenance) == 1

def test_provenance_from_dict2(setup_module):
    cfg = Config.from_dict({"a": 1})
    assert cfg.provenance[-1].source == "dict"
    assert cfg.provenance[-1].operation == ProvenanceOp.set
    cfg.update({"b": 2})
    assert cfg.provenance[-1].source == "dict"
    assert cfg.provenance[-1].operation == ProvenanceOp.update
    assert len(cfg.provenance) == 2

def test_provenance_from_set_config(setup_module):
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

def test_provenance_from_load_config(setup_module):
    s = """
    [a]
    b = 1"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml") as f:
        f.write(s)
        f.flush()

        cfg = config.load_config(f.name)

        assert len(cfg.provenance) == 1
        assert cfg.provenance[0].source == f.name


if __name__ == "__main__":
    pytest.main([__file__])