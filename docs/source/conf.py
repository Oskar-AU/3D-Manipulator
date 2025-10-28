# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

project = 'Manipulator'
copyright = '2025, Oskar Minds, Laurits Halaburt Jensen, Anders Ravnsholt Riis'
author = 'Oskar Minds, Laurits Halaburt Jensen, Anders Ravnsholt Riis'
release = '0.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.napoleon',      # NumPy docstrings.
    'sphinx.ext.autodoc',       # Allows for autodocumentation.
    'sphinx.ext.autosummary',
    # 'sphinx_autodoc_typehints'
]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']
