SHELL:=$(shell which bash)
parent_dir:=$(shell dirname $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST)))))
.PHONY: all
all: clean
all: apidoc
all: sphinx

SPHINXOPTS= -j 4 -d _build/doctrees .

.PHONY: sphinx
sphinx:
	sphinx-build -b html $(SPHINXOPTS) _build/html

.PHONY: clean
clean:
	rm -rf _build

.PHONY: apidoc
apidoc:
	sphinx-apidoc  ../apifuzzer -f -e -o .

