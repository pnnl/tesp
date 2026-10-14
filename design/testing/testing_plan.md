- Code should follow the coding guidlines outlined in the docs 
[Coding Style Guide](https://tesp.readthedocs.io/en/latest/references/Coding_Style_Guide.html)
- If you are using an IDE that shows you style problems, code warnging, and errors; resolve them.
- Tests should be written and used as you write. They may be informal tests to ensure your code runs as intended.
- Proper tests that are recognizable by Pytest should also be added to the `src/tesp_support/test/dsot` directory.
  - Pytest runs functions that start with "test"
  - These tests likely will not work with external programs.
- Testing that integrates external programs:
  - ?
- flake8 will be used to enforce code style and prevent semantic errors from passing
  - the styles to be enforced will be determined and configured
  - the scope will be confined to the new agents
- The use of a formatter like black is encouraged to aid in proper code style compliance
- mypy will be used for static type checking [mypy.readthedocs](https://mypy.readthedocs.io/en/stable/index.html)
  - only new agents will be checked for now

Generally the following tools will be useful
- Pytest for automated testing
- flake8 for automated testing and style guide enforcement
- mypy for type checking 
[mypy.readthedocs](https://mypy.readthedocs.io/en/stable/index.html)
> Type checkers help ensure that you’re using variables and functions in your code correctly. 
> With mypy, add type hints (PEP 484) to your Python programs, 
> and mypy will warn you when you use those types incorrectly.

