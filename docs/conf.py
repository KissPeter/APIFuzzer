#!/usr/bin/env python3
import os
import sys

from mock import Mock as MagicMock

from apifuzzer.__init__ import __version__ as version
from apifuzzer.version import PROJECT

path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
sys.path.insert(0, path)


class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return Mock()

    @classmethod
    def __getitem__(cls, name):
        return Mock()


MOCK_MODULES = ['pycurl']
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

project = PROJECT
version = version
master_doc = "index"
copyright = "All rights reserved"
extensions = [
    "sphinx.ext.autodoc",  # automatically include and render docstrings from code
    "sphinx.ext.intersphinx",  # required to be able to link to Python standard documentation
    "sphinx.ext.viewcode",  # add links to highlighted source code
]

# Required to be able to link to Python standard documentation
intersphinx_mapping = {'python': ('https://docs.python.org/2', None)}

# Exclude the given files from documentation generation
exclude_patterns = [
]

primary_domain = 'py'
default_role = 'py:obj'
autodoc_member_order = "bysource"
autoclass_content = "both"
add_module_names = False
html_show_sourcelink = False

# Path to static files which will be copied over to html folder when building
html_static_path = ['_static']

# Without this line sphinx includes a copy of object.__init__'s docstring
# on any class that doesn't define __init__.
# https://bitbucket.org/birkenfeld/sphinx/issue/1337/autoclass_content-both-uses-object__init__
autodoc_docstring_signature = False
coverage_skip_undoc_in_source = True
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
# On RTD we can't import sphinx_rtd_theme, but it will be applied by
# default anyway.  This block will use the same theme when building locally
if not on_rtd:
    import sphinx_rtd_theme

    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    html_style = 'css/custom.css'

"""
Documentation update:
- remove *.rst under docs except index.rst
- run: sphinx-apidoc apifuzzer/ -o docs/
"""
