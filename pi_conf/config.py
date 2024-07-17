"""Config"""

import configparser
import json
import logging
import os
from typing import Any, Iterable, Literal, Optional, TypeVar, cast

from pi_conf.provenance import Provenance, ProvenanceOp
from pi_conf.provenance import get_provenance_manager as get_pmanager

try:
    import yaml  # type: ignore

    has_yaml = True
except:
    has_yaml = False

try:  ## python 3.11+ have toml in the core libraries
    import tomllib

    is_tomllib = True
except:  ## python <3.11 need the toml library
    import toml  # type: ignore

    is_tomllib = False
try:
    from platformdirs import site_config_dir
except:

    def site_config_dir(
        appname: str | None = None,
        appauthor: str | None | Literal[False] = None,
        version: str | None = None,
        multipath: bool = False,  # noqa: FBT001, FBT002
        ensure_exists: bool = False,  # noqa: FBT001, FBT002
    ) -> str:
        return f"~/.config/{appname}"


T = TypeVar("T", bound="AttrDict")

log = logging.getLogger(__name__)

sentinel = object()
_attr_dict_dont_overwrite = set([func for func in dir(dict) if getattr(dict, func)])


def _is_iterable_with_type(obj):
    try:
        if isinstance(obj, str):
            return False, None
        elif isinstance(obj, dict):
            return True, dict
        elif isinstance(obj, list):
            return True, list
        iter(obj)
        return True, None
    except TypeError:
        return False, None


