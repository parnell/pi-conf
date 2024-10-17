""" Custom BaseSettings class for loading in complex types from toml files 
using the Config class."""

import json
import re
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Self, Type, TypeVar, get_args, get_origin

import toml
from bson import ObjectId
from pydantic import BaseModel, PrivateAttr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from pi_conf import Config, load_config
from pi_conf.config import load_from_appname

# Check if pymongo is installed
try:
    from pymongo import MongoClient

    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

sentinel = object()
M = TypeVar('M', bound=BaseModel)

class ConfigDict(SettingsConfigDict, total=False):
    """Extended SettingsConfigDict for TOML-specific settings.

    Attributes:
        appname (str): The name of the application.
        toml_table_header (str): Header for the TOML table.
    """

    appname: str
    toml_table_header: str
    mongo_uri: str
    mongo_database: str
    mongo_collection: str
    mongo_query: dict[str, Any]


class ConfigSource(ABC):
    @abstractmethod
    def load_config(self) -> Config: ...

    @abstractmethod
    def update_config(self, updates: Dict[str, Any]) -> None: ...

    @abstractmethod
    def refresh_config(self) -> Config: ...


@dataclass
class TomlConfigSource(ConfigSource):
    toml_file: Optional[Path]
    appname: Optional[str]
    toml_table_header: str = ""

    def load_config(self) -> Config:
        if self.toml_file and self.appname:
            cfg = load_from_appname(appname=self.appname, file=self.toml_file)
        elif self.toml_file:
            cfg = load_config(self.toml_file)
        elif self.appname:
            cfg = load_config(self.appname)
        else:
            raise ValueError("Either toml_file or appname must be provided")

        if self.toml_table_header:
            try:
                cfg = cfg.get_nested(self.toml_table_header)
            except KeyError:
                raise KeyError(
                    f"toml_table_header '{self.toml_table_header}' not found in config {cfg.provenance[-1].source}"
                )

        return cfg

    def update_config(self, updates: dict[str, Any]) -> None:
        if not self.toml_file:
            raise ValueError("Cannot update config: No TOML file specified")

        current_config = toml.load(self.toml_file)

        if self.toml_table_header:
            table = current_config
            for key in self.toml_table_header.split("."):
                table = table.setdefault(key, {})
            table.update(updates)
        else:
            current_config.update(updates)

        with open(self.toml_file, "w") as f:
            toml.dump(current_config, f)

    def refresh_config(self) -> Config:
        return self.load_config()


if MONGODB_AVAILABLE:
    from pymongo import MongoClient

    @dataclass
    class MongoConfigSource(ConfigSource):
        mongo_uri: str
        mongo_database: str
        mongo_collection: str
        mongo_query: dict[str, Any]
        _id: ObjectId = field(init=False)

        def _extract_hostname(self, uri: str) -> str:
            match = re.search(r"@([^/:]+)", uri)
            return match.group(1) if match else "unknown-host"

        def load_config(self) -> Config:
            client: MongoClient = MongoClient(self.mongo_uri)
            try:
                db = client[self.mongo_database]
                collection = db[self.mongo_collection]
                config = collection.find_one(self.mongo_query)
                if config is None:
                    hostname = self._extract_hostname(self.mongo_uri)
                    raise ValueError(
                        f"No configuration found in mongodb+srv://{hostname} "
                        f"{self.mongo_database}.{self.mongo_collection} query: {self.mongo_query}"
                    )
                if config:
                    self._id = ObjectId(config.pop("_id"))
                return Config(config)
            finally:
                client.close()

        def update_config(self, updates: dict[str, Any]) -> None:
            if self._id is None:
                raise ValueError("No document ID available. Make sure to load the config first.")

            client: MongoClient = MongoClient(self.mongo_uri)
            try:
                db = client[self.mongo_database]
                collection = db[self.mongo_collection]

                update_result = collection.update_one({"_id": self._id}, {"$set": updates})

                if update_result.matched_count == 0:
                    raise ValueError(f"No document found with ID {self._id}")
            finally:
                client.close()

        def refresh_config(self) -> Config:
            return self.load_config()

        def insert_config(self, insert: dict[str, Any]) -> ObjectId:
            client: MongoClient = MongoClient(self.mongo_uri)
            try:
                db = client[self.mongo_database]
                collection = db[self.mongo_collection]
                insert_result = collection.insert_one(insert)
                self._id = insert_result.inserted_id
                return self._id
                # return Config.from_dict(self.mongo_query)
            finally:
                client.close()


