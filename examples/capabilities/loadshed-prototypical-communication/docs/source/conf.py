# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../../R1-12.47-1-substation'))
print(sys.path)
sys.setrecursionlimit(1500)


# -- Project information -----------------------------------------------------

project = 'TESP'
copyright = '2021, Laurentiu Marinovici'
author = 'Laurentiu Marinovici \\and PNNL'

# The full version, including alpha/beta/rc tags
release = '1.0.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
    'sphinx.ext.imgmath',
    'sphinx.ext.githubpages',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    #'rinoh.frontend.sphinx']#,
   'sphinx-jsonschema',
   'sphinxcontrib.bibtex'
   ]

bibtex_bibfiles = ['../references/refs.bib']
bibtex_default_style = 'unsrt'

todo_include_todos = True
numfig = True

# The master toctree document.
master_doc = 'index'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'
# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'classic'
# html_theme = 'alabaster'
html_theme = 'sphinx_rtd_theme'
# html_theme = 'bizstyle'
# html_theme = 'agogo'
# pagewidth = 1200

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['../_static']
html_context = {
    'css_files': [
        '_static/css/custom_style.css',
        ],
     }

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    'preamble': r'''
      \usepackage[titles]{tocloft}
      \cftsetpnumwidth {1.25cm}\cftsetrmarg{1.5cm}
      \setlength{\cftchapnumwidth}{0.75cm}
      \setlength{\cftsecindent}{\cftchapnumwidth}
      \setlength{\cftsecnumwidth}{1.25cm}
      \usepackage{amsmath, amssymb, amsthm, enumerate, datetime, epsfig, amsthm, sidecap, latexsym}
      \usepackage{dsfont,verbatim,paralist,indentfirst, listings, pdflscape}
      ''',
    'fncychap': r'\usepackage[Bjornstrup]{fncychap}',
    'printindex': r'\footnotesize\raggedright\printindex',
    # Latex figure (float) alignment
    #
    'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'loadshed-prototypical.tex', project, author, 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#
# latex_logo = None

# If true, show page references after internal links.
#
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
#
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
#
# latex_appendices = []

# If false, no module index is generated.
#
# latex_domain_indices = True

autodoc_mock_imports = ["flask", "flask_restful", "pyfmi", "copy", "pandas", "scipy", "functools", "sys", "os", "cvxpy"]
#rst_epilog = "\n.. include:: ../.custom_roles.rst\n"
