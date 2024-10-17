import os
import tempfile
from pathlib import Path

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


def test_load_from_directory(tmpdir):
    s = """
    [a]
    b = 1
    """
    with open(os.path.join(tmpdir, "alt_config.toml"), "w") as f:
        f.write(s)
    cfg = load_config("alt_config.toml", directories=[tmpdir])

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
    cfg = load_config(file_name, directories=[nested_dir])

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
    cfg = load_config(f"nested/{file_name}", directories=[tmpdir])

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


def test_config_loads_toml_from_path():
    s = """
    [a]
    b = 1"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(s)
        f.flush()
        path = Path(f.name)

    cfg = _load_config_file(path)
    assert cfg["a"]["b"] == 1

    path.unlink()  # Clean up the temporary file


def test_load_from_directory_with_path(tmpdir):
    s = """
    [a]
    b = 1
    """
    config_path = Path(tmpdir) / "alt_config.toml"
    config_path.write_text(s)

    cfg = load_config("alt_config.toml", directories=[Path(tmpdir)])
    assert cfg["a"]["b"] == 1


def test_load_non_default_nested_with_path(tmpdir):
    s = """
    [a]
    b = 1
    """
    nested_dir = Path(tmpdir) / "nested"
    nested_dir.mkdir(parents=True, exist_ok=True)

    file_name = "alt_config.toml"
    file_loc = nested_dir / file_name
    file_loc.write_text(s)

    cfg = load_config(file_name, directories=[nested_dir])
    assert cfg["a"]["b"] == 1


def test_load_from_abs_path_with_path(tmpdir):
    s = """
    [a]
    b = 1
    """
    file_name = "alt_config.toml"
    file_loc = Path(tmpdir) / file_name
    file_loc.write_text(s)

    cfg = load_config(file_loc)
    assert cfg["a"]["b"] == 1


def test_load_config_with_different_file_types_using_path(tmpdir):
    base_path = Path(tmpdir)

    # TOML
    toml_path = base_path / "config.toml"
    toml_path.write_text("[a]\nb = 1")

    # JSON
    json_path = base_path / "config.json"
    json_path.write_text('{"a": {"b": 1}}')

    # YAML
    yaml_path = base_path / "config.yaml"
    yaml_path.write_text("a:\n  b: 1")

    # INI
    ini_path = base_path / "config.ini"
    ini_path.write_text("[a]\nb = 1")

    for path in [toml_path, json_path, yaml_path, ini_path]:
        cfg = _load_config_file(path)
        assert cfg["a"]["b"] == 1 if path.suffix != ".ini" else "1"


if __name__ == "__main__":
    pytest.main([__file__])
