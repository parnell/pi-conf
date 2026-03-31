# P-Conf

Easy configuration for Python projects. Load TOML, JSON, INI, or YAML from an explicit path, from OS-specific application directories (for example `~/.config/<appname>/config.toml`), or directly from a Python dict, then read values with attribute access (`cfg.section.key`). You can use the built-in singleton, pass `Config` objects around, or integrate with Pydantic via `ConfigSettings`.

## Where config files are searched

By default, discovery checks:

- `~/.config/<appname>/.config.toml`
- `~/.config/<appname>/config.(toml|json|ini|yaml)`
- `<system config directory>/<appname>/.config.toml`
- `<system config directory>/<appname>/config.(toml|json|ini|yaml)`

YAML requires the optional extra, for example: `uv add "pi-conf[yaml]"`.

## Quick start

Example `config.toml`:

```toml
foo = 1
[bar]
a = 2
```

### Single script

```python
from pi_conf import load_config

cfg = load_config(appname="ourappname")
print(cfg.foo)    # 1
print(cfg.bar.a)  # 2
```

### Application package

Set config once (for example in `__init__.py`), then import `cfg` elsewhere:

```python
# __init__.py
from pi_conf import cfg, set_config

set_config("ourappname")
```

```python
# other_module.py
from ourappname import cfg
print(cfg.foo)
```

Each `load_config(...)` call returns a new `Config`. To replace the shared module-level `cfg`, use `set_config(...)`.

## Explicit sources (recommended for clarity)

`load_config(...)` supports exactly one explicit source keyword, and these are usually clearer than the legacy positional argument:

```python
load_config(data={"debug": True})
load_config(path="/etc/myapp/config.toml")
load_config(appname="myapp")
load_config(appname="myapp", file="secrets.toml")  # not `config.<ext>`
```

Do not mix these keywords with each other, or with a positional source, in the same call.

## Other helpers

- **`AttrDict` / `Config`**: nested dicts with attribute access; `Config` adds optional provenance tracking.
- **`Config.load_config(...)`**: merge another config source into an existing `Config`; conflicting top-level keys raise by default, or pass `overwrite=True` to replace them.
- **`get_nested("a.b.c")`**: dot-path access, with optional defaults and list indexing (see tests in `tests/test_nested_get.py`).
- **`AttrDict.from_str(text, "toml"|"json"|"ini"|"yaml")`**: parse config from a string.
- **`to_env()`**: export nested config to environment variables (see `tests/test_config.py`).

## Pydantic (`ConfigSettings`)

Install with your environment’s equivalent of:

```bash
uv sync --extra pydantic
# or ensure pydantic-settings and toml are available for TOML round-trips on Python 3.11+
```

Typical TOML usage is to define a subclass and point it at either an explicit file path or an app name:

```python
from pi_conf import ConfigDict, ConfigSettings


class Settings(ConfigSettings):
    host: str
    port: int

    model_config = ConfigDict(toml_file="/etc/myapp/config.toml")
```

```python
from pi_conf import ConfigDict, ConfigSettings


class Settings(ConfigSettings):
    host: str
    port: int

    model_config = ConfigDict(appname="myapp")
```

You can also load a regular Pydantic model from config with `ConfigSettings.from_config(...)`.

For nested TOML sections, set `toml_table_header`. For MongoDB-backed settings, use `mongo_uri`, `mongo_database`, `mongo_collection`, and `mongo_query` when `pymongo` is installed. See `tests/test_config_settings.py` and `tests/test_config_settings_mongo.py`.

`ConfigSettings` loads without importing `bson` unless MongoDB support is used. Updating TOML on disk uses the PyPI `toml` package (declared with the pydantic dependency group) because the stdlib `tomllib` is read-only.

## Development

- Install the development environment: `uv sync --group dev --all-extras`
- Run tests: `make test` or `uv run pytest tests`
- CI runs on Python 3.9, 3.11, and 3.13 (see `.github/workflows/ci.yml`).
