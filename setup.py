#!/usr/bin/env python
import codecs
import os.path
import re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


install_requires = [
    'kittyfuzzer==0.7.4',
    'pycurl==7.43.0.5',
    'ruamel.yaml==0.16.7',
    'junit-xml==1.8'
]

setup_options = dict(
    name='APIFuzzer',
    version=find_version("awscli", "__init__.py"),
    description='Fuzz test your application using API definition without coding',
    long_description=read('README.md'),
    author='Péter Kiss',
    url='https://github.com/KissPeter/APIFuzzer/',
    scripts=['bin/APIFuzzer'],
    packages=find_packages(exclude=['tests*']),
    package_data={'apifuzzer': ['apifuzzer/fuzzer_target/*.py', 'apifuzzer/fuzzer_target/*py']},
    install_requires=install_requires,
    extras_require={},
    license="GNU General Public License v3.0",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)

setup(**setup_options)
