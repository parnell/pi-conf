"""Config"""
import configparser
import json
import logging
import os
from typing import Any

from pi_conf.provenance import Provenance
from pi_conf.provenance import get_provenance_manager as get_pmanager

try:
    import yaml

    has_yaml = True
except:
    has_yaml = False

try:  ## python 3.11+ have toml in the core libraries
    import tomllib

    is_tomllib = True
except:  ## python <3.11 need the toml library
    import toml

    is_tomllib = False
try:
    from platformdirs import site_config_dir
except:

    def site_config_dir(appname):
        return f"~/.config/{appname}"


log = logging.getLogger(__name__)

_attr_dict_dont_overwrite = set([func for func in dir(dict) if getattr(dict, func)])


class AttrDict(dict):
    """Config class, an attr dict that allows referencing by attribute
    Example:
        cfg = Config({"a":1, "b":{"c":3}})
        cfg.a.b.c == cfg["a"]["b"]["c"] # True
    """

    def __init__(self, *args, **kwargs):
        enable_provenance = kwargs.pop("enable_provenance", False)
        get_pmanager().set_enabled(self, enable_provenance)
        super().__init__(*args, **kwargs)
        self.__dict__ = self

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
            get_pmanager().append(self, Provenance("dict"))

    def clear(self) -> None:
        get_pmanager().clear(cfg)
        return super().clear()

    def to_env(
        self,
        d: dict[str, Any] = None,
        recursive: bool = True,
        ignore_complications: bool = True,
        prefix: str = "",
        to_upper: bool = True,
        overwrite: bool = False,
    ):
        def _is_iterable(obj):
            try:
                if isinstance(obj, str):
                    return False
                iter(obj)
                return True
            except TypeError:
                return False

        """recursively export the config to environment variables with the keys as prefixes"""
        if d is None:
            d = self
        for k, v in d.items():
            is_iterable = _is_iterable(v)
            if recursive and isinstance(v, dict):
                self.to_env(
                    d=v,
                    recursive=recursive,
                    ignore_complications=ignore_complications,
                    prefix=f"{k}_",
                    to_upper=to_upper,
                    overwrite=overwrite,
                )
            elif not ignore_complications and is_iterable:
                raise Exception(
                    f"Error! Cannot export iterable to environment variable '{k}' with value {v}"
                )
            else:
                if to_upper:
                    newk = f"{prefix}{k}".upper()
                if os.environ.get(newk) and not overwrite:
                    continue
                if is_iterable:
                    nv = json.dumps(v)
                else:
                    nv = str(v)
                os.environ[newk] = nv

    @classmethod
    def _from_dict(
        cls: "AttrDict", d: dict, _nested_same_class: bool = False, _depth: int = 0
    ) -> "AttrDict":
        """Make an AttrDict object without any keys
        that will overwrite the normal functions of a

        Args:
            cls (AttrDict): Create a new AttrDict object (or subclass)
            d (dict): The dictionary to convert to an AttrDict
            _nested_same_class (bool): If True, nested dicts will be the subclass,
                else they will be AttrDict

        Returns:
            AttrDict: the AttrDict object, or subclass
        """
        cls = cls if _nested_same_class or _depth == 0 else AttrDict

        def _from_list_or_tuple(l):
            ### TODO change to generic iterable
            new_l = []
            for pot_dict in l:
                if isinstance(pot_dict, dict):
                    new_l.append(
                        cls._from_dict(
                            pot_dict, _nested_same_class=_nested_same_class, _depth=_depth + 1
                        )
                    )
                elif isinstance(pot_dict, list) or isinstance(pot_dict, tuple):
                    new_l.append(_from_list_or_tuple(pot_dict))
                else:
                    new_l.append(pot_dict)
            return new_l

        d = cls(**d)
        for k, v in d.items():
            if k in _attr_dict_dont_overwrite:
                raise Exception(f"Error! config key={k} would overwrite a default dict attr/func")
            if isinstance(v, dict):
                d[k] = cls._from_dict(v, _nested_same_class=_nested_same_class, _depth=_depth + 1)
            elif isinstance(v, list) or isinstance(v, tuple):
                d[k] = _from_list_or_tuple(v)
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls: "AttrDict", d: dict, _nested_same_class: bool = False) -> "AttrDict":
        """Make an AttrDict object without any keys
        that will overwrite the normal functions of a

        Args:
            cls (AttrDict): Create a new AttrDict object (or subclass)
            d (dict): The dictionary to convert to an AttrDict
            _nested_same_class (bool): If True, nested dicts will be the subclass,
                else they will be AttrDict

        Raises:
            Exception: _description_

        Returns:
            AttrDict: the AttrDict object, or subclass
        """
        d = cls._from_dict(d, _nested_same_class=_nested_same_class, _depth=0)
        get_pmanager().append(d, Provenance("dict"))

        return d

    @classmethod
    def from_str(
        cls: "AttrDict",
        config_str: str,
        config_type: str = "toml",
        _nested_same_class: bool = False,
    ) -> "AttrDict":
        """Make an AttrDict object from a string

        Args:
            cls (AttrDict): Create a new AttrDict object (or subclass)
            config_str (str): The string to convert to an AttrDict
            config_type (str): The type of string to convert from (toml|json|ini|yaml)
            _nested_same_class (bool): If True, nested dicts will be the subclass,
                else they will be AttrDict

        Raises:
            Exception: _description_

        Returns:
            AttrDict: the AttrDict object, or subclass
        """
        if config_type == "toml":
            if is_tomllib:
                d = tomllib.loads(config_str)
            else:
                d = toml.loads(config_str)
        elif config_type == "json":
            d = json.loads(config_str)
        elif config_type == "ini":
            cfg_parser = configparser.ConfigParser()
            cfg_parser.read_string(config_str)
            d = {}
            for section in cfg_parser.sections():
                d[section] = {}
                for k, v in cfg_parser.items(section):
                    d[section][k] = v
        elif config_type == "yaml":
            if not has_yaml:
                raise Exception(
                    "Error! YAML not installed. If you would like to use YAML with pi-conf, "
                    "install it with 'pip install pyyaml' or 'pip install pi-conf[yaml]"
                )
            d = yaml.safe_load(config_str)
        else:
            raise Exception(f"Error! Unknown config_type '{config_type}'")
        return cls.from_dict(d, _nested_same_class=_nested_same_class)


