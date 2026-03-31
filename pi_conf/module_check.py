import importlib.util


def check_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


has_yaml = check_module("yaml")
has_stdlib_tomllib = check_module("tomllib")
has_toml_package = check_module("toml")
