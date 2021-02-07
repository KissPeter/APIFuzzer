#!/usr/bin/env python3
"""
Preparation instructions: https://packaging.python.org/tutorials/packaging-projects/
"""
import os.path
import re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    open("apifuzzer/__init__.py").read(),
).group(1)


def get_readme():
    readme = list()
    with open(os.path.join(here, "README.md"), "r") as f:
        skip_lines = True
        for line in f.read().splitlines():
            if line.startswith('# APIFuzzer — HTTP API Testing Framework'):
                skip_lines = False
            if skip_lines:
                continue
            else:
                readme.append(line)
    return '\n'.join(readme)


def get_requirements():
    requirements = list()
    with open(os.path.join(here, "requirements.txt"), "r") as f:
        for line in f.read().splitlines():
            if not line.startswith("#") and not line.startswith("--"):
                requirements.append(line)
    return '\n'.join(requirements)


setup_options = dict(
    name='APIFuzzer',
    version=__version__,
    description='Fuzz test your application using Swagger or OpenAPI definition without coding',
    long_description=get_readme(),
    long_description_content_type="text/markdown",
    author='Peter Kiss',
    author_email='peter.kiss@linuxadm.hu',
    url='https://github.com/KissPeter/APIFuzzer/',
    scripts=['APIFuzzer'],
    packages=find_packages(exclude=["test"]),
    install_requires=get_requirements(),
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
