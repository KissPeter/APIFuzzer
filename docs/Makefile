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

builld-pip-package:
	cd ..
	mkdir /tmp/$$
	mv test  # not the best, but setup exclude doesn't work
	find . -name "__pycache __" -exec rm -rf {} \;
	rm -fr  dist/ build/ *.egg-info
	python3 setup.py sdist bdist_wheel
	tar -tvf dist/APIFuzzer-*.tar.gz
	mv /tmp/$$/test .
