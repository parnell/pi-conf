import importlib.util


def check_module(module_name):
    return importlib.util.find_spec(module_name) is not None


has_yaml = check_module("yaml")
is_tomllib = check_module("tomllib")

if not is_tomllib:
    is_tomllib = check_module("toml")
