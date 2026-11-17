# define the name of the virtual environment directory
VENV := venv
PYTHON := $(VENV)/bin/python3.12
PIP := $(VENV)/bin/pip

# default target, when make executed without arguments
all: venv

$(VENV)/bin/activate:
	@echo "Creating Python virtual environment at ./venv/..."
	@python3.12 -m venv $(VENV)
	@./$(PYTHON) -m pip install --upgrade pip
	@echo "Installing requirements..."
	@./$(PIP) install -r requirements.txt
# Pip does not seem to install 'api/datafiles' after trying build, so using -e
#    @./$(PYTHON) -m build src/tesp_support/.
	@./$(PIP) install -e src/tesp_support/.

# venv is a shortcut target
venv: $(VENV)/bin/activate

run: venv
	.$(PYTHON) app.py

clean:
	@echo "Deleting venv, *.pyc, and test coverage data..."
	@rm -rf $(VENV)
	@rm -rf .coverage coverage.xml results.xml .pytest_cache htmlcov
	@rm -rf docs/_build src/tesp_support/build src/tesp_support/tesp_support.egg-info
	@find . -type f -name '*.pyc' -delete

docs:
	@echo "Creating HTML "read the docs" website"
	@. $(VENV)/bin/activate; cd ./doc; make html

tests:
	@echo "Running tests with coverage report..."
	@$(PYTHON) -m pytest -c pytest.ini --cov-report html --cov-report term --cov-report xml \
		--cov=tesp_support --cov-fail-under=20 --junitxml results.xml -v src/tesp_support/test

.PHONY: all venv run clean docs tests coverage