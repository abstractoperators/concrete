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

# Demo Webapp with Deploy
localhost_demo_with_deploy: localhost_demo_down
	docker compose -f docker/docker-compose.yml build
	docker compose -f docker/docker-compose.yml up

localhost_demo_down:
	docker compose -f docker/docker-compose.yml down -v

# Build docker images
# Push to ECR? 