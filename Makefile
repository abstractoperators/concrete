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

build-webapp-demo:
	docker compose -f docker/docker-compose.yml build $(if $(filter true,$(USE_CACHE)),,--no-cache)
down-webapp-demo:
	docker compose -f docker/docker-compose.yml down -v
run-webapp-demo: down-webapp-demo
	docker compose -f docker/docker-compose.yml up

run-webapp-main: 
	docker-compose -f docker/docker-compose.yml stop webapp-main
	docker-compose -f docker/docker-compose.yml up --build -d webapp-main

run-dind-builder: 
	docker-compose -f docker/docker-compose.yml stop dind-builder
	docker-compose -f docker/docker-compose.yml up --build -d dind-builder

# Need to set your aws config for default profile + credentials
aws_ecr_login:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 008971649127.dkr.ecr.us-east-1.amazonaws.com
aws_ecr_push_main: aws_ecr_login
	docker tag webapp-main:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-main:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-main:latest
aws_ecr_push_demo: aws_ecr_login
	docker tag webapp-demo:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
