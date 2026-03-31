
test::
	uv run pytest tests

format::
	uv run toml-sort pyproject.toml

build::
	uv build

publish:: format build
	uv publish