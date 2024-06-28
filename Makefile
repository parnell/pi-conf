
test::
	pytest tests

build::
	poetry build

publish:: build
	poetry publish