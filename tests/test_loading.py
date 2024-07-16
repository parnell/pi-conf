import os
import tempfile

import pytest

from pi_conf import load_config
from pi_conf.config import _load_config_file


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


def test_load_non_default(tmpdir):
    s = """
    [a]
    b = 1
    """
    with open(os.path.join(tmpdir, "alt_config.toml"), "w") as f:
        f.write(s)
    cfg = load_config("alt_config.toml", config_directories=[tmpdir])

    assert cfg["a"]["b"] == 1


def test_load_non_default_nested(tmpdir):
    s = """
    [a]
    b = 1
    """
    nested_dir = os.path.join(tmpdir, "nested")
    os.makedirs(nested_dir)
    file_name = f"alt_config.toml"
    file_loc = os.path.join(tmpdir, os.path.join(nested_dir, file_name))
    with open(file_loc, "w") as f:
        f.write(s)
    cfg = load_config(file_name, config_directories=[nested_dir])

    assert cfg["a"]["b"] == 1


def test_load_non_default_nested_filename(tmpdir):
    s = """
    [a]
    b = 1
    """
    nested_dir = os.path.join(tmpdir, "nested")
    os.makedirs(nested_dir)
    file_name = f"alt_config.toml"
    file_loc = os.path.join(tmpdir, os.path.join(nested_dir, file_name))
    with open(file_loc, "w") as f:
        f.write(s)
    cfg = load_config(f"nested/{file_name}", config_directories=[tmpdir])

    assert cfg["a"]["b"] == 1


def test_load_from_abs_path(tmpdir):
    s = """
    [a]
    b = 1
    """
    file_name = f"alt_config.toml"
    file_loc = os.path.join(tmpdir, file_name)
    with open(file_loc, "w") as f:
        f.write(s)
    cfg = load_config(file_loc)

    assert cfg["a"]["b"] == 1


if __name__ == "__main__":
    pytest.main([__file__])
