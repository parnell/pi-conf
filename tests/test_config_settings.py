from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import toml
from pydantic import BaseModel, ValidationError

from pi_conf.config_settings import ConfigDict, ConfigSettings


@pytest.fixture
def test_data():
    return {
        "string_value": "test",
        "int_value": 42,
        "list_value": [1, 2, 3],
        "dict_value": {"a": 1, "b": 2},
        "pymodel_value": {"name": "Test", "sub": {"value": 10}},
        "pymodel_list": [
            {"name": "Test1", "sub": {"value": 1}},
            {"name": "Test2", "sub": {"value": 2}},
        ],
    }


class SubModel(BaseModel):
    value: int


class ModelValue(BaseModel):
    name: str
    sub: SubModel


class MySettings(ConfigSettings):
    string_value: Optional[str] = None
    int_value: Optional[int] = None
    list_value: Optional[List[int]] = None
    dict_value: Optional[Dict[str, int]] = None
    pymodel_value: Optional[ModelValue] = None
    pymodel_list: Optional[List[ModelValue]] = None

    model_config = ConfigDict(toml_file="")


def config_settings(toml_file_path: str) -> MySettings:
    return MySettings.model_construct(
        model_config=ConfigDict(appname=toml_file_path),
    )


def write_toml(data: dict[str, Any], path: Path, name: str = "config.toml"):
    toml_string = toml.dumps(data)
    with open(path / name, "w") as toml_file:
        toml_file.write(toml_string)


def test_config_settings(tmp_path, test_data):
    config_file = tmp_path / "config.toml"
    write_toml(test_data, tmp_path)
    settings = config_settings(str(config_file))
    assert settings.string_value == test_data["string_value"]
    assert settings.int_value == test_data["int_value"]
    assert settings.list_value == test_data["list_value"]
    assert settings.dict_value == test_data["dict_value"]
    assert settings.pymodel_value
    assert settings.pymodel_value.model_dump() == test_data["pymodel_value"]
    assert settings.pymodel_list
    assert [model.model_dump() for model in settings.pymodel_list] == test_data["pymodel_list"]


def test_missing_optional_values(tmp_path):
    partial_data = {
        "string_value": "test",
        "int_value": 42,
    }
    write_toml(partial_data, tmp_path)
    settings = config_settings(str(tmp_path / "config.toml"))
    assert settings.string_value == "test"
    assert settings.int_value == 42
    assert settings.list_value is None
    assert settings.dict_value is None
    assert settings.pymodel_value is None
    assert settings.pymodel_list is None


def test_invalid_data_type(tmp_path):
    invalid_data = {
        "int_value": "not an integer",
    }
    write_toml(invalid_data, tmp_path)
    with pytest.raises(ValidationError):
        config_settings(str(tmp_path / "config.toml"))


def test_nested_toml_table(tmp_path):
    nested_data = {
        "some_other_section": {},
        "my_section": {
            "string_value": "nested",
            "int_value": 100,
        },
    }
    write_toml(nested_data, tmp_path)

    class NestedSettings(ConfigSettings):
        string_value: str
        int_value: int
        model_config = ConfigDict(toml_file="", toml_table_header="my_section")

    settings = NestedSettings.model_construct(
        model_config=ConfigDict(
            appname=str(tmp_path / "config.toml"), toml_table_header="my_section"
        ),
    )
    assert settings.string_value == "nested"
    assert settings.int_value == 100


def test_config_dict_construction():
    config = ConfigDict(appname="test_app", toml_table_header="my_section")
    assert "appname" in config and "toml_table_header" in config
    assert config["appname"] == "test_app"
    assert config["toml_table_header"] == "my_section"


def test_model_construct_with_values():
    values = {
        "string_value": "constructed",
        "int_value": 200,
    }
    settings = MySettings.model_construct(**values)
    assert settings.string_value == "constructed"
    assert settings.int_value == 200
    assert settings.list_value is None


@pytest.mark.parametrize("file_name", ["config.toml", "alternate_config.toml"])
def test_different_file_names(tmp_path, test_data, file_name):
    write_toml(test_data, tmp_path, name=file_name)
    settings = config_settings(str(tmp_path / file_name))
    assert settings.string_value == test_data["string_value"]
    assert settings.int_value == test_data["int_value"]


if __name__ == "__main__":
    pytest.main([__file__])
