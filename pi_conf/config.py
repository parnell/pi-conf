"""Config"""

import configparser
import json
import logging
import os
from typing import Optional, TypeVar

from pi_conf.attr_dict import AttrDict, has_yaml, is_tomllib, site_config_dir
from pi_conf.module_check import has_yaml, is_tomllib
from pi_conf.provenance import Provenance, ProvenanceOp
from pi_conf.provenance import get_provenance_manager as get_pmanager

if has_yaml:
    import yaml
if is_tomllib:
    import tomllib
else:
    import toml

T = TypeVar("T", bound="AttrDict")

log = logging.getLogger(__name__)


class ProvenanceDict(AttrDict):
    """Config class, an attr dict that allows referencing by attribute and also
    tracks provenance information, such as updates and where they were from.
    Example:
        cfg = Config({"a":1, "b":{"c":3}})
        cfg.a.b.c == cfg["a"]["b"]["c"] # True
    """

    def __init__(self, *args, **kwargs):
        enable_provenance = kwargs.pop("enable_provenance", True)
        get_pmanager().set_enabled(self, enable_provenance)

        super().__init__(*args, **kwargs)
        self.__dict__ = self
        get_pmanager().append(self, Provenance("dict", ProvenanceOp.set))

    def __post_init__(self):
        ## Iterate over members and add them to the dict
        members = [
            attr
            for attr in dir(self)
            if not callable(getattr(self, attr)) and not attr.startswith("__")
        ]
        for m in members:
            if m == "provenance":
                continue
            if isinstance(getattr(self, m), dict):
                nd = AttrDict.from_dict(getattr(self, m))
                setattr(self, m, nd)
                self[m] = nd
            else:
                self[m] = getattr(self, m)

    def load_config(
        self,
        appname_path_dict: str | dict,
        directories: Optional[str | list] = None,
    ) -> None:
        """Loads a config based on the given appname | path | dict

        Args:
            appname_path_dict (str): Set the config from an appname | path | dict
            Can be passed with the following.
                Dict: updates cfg with the given dict
                str: a path to a (.toml|.json|.ini|.yaml) file
                str: appname to search for the config.toml in the the application config dir
            directories (Optional[str | list]): Optional list of directories to search
        """
        newcfg = load_config(appname_path_dict, directories=directories)
        self.update(newcfg, _add_to_provenance=False)
        get_pmanager().extend(self, newcfg.provenance)
        get_pmanager().delete(newcfg)

    @property
    def provenance(self) -> list[Provenance]:
        return get_pmanager().get(self)

    def __del__(self):
        """Delete the config from the provenance if this object is deleted"""
        get_pmanager().delete(self)

    def update(self, *args, **kwargs):
        """Update the config with another dict"""
        _add_to_provenance = kwargs.pop("_add_to_provenance", True)
        super().update(*args, **kwargs)
        if _add_to_provenance:
            get_pmanager().append(self, Provenance("dict", ProvenanceOp.update))

    def clear(self) -> None:
        get_pmanager().clear(cfg)
        return super().clear()

    @classmethod
    def from_dict(cls: type[T], d: dict, _nested_same_class: bool = False) -> T:
        """Make an AttrDict object without any keys
        that will overwrite the normal functions of a dict

        Args:
            cls (Type[AttrDict]): Create a new AttrDict object (or subclass)
            d (dict): The dictionary to convert to an AttrDict
            _nested_same_class (bool): If True, nested dicts will be the subclass,
                else they will be AttrDict

        Returns:
            AttrDict: the AttrDict object, or subclass
        """
        ad = cls._from_dict(d, _nested_same_class=_nested_same_class, _depth=0)
        return ad


class Config(ProvenanceDict):
    pass


def _load_config_file(path: str, ext: Optional[str] = None) -> Config:
    """Load a config file from the given path"""
    if ext is None:
        __, ext = os.path.splitext(path)

    if ext == ".toml":
        if is_tomllib:  ## python 3.11+ have toml in the core libraries
            with open(path, "rb") as fp:
                return Config.from_dict(tomllib.load(fp))  # type: ignore
        else:  ## python <3.11 need the toml library
            return Config.from_dict(toml.load(path))  # type: ignore
    elif ext == ".json":
        with open(path, "r") as fp:
            return Config.from_dict(json.load(fp))
    elif ext == ".ini":
        cfg_parser = configparser.ConfigParser()
        cfg_parser.read(path)
        cfg_dict = {section: dict(cfg_parser[section]) for section in cfg_parser.sections()}
        return Config.from_dict(cfg_dict)
    elif ext == ".yaml":
        if not has_yaml:
            raise Exception(
                "Error! YAML not installed. If you would like to use YAML with pi-conf, "
                "install it with 'pip install pyyaml' or 'pip install pi-conf[yaml]"
            )
        with open(path, "r") as fp:
            return Config.from_dict(yaml.safe_load(fp))  # type: ignore
    raise Exception(f"Error! Unknown config file extension '{ext}'")


