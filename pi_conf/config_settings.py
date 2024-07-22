""" Custom BaseSettings class for loading in complex types from toml files 
using the Config class."""

import json
import tempfile
from typing import Any, Dict, List, Self, Type, get_args, get_origin

import toml
from pydantic import BaseModel, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from pi_conf import Config, load_config


class ConfigDict(SettingsConfigDict, total=False):
    """Extended SettingsConfigDict for TOML-specific settings.

    Attributes:
        appname (str): The name of the application.
        table_header (str): Header for the TOML table.
    """

    appname: str
    table_header: str


class ConfigSettings(BaseSettings):
    """Main class for handling configuration settings.

    Attributes:
        model_config (ConfigDict): Configuration for the model.
    """

    model_config = ConfigDict(table_header="")

    def __init__(self, *args, **kwargs):
        """Initialize the ConfigSettings object.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Raises:
            ValueError: If neither 'toml_file' nor 'appname' is provided.
        """
        model_config = kwargs.pop("model_config", self.model_config)
        table_header = kwargs.pop("table_header", model_config.get("table_header", ""))
        locs = ["toml_file", "appname"]
        for loc in locs:
            v = kwargs.pop(loc, model_config.get(loc))
            if v:
                cfg = load_config(v)
                break
        else:
            raise ValueError(f"one of {locs} must be provided")

        if table_header:
            cfg = cfg.get_nested(table_header)

        temp_toml_file = self.create_temp_toml_file(cfg)
        try:
            self.parse_nested_objects(cfg)
            super().__init__(*args, **cfg, **kwargs)
        finally:
            import os

            os.unlink(temp_toml_file)

    @classmethod
    def model_construct(cls, _fields_set: set[str] | None = None, **values: Any) -> Self:
        """Construct the model.

        Args:
            _fields_set: Set of fields to be set (not currently supported).
            **values: Arbitrary keyword arguments for model construction.

        Returns:
            Self: An instance of the class.

        Raises:
            NotImplementedError: If _fields_set is provided.
        """
        if _fields_set is not None:
            raise NotImplementedError(
                "ConfigSettings.model_construct does not currently support _fields_set"
            )

        return cls(**values)

    @classmethod
    def create_temp_toml_file(cls, config: Config) -> str:
        """Create a temporary TOML file from the given configuration.

        Args:
            config (Config): The configuration object.

        Returns:
            str: The path to the created temporary TOML file.
        """
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=False) as temp_file:
            toml.dump(config, temp_file)
            return temp_file.name

    def parse_nested_objects(self, config_dict: Dict[str, Any]):
        """Parse nested objects in the configuration dictionary.

        Args:
            config_dict (Dict[str, Any]): The configuration dictionary to parse.
        """
        for field_name, field_value in self.__annotations__.items():
            if field_name in config_dict:
                config_dict[field_name] = self._parse_field(field_value, config_dict[field_name])

    def _parse_field(self, field_type, field_value):
        """Parse a single field based on its type.

        Args:
            field_type: The type of the field.
            field_value: The value of the field.

        Returns:
            The parsed field value.
        """
        origin = get_origin(field_type)
        if origin is List:
            item_type = get_args(field_type)[0]
            if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                return [self._parse_model(item_type, item) for item in field_value]
        elif isinstance(field_type, type) and issubclass(field_type, BaseModel):
            return self._parse_model(field_type, field_value)
        return field_value

    def _parse_model(self, model_class: Type[BaseModel], data: Dict[str, Any]) -> BaseModel:
        """Parse and validate a model using Pydantic.

        Args:
            model_class (Type[BaseModel]): The Pydantic model class.
            data (Dict[str, Any]): The data to parse into the model.

        Returns:
            BaseModel: An instance of the parsed model.

        Raises:
            ValidationError: If the data fails to validate against the model.
        """
        try:
            return model_class(**data)
        except ValidationError as e:
            print(f"Error parsing {model_class.__name__}: {e}")
            raise e

    def _pformat(self, indent: int = 4) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=indent)
