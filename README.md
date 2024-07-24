# Concrete

## Installation
```python
pip install concrete-operators
```

## Quickstart
```bash
export OPENAI_API_KEY=<your-api-key-here>
python -m concrete "Create a simple program that says 'Hello, World!'"
```

# Dev Setup
Run the following commands to get your local environment setup
```bash
brew install poetry
poetry install
poetry shell
pre-commit install
```

Pre-commit will check for code formatting before completing the commit. If code is formatted by black, you will need to add the changes files to staged and re-try the commit.
Flake8 generally have to be handled manually.

To force a commit locally add the flag `--no-verify` as an option to `git commit` e.g. `git commit --no-verify -m "..."`. Github workflows should mirror local pre commit checks.