def _find_config(
    config_file_or_appname: str, directories: Optional[str | list] = None
) -> Optional[str]:
    """Find the config file from the config directory
        This will be read the first config found in following directories.
        If multiple config files are found, the first one will be used,
        in this order toml|json|ini|yaml
            - specified config file
            - ~/.config/<appname>/config.(toml|json|ini|yaml)
            - <system config directory>/<appname>/config.(toml|json|ini|yaml)

    Args:
        config_file_or_appname (str): App name for choosing the config directory
        directories (Optional[str | list]): Optional list of directories to search

    Returns:
        str: the path to the config file
    """
    _, ext = os.path.splitext(config_file_or_appname)
    is_file = bool(ext)

    default_file_name = "config" if not is_file else config_file_or_appname
    file_name_str = f"{default_file_name}.<ext>" if not is_file else config_file_or_appname

    if directories is None:
        check_order = [
            config_file_or_appname,
            f"~/.config/{config_file_or_appname}/{file_name_str}",
            f"{site_config_dir(appname=config_file_or_appname)}/{file_name_str}",
        ]
    elif isinstance(directories, str):
        directories = os.path.expanduser(directories)
        check_order = [
            f"{directories}/{file_name_str}",
        ]
    else:
        check_order = [f"{os.path.expanduser(d)}/{file_name_str}" for d in directories]
    for potential_config in check_order:
        if is_file:
            if os.path.exists(potential_config):
                log.debug(f"Found config: '{potential_config}'")
                return potential_config
        else:
            for extension in ["toml", "json", "ini", "yaml"]:
                potential_config = potential_config.replace("<ext>", extension)
                potential_config = os.path.expanduser(potential_config)
                if os.path.isfile(potential_config):
                    log.debug(f"Found config: '{potential_config}'")
                    return potential_config
    log.debug(f"No config file found.")
    return None


def update_config(appname_path_dict: str | dict, directories: Optional[str | list[str]]) -> Config:
    """Update the global config with another config

    Args:
        appname_path_dict (str): Set the config from an appname | path | dict
        Can be passed with the following.
            Dict: updates cfg with the given dict
            str: a path to a (.toml|.json|.ini|.yaml) file
            str: appname to search for the config.toml in the the application config dir

    Returns:
        Config: A config object (an attribute dictionary)
    """
    newcfg = load_config(appname_path_dict, directories=directories)
    cfg.update(newcfg, _add_to_provenance=False)
    get_pmanager().extend(cfg, newcfg.provenance)
    get_pmanager().delete(newcfg)
    return cfg


def set_config(
    appname_path_dict: Optional[str | dict] = None,
    create_if_not_exists: bool = True,
    create_with_extension=".toml",
    directories: Optional[str | list] = None,
) -> Config:
    """Sets the global config.toml to use based on the given appname | path | dict

    Args:
        appname_path_dict (str): Set the config from an appname | path | dict
            Can be passed with the following.
                Dict: updates cfg with the given dict
                str: a path to a (.toml|.json|.ini|.yaml) file
                str: appname to search for the config.toml in the the application config dir
        create_if_not_exists (bool): If True, and appname_path_dict is a path, create the config file if it doesn't exist
        create_with_extension (str): The extension to use if creating the config file
        directories (Optional[str | list]): Optional list of directories to search

    Returns:
        Config: A config object (an attribute dictionary)
    """
    if appname_path_dict is None:
        appname_path_dict = ".config.toml"

    cfg.clear()
    if create_if_not_exists and isinstance(appname_path_dict, str):
        path = _find_config(appname_path_dict, directories=directories)
        if path is None:
            if not isinstance(appname_path_dict, str):
                raise Exception("Error! appname_path_dict must be a string to create a config file")

            if directories is not None:
                if isinstance(directories, str):
                    directories = [directories]
                path = directories[0]
            else:
                path = site_config_dir(appname=appname_path_dict)
            path = os.path.join(path, appname_path_dict, f"config{create_with_extension}")
            os.makedirs(os.path.dirname(path), exist_ok=True)

            log.info(f"Creating config file at '{path}' for appname '{appname_path_dict}'")
            with open(path, "w") as fp:
                fp.write("")
            directories = [os.path.dirname(path)]
    return update_config(appname_path_dict, directories=directories)


def load_from_dict(d: dict) -> Config:
    """Load a config from a dict"""
    return Config.from_dict(d)


def load_from_appname(appname: str, directories: Optional[str | list] = None) -> Config:
    """Load a config from an appname"""
    path = _find_config(appname, directories=directories)
    if path is None:
        log.warning(f"No config file found for appname '{appname}'")
        log.warning(f"You can create a config file at '{site_config_dir(appname=appname)}'")
        raise FileNotFoundError(f"No config file found for '{appname}'")
    return load_from_path(path)


def load_from_path(path: str, directories: Optional[str | list] = None) -> Config:
    """Load a config from a file path"""
    full_path = _find_config(path, directories=directories)
    if full_path is None:
        raise FileNotFoundError(f"No config file found at '{path}' or in provided directories")
    newcfg = _load_config_file(full_path)
    get_pmanager().set(newcfg, Provenance(full_path, ProvenanceOp.set))
    return newcfg


def load_config(
    appname_path_dict: Optional[str | dict] = None,
    directories: Optional[str | list] = None,
    ignore_warnings: bool = False,
) -> Config:
    """Loads a config based on the given appname | path | dict

    Args:
        appname_path_dict (str | dict): Set the config from an appname | path | dict
        Can be passed with the following:
            Dict: updates cfg with the given dict
            str: a path to a (.toml|.json|.ini|.yaml) file
            str: appname to search for the config.toml in the application config dir
        directories (Optional[str | list]): Optional list of directories to search
        ignore_warnings (bool): If True, suppress warnings and return an empty Config for missing files

    Returns:
        Config: A config object (an attribute dictionary)
    """
    if appname_path_dict is None:
        appname_path_dict = ".config.toml"

    if isinstance(appname_path_dict, dict):
        return load_from_dict(appname_path_dict)

    try:
        return load_from_path(appname_path_dict, directories)
    except FileNotFoundError:
        # If it's not found as a direct path, try as an appname
        try:
            return load_from_appname(appname_path_dict, directories)
        except FileNotFoundError:
            if ignore_warnings:
                return Config.from_dict({})
            raise


cfg = Config()  ## Our global config
