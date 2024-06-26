
test::
	python -m unittest

build::
	poetry build

publish:: build
	poetry publish