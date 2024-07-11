
test::
	pytest tests

format::
	toml-sort pyproject.toml

build::
	poetry build

publish:: format build
	poetry publish