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

# ----------------------- Build commands -----------------------
build-api:
	docker compose -f docker/docker-compose.yml build api

build-webapp-demo:
	docker compose -f docker/docker-compose.yml build webapp-demo

build-webapp-homepage:
	docker compose -f docker/docker-compose.yml build webapp-homepage

build-auth:
	docker compose -f docker/docker-compose.yml build auth

build-dind-builder:
	docker compose -f docker/docker-compose.yml build dind-builder

build-daemons:
	docker compose -f docker/docker-compose.yml build daemons

build-docs:
	$(POETRY) mkdocs build --config-file config/mkdocs.yml
	docker compose -f docker/docker-compose.yml build docs

build-main:
	docker compose -f docker/docker-compose.yml build main

build-alembic:
	docker compose -f docker/docker-compose.yml build alembic
# ----------------------- Run commands -----------------------
run-webapp-api: build-webapp-api
	docker compose -f docker/docker-compose.yml stop api
	docker compose -f docker/docker-compose.yml up -d api

run-webapp-demo: build-webapp-demo
	docker compose -f docker/docker-compose.yml stop webapp-demo
	docker compose -f docker/docker-compose.yml up -d webapp-demo

run-webapp-homepage: build-webapp-homepage
	docker compose -f docker/docker-compose.yml stop webapp-homepage
	docker compose -f docker/docker-compose.yml up -d webapp-homepage

run-webapp-auth: build-webapp-auth
	docker compose -f docker/docker-compose.yml stop auth
	docker compose -f docker/docker-compose.yml up -d auth

run-dind-builder:
	docker compose -f docker/docker-compose.yml stop dind-builder
	docker compose -f docker/docker-compose.yml up -d dind-builder

run-daemons:
	docker compose -f docker/docker-compose.yml stop daemons
	docker compose -f docker/docker-compose.yml up -d daemons

run-docs:
	docker compose -f docker/docker-compose.yml stop docs
	docker compose -f docker/docker-compose.yml up -d docs

run-main: build-main
	docker compose -f docker/docker-compose.yml stop main
	docker compose -f docker/docker-compose.yml up -d main

run-postgres:
	docker compose -f docker/docker-compose.yml down postgres
	docker compose -f docker/docker-compose.yml up -d postgres
	$(POETRY) alembic upgrade head

# ----------------------- AWS Commands -----------------------
# TODO: Use hyphens instead of underscores
# https://www.gnu.org/software/libc/manual/html_node/Argument-Syntax.html

# Need to set your aws config for default profile + credentials
aws-ecr-login:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 008971649127.dkr.ecr.us-east-1.amazonaws.com

# Build before pushing to registry
aws-ecr-push-api: aws-ecr-login
	docker tag api:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/api:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/api:latest
aws-ecr-push-auth: aws-ecr-login
	docker tag auth:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/auth:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/auth:latest
aws-ecr-push-homepage: aws-ecr-login
	docker tag webapp-homepage:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-homepage:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-homepage:latest
aws-ecr-push-demo: aws-ecr-login
	docker tag webapp-demo:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
aws-ecr-push-docs: aws-ecr-login
	docker tag docs:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/docs:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/docs:latest
aws-ecr-push-daemons: aws-ecr-login
	docker tag daemons:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest
aws-ecr-push-main: aws-ecr-login
	docker tag main:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/main:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/main:latest
aws-ecr-push-alembic: aws-ecr-login
	docker tag alembic:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/alembic:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/alembic:latest
deploy-daemon-to-aws-staging:
	$(POETRY) python -m concrete deploy --image-uri 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest --container-name daemons-staging --container-port 80 --service-name=daemons-staging


# ------------------------ Local Development without Docker ------------------------
rabbitmq:
	docker rm -f rabbitmq || true
	docker run -d -p 5672:5672 --name rabbitmq rabbitmq &

# TODO autoreload celery
celery: rabbitmq
	rm logs/celery.log || true
	celery -A concrete worker --loglevel=INFO -f logs/celery.log &

# Run locally
local-docs:
	poetry run mkdocs build --config-file config/mkdocs.yml
	mkdocs serve --config-file config/mkdocs.yml

local-api:
	$(POETRY) fastapi dev webapp/api/server.py --port 8001

local-main:
	$(POETRY) fastapi dev webapp/main/server.py

local-auth:
	$(POETRY) fastapi dev webapp/auth/server.py --port 8002

# Note that for webhook functionality, you will need to use a service like ngrok to expose your local server to the internet. 
# I run `ngrok http 8000`, and then use the forwarding URL as the webhook URL in the GitHub app settings. See webapp/daemons/README.md for more details.
local-daemons:
	/bin/bash -c "set -a; source .env.daemons; set +a; cd webapp/daemons && $(POETRY) fastapi dev server.py"

