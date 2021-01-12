#!/usr/bin/env python
import codecs
import os.path
import re
from os import path

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',  # It excludes inline comment too
    open("apifuzzer/__init__.py").read(),
).group(1)

REQUIREMENTS_FILE_PATH = path.join(
    path.abspath(path.dirname(__file__)), "requirements.txt"
)


def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()


with open(REQUIREMENTS_FILE_PATH, "r") as f:
    REQUIREMENTS_FILE = [
        line
        for line in f.read().splitlines()
        if not line.startswith("#") and not line.startswith("--")
    ]

setup_options = dict(
    name='APIFuzzer',
    version=__version__,
    description='Fuzz test your application using Swagger or OpenAPI definition without coding',
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    author='Peter Kiss',
    author_email='peter.kiss@linuxadm.hu',
    url='https://github.com/KissPeter/APIFuzzer/',
    scripts=['APIFuzzer'],
    packages=find_packages(exclude=["test"]),
    install_requires=REQUIREMENTS_FILE,
    license="GNU General Public License v3.0",
    classifiers=[  # https://pypi.org/classifiers/
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='Fuzz test, QA, Software Quality Assurance, Security testing, Swagger, OpenAPI',
    python_requires='>=3.6, <4',
    package_data={"apifuzzer": ['fuzzer_target/*.py']},
    exclude_package_data={"test": ["*"]}
)

setup(**setup_options)

"""
Preparation instructions: https://packaging.python.org/tutorials/packaging-projects/
"""
