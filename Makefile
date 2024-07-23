POETRY := poetry run
PYTHON := $(POETRY) python
ORCHESTRATE := $(PYTHON) -m concrete.orchestrator

# Setup
install:
	poetry install

# Demo commands
helloworld:
	$(ORCHESTRATE) "Create a simple hello world program"

simpleflask:
	$(ORCHESTRATE) "Provide the code to quickstart a basic builtin Flask server. The Flask server should only show Hello World"