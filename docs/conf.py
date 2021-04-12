# Copyright 2021 Google
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = "Google Cloud OpenTelemetry"
copyright = "2020, Google"
author = "Google"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # API doc generation
    "sphinx.ext.autodoc",
    # Automatically generate autodoc API docs
    "sphinx.ext.autosummary",
    # Support for google-style docstrings
    "sphinx.ext.napoleon",
    # Infer types from hints instead of docstrings
    "sphinx_autodoc_typehints",
    # Add links to source from generated docs
    "sphinx.ext.viewcode",
    # Link to other sphinx docs
    "sphinx.ext.intersphinx",
    # Add a .nojekyll file to the generated HTML docs
    # https://help.github.com/en/articles/files-that-start-with-an-underscore-are-missing
    "sphinx.ext.githubpages",
    # Support external links to different versions in the Github repo
    "sphinx.ext.extlinks",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "opentelemetry": (
        "https://opentelemetry-python.readthedocs.io/en/latest/",
        None,
    ),
}

autosummary_generate = True  # automatically generate autodoc stubs

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**/venv"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_theme_options = {
    "github_repo": "opentelemetry-operations-python",
    "github_user": "GoogleCloudPlatform",
    "page_width": "1400px",
    "sidebar_width": "320px",
    "body_max_width": "800px",
}
