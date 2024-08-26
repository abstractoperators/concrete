POETRY := poetry run
PYTHON := $(POETRY) python
ORCHESTRATE := $(PYTHON) -m concrete prompt

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

# Requires dind-builder to be running
# Need to manually delete created resources in AWS.
# Created resources will be in ECR, ECS (tasks definitions and services), LB listener rules.
deploysimpleflask:
	$(ORCHESTRATE) "Create a simple helloworld flask application" --deploy

# Note that webapp-demo will require dind-builder to deploy a service to aws. 
# No actual dependency is defined for flexibility.
build-webapp-demo:
	docker compose -f docker/docker-compose.yml build webapp-demo

build-webapp-main:
	docker compose -f docker/docker-compose.yml build webapp-main

build-dind-builder:
	docker compose -f docker/docker-compose.yml build dind-builder

run-webapp-demo: 
	docker compose -f docker/docker-compose.yml stop webapp-demo
	docker compose -f docker/docker-compose.yml up -d webapp-demo

run-webapp-main: 
	docker compose -f docker/docker-compose.yml stop webapp-main
	docker compose -f docker/docker-compose.yml up -d webapp-main

run-dind-builder: 
	docker compose -f docker/docker-compose.yml stop dind-builder
	docker compose -f docker/docker-compose.yml up -d dind-builder

# Need to set your aws config for default profile + credentials
aws_ecr_login:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 008971649127.dkr.ecr.us-east-1.amazonaws.com
aws_ecr_push_main: aws_ecr_login
	docker tag webapp-main:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-main:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-main:latest
aws_ecr_push_demo: aws_ecr_login
	docker tag webapp-demo:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
