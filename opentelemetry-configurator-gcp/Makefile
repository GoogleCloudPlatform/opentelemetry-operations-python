.PHONY: all build test clean lint install

all: build test lint

build:
	./tools/build.sh

test:
	./tools/test.sh

lint:
	./tools/lint.sh

install: build
	pip install dist/*.whl

clean:
	rm -rf .build
	rm -rf dist
	rm -rf .test
	rm -rf .tox
	rm -rf .venv
