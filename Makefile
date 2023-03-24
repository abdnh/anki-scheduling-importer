.PHONY: all zip clean format mypy pylint fix
all: zip

PACKAGE_NAME := scheduling_importer

zip: $(PACKAGE_NAME).ankiaddon

$(PACKAGE_NAME).ankiaddon: src/*
	rm -f $@
	rm -rf src/__pycache__
	rm -rf src/meta.json
	( cd src/; zip -r ../$@ * )

fix:
	python -m black src
	python -m isort src

mypy:
	python -m mypy src

pylint:
	python -m pylint src

clean:
	rm -f $(PACKAGE_NAME).ankiaddon
