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
# Note that webapp-demo will require dind-builder to deploy a service to aws. 
# No actual dependency is defined for flexibility.
build-webapp-demo:
	docker compose -f docker/docker-compose.yml build webapp-demo

build-webapp-homepage:
	docker compose -f docker/docker-compose.yml build webapp-homepage

build-dind-builder:
	docker compose -f docker/docker-compose.yml build dind-builder

build-daemons:
	docker compose -f docker/docker-compose.yml build daemons

build-docs:
	$(POETRY) mkdocs build --config-file config/mkdocs.yml
	docker compose -f docker/docker-compose.yml build docs

build-main:
	docker compose -f docker/docker-compose.yml build main

# ----------------------- Run commands -----------------------
run-webapp-demo: build-webapp-demo
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

run-main: build-main
	docker compose -f docker/docker-compose.yml stop main
	docker compose -f docker/docker-compose.yml up -d main

# Note that the actual postgres server is running on EC2 and is not dockerized. 
# Therefore the deployment is native, and does not use deployment workflows like webapps do.
# database url is set in orm/setup, which uses an env variable. 
# SQLALCHEMY_DATABSE_URL="postgresql+psycopg://local_user:local_password@localhost:5432/local_db"
run-postgres:
	docker compose -f docker/docker-compose.yml stop postgres
	docker compose -f docker/docker-compose.yml up -d postgres

# ----------------------- AWS Commands -----------------------
# TODO: Use hyphens instead of underscores
# https://www.gnu.org/software/libc/manual/html_node/Argument-Syntax.html

# Need to set your aws config for default profile + credentials
aws-ecr-login:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 008971649127.dkr.ecr.us-east-1.amazonaws.com

# Build before pushing to registry
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

# local swagger UI
local-api:
	$(POETRY) fastapi dev webapp/api/server.py --port 8001

# local webapp-main
local-webapp-main:
	$(POETRY) fastapi dev webapp/main/server.py

# Note that for webhook functionality, you will need to use a service like ngrok to expose your local server to the internet. 
# I run `ngrok http 8000`, and then use the forwarding URL as the webhook URL in the GitHub app settings. See webapp/daemons/README.md for more details.
local-daemons:
	/bin/bash -c "set -a; source .env.daemons; set +a; cd webapp/daemons && $(POETRY) fastapi dev server.py"

