"""Config"""
import configparser
import inspect
import json
import logging
import os
from typing import Any

try:
    import yaml

    has_yaml = True
except:
    has_yaml = False

try:  ## python 3.11+ have toml in the core libraries
    import tomllib
except:  ## python 3.10- need the toml library
    import toml as tomllib
try:
    from platformdirs import site_config_dir
except:

    def site_config_dir(appname):
        return f"~/.config/{appname}"


_attr_dict_dont_overwrite = set([func for func in dir(dict) if getattr(dict, func)])


class Config(dict):
    """Config class, an attr dict that allows referencing by attribute
    Example:
        cfg = Config({"a":1, "b":{"c":3}})
        cfg.a.b.c == cfg["a"]["b"]["c"] # True
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__source__: str = None
        self.__dict__ = self

    def to_env(
        self,
        d: dict[str, Any] = None,
        recursive: bool = True,
        ignore_complications: bool = False,
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
            if recursive and isinstance(v, dict):
                self.to_env(d=v, prefix=f"{k}_")
            elif not ignore_complications and _is_iterable(v):
                raise Exception(
                    f"Error! Cannot export iterable to environment variable '{k}' with value {v}"
                )
            else:
                if to_upper:
                    newk = f"{prefix}{k}".upper()
                if os.environ.get(newk) and not overwrite:
                    continue
                os.environ[newk] = str(v)

    @staticmethod
    def make_attr_dict(d: dict):
        """Make an AttrDict (Config) object without any keys
        that will overwrite the normal functions of a

        Args:
            d (dict): _description_

        Raises:
            Exception: _description_

        Returns:
            _type_: _description_
        """
        d = Config(**d)
        for k, v in d.items():
            if k in _attr_dict_dont_overwrite:
                raise Exception(f"Error! config key={k} would overwrite a default dict attr/func")
            if isinstance(v, dict):
                d[k] = make_attr_dict(v)
        return d


def make_attr_dict(d: dict, source: str = None):
    """Make an AttrDict (Config) object without any keys
    that will overwrite the normal functions of a

    Args:
        d (dict): _description_
        source (dict): optional source of the config

    Raises:
        Exception: _description_

    Returns:
        _type_: _description_
    """
    d = Config.make_attr_dict(d)
    d.__source__ = source
    return d


def _load_config_file(path: str) -> dict:
    __, ext = os.path.splitext(path)
    if ext == ".toml":
        with open(path, "rb") as fp:
            return tomllib.load(fp)
    elif ext == ".json":
        with open(path, "r") as fp:
            return json.load(fp)
    elif ext == ".ini":
        cfg = configparser.ConfigParser()
        cfg.read(path)
        return cfg
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
                logging.debug(f"p-config::config.py: Using '{potential_config}'")
                cfg = _load_config_file(potential_config)
                return make_attr_dict(cfg, potential_config)
    logging.debug(f"No config file found. Using blank config")
    return make_attr_dict({})


def update_config(appname_path_dict: str | dict) -> Config:
    """Set the config to use

    Args:
        appname_path_dict (str): Set the config for SQLAlchemy Extensions.
        Can be passed with the following.
            Dict: updates cfg with the given dict
            str: a path to a .toml file
            str: appname to search for the config.toml in the the application config dir

    Returns:
        Config: A config object (an attribute dictionary)
    """
    if isinstance(appname_path_dict, dict):
        newcfg = make_attr_dict(appname_path_dict)
        cfg.__source__ = "dict"
    else:
        newcfg = read_config_dir(appname_path_dict)
        cfg.__source__ = newcfg.__source__
    cfg.update(newcfg)
    return cfg


def load_config(appname_path_dict: str | dict) -> Config:
    """Set the config.toml to use

    Args:
        appname_path_dict (str): Set the config for SQLAlchemy Extensions.
        Can be passed with the following.
            Dict: updates cfg with the given dict
            str: a path to a .toml file
            str: appname to search for the config.toml in the the application config dir

    Returns:
        Config: A config object (an attribute dictionary)
    """
    cfg.clear()
    return update_config(appname_path_dict)


cfg = Config()  ## our config


def _set_log_level(level: str | int, name: str = None):
    """Set logging to the specified level

    Args:
        level (str): log level
    """
    logger = logging.getLogger(name)
    level = logging._nameToLevel.get(level.upper)
    if level and level != logger.level:
        logging.basicConfig(level=level)
        logger.setLevel(level)
        logger.debug(f"p-config: logging set to {level}")


def _get_importer_project_name():
    """Get the name of the project that imported this module
    meant to be used from within a module to get the name of the project automtically"""

    for i in range(len(inspect.stack())):
        frame = inspect.stack()[i]
        module = inspect.getmodule(frame[0])
        if module:
            module_path = os.path.abspath(module.__file__)
            n = os.path.basename(os.path.dirname(module_path))
            if n not in ["pi_conf", "tests", "unittest"]:
                return n
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    if module:
        module_path = os.path.abspath(module.__file__)
        # Parse this path according to your project's structure
        return os.path.basename(os.path.dirname(module_path))
    return None
