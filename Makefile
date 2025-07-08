# Makefile for DuoScience Client

.PHONY: build publish clean

build:
	python setup.py sdist bdist_wheel

publish: build
	twine upload dist/*

clean:
	rm -rf build dist *.egg-info
