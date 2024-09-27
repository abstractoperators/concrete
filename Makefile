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

# Requires rabbitmq and celery worker to be running
helloworld_celery: celery
	sleep 10
	$(ORCHESTRATE) "Create a simple hello world program" --celery
	
simpleflask:
	$(ORCHESTRATE) "Provide the code for a flask application. The applicataion should have a single route that renders the HTML template 'index.html'. The template should contain a single header tag with the text 'Hello, World!'."


# Requires dind-builder to be running
# Need to manually delete created resources in AWS.
# Created resources will be in ECR, ECS (tasks definitions and services), LB listener rules.
deploysimpleflask:
	$(ORCHESTRATE) "Create a simple helloworld flask application" --deploy

# Note that webapp-demo will require dind-builder to deploy a service to aws. 
# No actual dependency is defined for flexibility.
build-webapp-demo:
	docker compose -f docker/docker-compose.yml build webapp-demo

build-webapp-homepage:
	docker compose -f docker/docker-compose.yml build webapp-homepage

build-dind-builder:
	docker compose -f docker/docker-compose.yml build dind-builder

build-daemons:
	docker compose --env-file .env.daemons -f docker/docker-compose.yml build daemons

build-docs:
	$(POETRY) mkdocs build --config-file config/mkdocs.yml
	docker compose -f docker/docker-compose.yml build docs

run-webapp-demo:
	docker compose -f docker/docker-compose.yml stop webapp-demo
	docker compose -f docker/docker-compose.yml up -d webapp-demo

run-webapp-homepage: build-webapp-homepage
	docker compose -f docker/docker-compose.yml stop webapp-homepage
	docker compose -f docker/docker-compose.yml up -d webapp-homepage

run-dind-builder:
	docker compose -f docker/docker-compose.yml stop dind-builder
	docker compose -f docker/docker-compose.yml up -d dind-builder

run-daemons:
	docker compose -f docker/docker-compose.yml stop daemons
	docker compose -f docker/docker-compose.yml up -d daemons

run-docs:
	docker compose -f docker/docker-compose.yml stop docs
	docker compose -f docker/docker-compose.yml up -d docs

# Run locally
local-docs:
	poetry run mkdocs build --config-file config/mkdocs.yml
	mkdocs serve --config-file config/mkdocs.yml

# TODO: Use hyphens instead of underscores
# https://www.gnu.org/software/libc/manual/html_node/Argument-Syntax.html

# Need to set your aws config for default profile + credentials
aws_ecr_login:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 008971649127.dkr.ecr.us-east-1.amazonaws.com

# Build before pushing to registry
aws_ecr_push_homepage: aws_ecr_login
	docker tag webapp-homepage:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-homepage:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-homepage:latest
aws_ecr_push_demo: aws_ecr_login
	docker tag webapp-demo:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
aws_ecr_push_docs: aws_ecr_login
	docker tag docs:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/docs:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/docs:latest
aws_ecr_push_daemons: aws_ecr_login
	docker tag daemons:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest

deploy-daemon-to-aws-staging:
	$(POETRY) python -m concrete deploy --image-uri 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest --container-name daemons-staging --container-port 80 --service-name=daemons-staging

rabbitmq:
	docker rm -f rabbitmq || true
	docker run -d -p 5672:5672 --name rabbitmq rabbitmq &

# TODO autoreload celery
celery: rabbitmq
	rm logs/celery.log || true
	celery -A concrete worker --loglevel=INFO -f logs/celery.log &

# local swagger UI
local-api:
	$(POETRY) fastapi dev webapp/api/server.py --port 8001

# local webapp-main
local-webapp-main:
	$(POETRY) fastapi dev webapp/main/server.py

# Note that for webhook functionality, you will need to use a service like ngrok to expose your local server to the internet. 
# I run `ngrok http 8000`, and then use the forwarding URL as the webhook URL in the GitHub app settings. See webapp/daemons/README.md for more details.
local-daemons:
	/bin/bash -c "set -a; source .env.daemons; set +a; cd webapp/daemons && $(POETRY) fastapi dev server.py"# Additional Commands Documentation

# Local Development Commands

## Local Development for Documentation
local-docs:
	poetry run mkdocs build --config-file config/mkdocs.yml
	mkdocs serve --config-file config/mkdocs.yml

# AWS ECR Commands

## AWS ECR Login
aws_ecr_login:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 008971649127.dkr.ecr.us-east-1.amazonaws.com

## Push Docker Images to AWS ECR
aws_ecr_push_homepage: aws_ecr_login
	docker tag webapp-homepage:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-homepage:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-homepage:latest

aws_ecr_push_demo: aws_ecr_login
	docker tag webapp-demo:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest

aws_ecr_push_docs: aws_ecr_login
	docker tag docs:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/docs:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/docs:latest

aws_ecr_push_daemons: aws_ecr_login
	docker tag daemons:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest

# Deployment Commands

deply-daemon-to-aws-staging:
	$(POETRY) python -m concrete deploy --image-uri 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest --container-name daemons-staging --container-port 80 --service-name=daemons-staging

# RabbitMQ and Celery Commands

## Start RabbitMQ
rabbitmq:
	docker rm -f rabbitmq || true
	docker run -d -p 5672:5672 --name rabbitmq rabbitmq &

## Start Celery Worker
celery: rabbitmq
	rm logs/celery.log || true
	celery -A concrete worker --loglevel=INFO -f logs/celery.log &

# Local API and Web Application Commands

## Local API Server
local-api:
	$(POETRY) fastapi dev webapp/api/server.py --port 8001

## Local Web Application Main Server
local-webapp-main:
	$(POETRY) fastapi dev webapp/main/server.py

## Local Daemons
local-daemons:
	/bin/bash -c "set -a; source .env.daemons; set +a; cd webapp/daemons && $(POETRY) fastapi dev server.py"