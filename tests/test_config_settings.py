from typing import Any, Dict, List, Optional

import pytest
import toml
from pydantic import BaseModel

from pi_conf.config_settings import ConfigSettings, TomlSettingsConfigDict


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

    model_config = TomlSettingsConfigDict(toml_file="")


def config(toml_file_path: str):
    return MySettings.model_construct(
        model_config=TomlSettingsConfigDict(appname=toml_file_path),
    )
    # return MySettings(model_config={"appname":toml_file_path})


def write_toml(data: dict[str, Any], path: str, name: str = "config.toml"):
    toml_string = toml.dumps(data)
    with open(f"{path}/{name}", "w") as toml_file:
        toml_file.write(toml_string)


def test_config_settings(tmp_path, test_data):
    config_file = tmp_path / "config.toml"
    write_toml(test_data, tmp_path)
    config_settings = config(str(config_file))
    assert config_settings.string_value == test_data["string_value"]
    assert config_settings.int_value == test_data["int_value"]
    assert config_settings.list_value == test_data["list_value"]
    assert config_settings.dict_value == test_data["dict_value"]
    assert config_settings.pymodel_value
    assert config_settings.pymodel_value.model_dump() == test_data["pymodel_value"]
    assert config_settings.pymodel_list
    assert [model.model_dump() for model in config_settings.pymodel_list] == test_data[
        "pymodel_list"
    ]


if __name__ == "__main__":
    pytest.main([__file__])
