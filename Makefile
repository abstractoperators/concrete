POETRY := poetry run
PYTHON := $(POETRY) python
ORCHESTRATE := $(PYTHON) -m concrete

# Setup
install:
	poetry install

# Run tests
test:
	$(PYTHON) -m pytest

# Demo commands
helloworld:
	$(ORCHESTRATE) "Create a simple hello world program"

simpleflask:
	$(ORCHESTRATE) "Provide the code to quickstart a basic builtin Flask server. The Flask server should only show Hello World"

django:
	$(PYTHON) manage.py runserver