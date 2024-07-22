import configparser
import json
import logging
import os
from typing import Any, Iterable, Literal, Optional, TypeVar, cast

from pi_conf.module_check import has_yaml, is_tomllib
from pi_conf.provenance import Provenance, ProvenanceOp
from pi_conf.provenance import get_provenance_manager as get_pmanager

if has_yaml:
    import yaml
if is_tomllib:
    import tomllib
else:
    import toml


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
