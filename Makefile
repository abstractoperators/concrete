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
helloworld-celery: celery
	sleep 10
	$(ORCHESTRATE) "Create a simple hello world program" --run-async
	
simpleflask:
	$(ORCHESTRATE) "Provide the code for a flask application. The applicataion should have a single route that renders the HTML template 'index.html'. The template should contain a single header tag with the text 'Hello, World!'."


# ----------------------- Build commands -----------------------
build-api:
	docker compose -f docker/docker-compose.yml build api

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
# NOTE: Services inside docker requiring postgres need to have env variable DB_HOST=host.docker.internal
# Launch postgres using env variable DB_HOST=localhost for alembic migrations
# Then, change DB_HOST=host.docker.internal, and launch your dockerized service.
run-webapp-api: build-webapp-api
	docker compose -f docker/docker-compose.yml stop api
	docker compose -f docker/docker-compose.yml up -d api

run-webapp-homepage: build-webapp-homepage
	docker compose -f docker/docker-compose.yml stop webapp-homepage
	docker compose -f docker/docker-compose.yml up -d webapp-homepage

run-webapp-auth: build-auth
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
	@echo "Waiting for PostgreSQL to be ready..."
	while ! docker exec postgres pg_isready -h localhost -p 5432 -q; do \
		echo "Waiting for postgres..."; \
		sleep 1; \
	done
	$(POETRY) alembic upgrade head

# ----------------------- AWS Commands -----------------------

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

ngrok: # Use the provided url as your webhook url
	ngrok http 8000

local-daemons: ngrok
	$(POETRY) fastapi dev server.py
	