class Config(AttrDict):
    def __init__(self, *args, **kwargs):
        enable_provenance = kwargs.pop("enable_provenance", True)
        super().__init__(*args, enable_provenance=enable_provenance, **kwargs)


def _load_config_file(path: str, ext: str = None) -> dict:
    """Load a config file from the given path"""
    if ext is None:
        __, ext = os.path.splitext(path)

    if ext == ".toml":
        if is_tomllib:  ## python 3.11+ have toml in the core libraries
            with open(path, "rb") as fp:
                return tomllib.load(fp)
        else:  ## python <3.11 need the toml library
            return toml.load(path)
    elif ext == ".json":
        with open(path, "r") as fp:
            return json.load(fp)
    elif ext == ".ini":
        cfg_parser = configparser.ConfigParser()
        cfg_parser.read(path)
        return cfg_parser
    elif ext == ".yaml":
        if not has_yaml:
            raise Exception(
                "Error! YAML not installed. If you would like to use YAML with pi-conf, "
                "install it with 'pip install pyyaml' or 'pip install pi-conf[yaml]"
            )
        with open(path, "r") as fp:
            return yaml.safe_load(fp)


def read_config_dir(config_file_or_appname: str) -> Config:
    """Read the config.toml file from the config directory
        This will be read the first config found in following directories.
        If multiple config files are found, the first one will be used,
        in this order toml|json|ini|yaml
            - specified config file
            - ~/.config/<appname>/config.(toml|json|ini|yaml)
            - <system config directory>/<appname>/config.(toml|json|ini|yaml)

    Args:
        config_file_or_appname (str): App name for choosing the config directory

    Returns:
        AttrDict: the parsed config file in a dict format
    """
    check_order = [
        config_file_or_appname,
        f"~/.config/{config_file_or_appname}/config.<ext>",
        f"{site_config_dir(appname=config_file_or_appname)}/config.<ext>",
    ]
    for potential_config in check_order:
        for extension in ["toml", "json", "ini", "yaml"]:
            potential_config = potential_config.replace("<ext>", extension)
            potential_config = os.path.expanduser(potential_config)
            if os.path.isfile(potential_config):
                log.debug(f"p-config::config.py: Using '{potential_config}'")
                cfg = _load_config_file(potential_config)
                cfg = Config.from_dict(cfg)
                get_pmanager().set(cfg, Provenance(potential_config))

                return cfg
    log.debug(f"No config file found. Using blank config")
    return Config()


def update_config(appname_path_dict: str | dict) -> Config:
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
    newcfg = load_config(appname_path_dict)
    cfg.update(newcfg, _add_to_provenance=False)
    get_pmanager().extend(cfg, newcfg.provenance)
    get_pmanager().delete(newcfg)
    return cfg


def set_config(appname_path_dict: str | dict) -> Config:
    """Sets the global config.toml to use based on the given appname | path | dict

    Args:
        appname_path_dict (str): Set the config from an appname | path | dict
        Can be passed with the following.
            Dict: updates cfg with the given dict
            str: a path to a (.toml|.json|.ini|.yaml) file
            str: appname to search for the config.toml in the the application config dir

    Returns:
        Config: A config object (an attribute dictionary)
    """
    cfg.clear()

    return update_config(appname_path_dict)


def load_config(appname_path_dict: str | dict) -> Config:
    """Loads a config based on the given appname | path | dict

    Args:
        appname_path_dict (str): Set the config from an appname | path | dict
        Can be passed with the following.
            Dict: updates cfg with the given dict
            str: a path to a (.toml|.json|.ini|.yaml) file
            str: appname to search for the config.toml in the the application config dir

    Returns:
        Config: A config object (an attribute dictionary)
    """
    if isinstance(appname_path_dict, dict):
        newcfg = Config.from_dict(appname_path_dict)
    else:
        newcfg = read_config_dir(appname_path_dict)
    return newcfg


cfg = Config()  ## Our global config
