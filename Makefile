.PHONY: all zip clean format mypy pylint fix vendor
all: zip

PACKAGE_NAME := scheduling_importer

zip: build/$(PACKAGE_NAME).ankiaddon

build/$(PACKAGE_NAME).ankiaddon: src/*
	rm -f $@
	rm -rf src/__pycache__
	rm -rf src/meta.json
	mkdir -p build
	( cd src/; zip -r ../$@ * )

fix:
	python -m black src --exclude="vendor"
	python -m isort src

mypy:
	python -m mypy src

pylint:
	python -m pylint src

vendor:
	./vendor.sh

clean:
	rm -rf build/