class ConfigSettings(BaseSettings):
    """Main class for handling configuration settings.

    Attributes:
        model_config (ConfigDict): Configuration for the model.
    """

    model_config = ConfigDict(toml_table_header="")
    _config_source: ConfigSource = PrivateAttr(default=None)

    def __init__(self, *args, **kwargs):
        specified_vars = [
            "toml_file",
            "appname",
            "toml_table_header",
            "mongo_uri",
            "mongo_database",
            "mongo_collection",
        ]
        if kwargs and not any(var in kwargs for var in specified_vars + ["model_config"]):
            return super().__init__(*args, **kwargs)

        model_config = kwargs.pop("model_config", self.model_config)
        for var in specified_vars:
            val = kwargs.pop(var, sentinel)
            if val is not sentinel:
                model_config[var] = val

        _config_source = self._get_config_source(model_config)
        try:
            cfg = _config_source.load_config()
        except Exception as e:
            ## Add class name to error message
            e.args = (f"{self.__class__.__name__}: {e.args[0] if e.args else ''}",) + e.args[1:]
            raise
        try:
            self._parse_nested_objects(cfg)
            super().__init__(*args, **cfg, **kwargs)
            self._config_source = _config_source
        finally:
            pass

    @classmethod
    def _from_toml(
        cls,
        toml_file: Optional[Path] = None,
        appname: Optional[str] = None,
        toml_table_header: str = "",
    ):
        config_source = TomlConfigSource(toml_file, appname, toml_table_header)
        return cls(config_source)

    @classmethod
    def _from_mongodb(
        cls, mongo_uri: str, mongo_database: str, mongo_collection: str, mongo_query: dict[str, Any]
    ):
        if not MONGODB_AVAILABLE:
            raise ImportError(
                "MongoDB support requires pymongo to be installed. Please install it with 'pip install pymongo'."
            )
        config_source = MongoConfigSource(mongo_uri, mongo_database, mongo_collection, mongo_query)
        return cls(config_source)

    @staticmethod
    def from_config(model_class: Type[M], **kwargs) -> M:
        # Create a temporary class that inherits from both ConfigSettings and the model_class
        class TempConfigModel(ConfigSettings, model_class):  # type: ignore
            pass

        # Use this temporary class to load the configuration
        config_settings = TempConfigModel(**kwargs)

        # Extract only the fields defined in the original model_class
        model_fields = {
            field: getattr(config_settings, field) for field in model_class.model_fields
        }

        # Validate and return an instance of the original model_class
        return model_class.model_validate(model_fields)

    def _update(self, updates: dict[str, Any]) -> None:
        self._config_source.update_config(updates)
        self.__dict__.update(updates)

    def _refresh(self) -> None:
        new_config = self._config_source.refresh_config()
        self.__dict__.update(new_config)

    def _get_config_source(self, model_config: ConfigDict) -> ConfigSource:
        if "mongo_uri" in model_config:
            if MONGODB_AVAILABLE:
                for key in ["mongo_uri", "mongo_database", "mongo_collection"]:
                    if key not in model_config:
                        raise ValueError(f"MongoDB configuration requires {key} to be provided")
                mongo_uri = model_config["mongo_uri"]
                mongo_database = model_config["mongo_database"]  # type: ignore
                mongo_collection = model_config["mongo_collection"]  # type: ignore
                mongo_query = model_config["mongo_query"]  # type: ignore

                return MongoConfigSource(mongo_uri, mongo_database, mongo_collection, mongo_query)
            else:
                raise ImportError(
                    "MongoDB support requires pymongo to be installed. Please install it with 'pip install pymongo'."
                )
        elif "toml_file" in model_config or "appname" in model_config:
            toml_file = model_config.get("toml_file")
            if toml_file:  ## Toml file is a PathType (which includes tuples and lists)
                if isinstance(toml_file, (list, tuple)):
                    toml_file = Path(*toml_file).expanduser()
                else:
                    toml_file = Path(toml_file).expanduser()
            appname = model_config.get("appname")
            toml_table_header = model_config.get("toml_table_header", "")

            if not (toml_file or appname):
                raise ValueError("Either TOML file or appname must be provided")
            assert toml_file is None or isinstance(toml_file, Path)
            return TomlConfigSource(
                toml_file=toml_file,
                appname=appname,
                toml_table_header=toml_table_header,
            )
        else:
            raise ValueError("Either TOML or MongoDB configuration must be provided")

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
    def _create_temp_toml_file(cls, config: Config) -> str:
        """Create a temporary TOML file from the given configuration.

        Args:
            config (Config): The configuration object.

        Returns:
            str: The path to the created temporary TOML file.
        """
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".toml", delete=False) as temp_file:
            toml.dump(config, temp_file)
            return temp_file.name

    def _parse_nested_objects(self, config_dict: Dict[str, Any]):
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