class AttrDict(dict):
    """A dictionary class that allows referencing by attribute
    Example:
        d = AttrDict({"a":1, "b":{"c":3}})
        d.a.b.c == d["a"]["b"]["c"] # True
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def __post_init__(self):
        ## Iterate over members and add them to the dict
        members = [
            attr
            for attr in dir(self)
            if not callable(getattr(self, attr)) and not attr.startswith("__")
        ]
        for m in members:
            if isinstance(getattr(self, m), dict):
                nd = AttrDict.from_dict(getattr(self, m))
                setattr(self, m, nd)
                self[m] = nd
            else:
                self[m] = getattr(self, m)

    def __getattribute__(self, name: str) -> Any:
        """Get an attribute from the dictionary.
        This will allow you to access the dictionary keys as attributes.
        Returning Any removes MyPy errors."""
        return super().__getattribute__(name)

    def update(self, *args, **kwargs):
        """Update the config with another dict"""
        if "_no_attrdict" in kwargs:
            kwargs.pop("_no_attrdict")
            super().update(*args, **kwargs)
            return

        super().update(*args, **kwargs)
        AttrDict._from_dict(self, _depth=0, inline=True)

    def get_nested(
        self,
        keys: str,
        default: Any = sentinel,
        list_item: Optional[int] = 0,
        split_delimiter: str = ".",
    ) -> Any:
        """
        Get a nested value from the dictionary. Only works with string keys
        Args:
            keys (str): The keys to get from the dictionary
            default (Any): The default value if the key is not found
            list_item (int): If the key is a list, get the item at the index,
                set to None to disable
        Returns:
            Any: The value of the key

        Example:
            d = AttrDict({"a":1, "b":{"c":3}})
            d.get_nested('a') == 1
            d.get_nested('b.c') == 3
            d.get_nested('b.d', 'default') == 'default'
            d.get_nested('x.y.z', None) == None
            d.get_nested("notfound") # raises KeyError
        """
        current = self
        for key in keys.split(split_delimiter):
            if isinstance(current, dict):
                if key in current:
                    current = current[key]
                elif default is not sentinel:
                    return default
                else:
                    raise KeyError(f"Key not found: '{key}'")
            elif list_item is not None and isinstance(current, list):
                if list_item < len(current):
                    current = current[list_item]
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    elif default is not sentinel:
                        return default
                    else:
                        raise KeyError(f"Key not found: '{key}'")
                else:
                    if default is not sentinel:
                        return default
                    else:
                        raise KeyError(
                            f"'{key}', List index out of range: idx={list_item}, len={len(current)}"
                        )
            elif default is not sentinel:
                return default
            else:
                raise KeyError(f"'{key}' is not a nested dictionary")
        return current

    def to_env(
        self,
        recursive: bool = True,
        to_upper: bool = True,
        overwrite: bool = False,
        ignore_complications: bool = True,
    ) -> list[str | Any]:
        """recursively export the config to environment variables
        with the keys as prefixes
        args:
            d (dict): The dictionary to convert to an AttrDict
            recursive (bool): If True, recursively convert the dictionary to environment variables
            to_upper (bool): If True, convert the keys to uppercase
            overwrite (bool): If True, overwrite existing environment variables
            ignore_complications (bool): If True, ignore any complications in the dictionary
        returns:
            list: A list of tuples of the environment variables added
        """
        return self._to_env(
            recursive=recursive,
            to_upper=to_upper,
            overwrite=overwrite,
            ignore_complications=ignore_complications,
        )

    def _to_env(
        self,
        d: Optional[str | list[Any] | dict[str, Any] | Iterable] = None,
        recursive: bool = True,
        to_upper: bool = True,
        overwrite: bool = False,
        ignore_complications: bool = True,
        prefix: str = "",
        path: Optional[list] = None,
    ) -> list[str | Any]:
        """recursively export the config to environment variables
        with the keys as prefixes
        """
        if not path:
            path = []
        added_envs: list[str | Any] = []
        if d is None:
            d = self
        is_iterable, iterable_type = _is_iterable_with_type(d)
        if not is_iterable:
            v = json.dumps(d) if not isinstance(d, str) else d

            newk = "_".join(path)
            if to_upper:
                newk = newk.upper()
            if not os.environ.get(newk) or overwrite:
                os.environ[newk] = v
                added_envs.append((newk, v))
        elif iterable_type == dict:
            d = cast(dict[str, Any], d)
            for k, v in d.items():
                np = path.copy()
                np.append(k)
                a = self._to_env(
                    d=v,
                    recursive=recursive,
                    to_upper=to_upper,
                    overwrite=overwrite,
                    ignore_complications=ignore_complications,
                    prefix=f"{prefix}{k}",
                    path=np,
                )
                added_envs.extend(a)
        elif iterable_type == list:
            for i, v in enumerate(d):
                np = path[:-1].copy()
                np.append(f"{prefix}{i}")
                a = self._to_env(
                    d=v,
                    recursive=recursive,
                    to_upper=to_upper,
                    overwrite=overwrite,
                    ignore_complications=ignore_complications,
                    path=np,
                )
                added_envs.extend(a)
        elif not ignore_complications and is_iterable:
            raise Exception(f"Error! Cannot export iterable to environment variable d={d}")

        return added_envs

    @classmethod
    def _from_dict(
        cls: type[T],
        d: dict,
        _nested_same_class: bool = False,
        _depth: int = 0,
        inline: bool = False,
    ) -> T:
        """Make an AttrDict object without any keys
        that will overwrite the normal functions of a dict

        Args:
            cls (AttrDict): Create a new AttrDict object (or subclass)
            d (dict): The dictionary to convert to an AttrDict
            _nested_same_class (bool): If True, nested dicts will be the subclass,
                else they will be AttrDict

        Returns:
            AttrDict: the AttrDict object, or subclass
        """
        if not (_nested_same_class or _depth == 0):
            cls = AttrDict

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

        if not inline:
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
    def from_dict(
        cls: type["AttrDict"],
        d: dict,
        _nested_same_class: bool = False,
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
        return cls._from_dict(d, _nested_same_class=_nested_same_class, _depth=0)

    @classmethod
    def from_str(
        cls: type["AttrDict"],
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
                d = tomllib.loads(config_str)  # type: ignore
            else:
                d = toml.loads(config_str)  # type: ignore
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
                    'install it with `pip install pyyaml` or `pip install "pi-conf[yaml]"`'
                )
            d = yaml.safe_load(config_str)  # type: ignore
        else:
            raise Exception(f"Error! Unknown config_type '{config_type}'")
        return cls.from_dict(d, _nested_same_class=_nested_same_class)


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


def load_config(
    appname_path_dict: Optional[str | dict] = None,
    directories: Optional[str | list] = None,
    ignore_warnings: bool = False,
) -> Config:
    """Loads a config based on the given appname | path | dict

    Args:
        appname_path_dict (str): Set the config from an appname | path | dict
        Can be passed with the following.
            Dict: updates cfg with the given dict
            str: a path to a (.toml|.json|.ini|.yaml) file
            str: appname to search for the config.toml in the the application config dir
        directories (Optional[str | list]): Optional list of directories to search

    Returns:
        Config: A config object (an attribute dictionary)
    """
    if appname_path_dict is None:
        appname_path_dict = ".config.toml"
    if isinstance(appname_path_dict, dict):
        newcfg = Config.from_dict(appname_path_dict)
    else:
        path = _find_config(appname_path_dict, directories=directories)
        if path is None:
            if not ignore_warnings:
                log.warning(f"No config file found for appname '{appname_path_dict}'")
                log.warning(
                    f"You can create a config file at '{site_config_dir(appname=appname_path_dict)}'"
                )
                raise FileNotFoundError(f"No config file found for '{appname_path_dict}'")
            newcfg = Config.from_dict({})
        else:
            newcfg = _load_config_file(path)
            get_pmanager().set(newcfg, Provenance(path, ProvenanceOp.set))

    return newcfg


cfg = Config()  ## Our global config
