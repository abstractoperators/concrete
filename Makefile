UV := uv run
PYTHON := $(UV) python
ORCHESTRATE := PYTHONPATH=src/concrete-core $(PYTHON) -m concrete prompt


# Setup
install:
	$(UV) pre-commit install

# Run tests
test:
	$(UV) pytest

# Lint
lint:
	$(UV) pre-commit run --all-files

# Demo commands
helloworld:
	$(ORCHESTRATE) "Create a simple hello world program"

# Requires rabbitmq and celery worker to be running
helloworld_celery: celery
	sleep 10
	$(ORCHESTRATE) "Create a simple hello world program" --run-async
	
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

build-webapp-homepage:
	docker compose -f docker/docker-compose.yml build webapp-homepage

build-auth:
	docker compose -f docker/docker-compose.yml build auth

build-dind-builder:
	docker compose -f docker/docker-compose.yml build dind-builder

build-daemons:
	docker compose -f docker/docker-compose.yml build daemons

build-docs:
	$(UV) mkdocs build --config-file config/mkdocs.yml
	docker compose -f docker/docker-compose.yml build docs

build-main:
	docker compose -f docker/docker-compose.yml build main

build-alembic:
	docker compose -f docker/docker-compose.yml build alembic
# ----------------------- Run commands -----------------------
# NOTE: Services inside docker requiring postgres need to have env variable DB_HOST=host.docker.internal
# Launch postgres using env variable DB_HOST=localhost for alembic migrations
# Then, change DB_HOST=host.docker.internal, and launch your dockerized service.
run-webapp-api: build-api 
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
	$(UV) alembic upgrade head
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
	$(UV) celery -A src.concrete-async.concrete_async worker --loglevel=INFO -E 

# Run locally
local-docs:
	poetry run mkdocs build --config-file config/mkdocs.yml
	mkdocs serve --config-file config/mkdocs.yml

local-api:
	$(UV) fastapi dev webapp/api/server.py --port 8001

local-main:
	$(UV) fastapi dev webapp/main/server.py

local-auth:
	$(UV) fastapi dev webapp/auth/server.py --port 8002

# Note that for webhook functionality, you will need to use a service like ngrok to expose your local server to the internet. 
# I run `ngrok http 8000`, and then use the forwarding URL as the webhook URL in the GitHub app settings. See webapp/daemons/README.md for more details.
local-daemons:
	/bin/bash -c "set -a; source .env.daemons; set +a; cd webapp/daemons && $(UV) fastapi dev server.py"


# Build Packages
clear-dist:
	rm -rf dist/*

build-concrete-core: clear-dist
	uv build --package concrete-core --no-sources --out-dir dist

build-concrete-async: clear-dist
	uv build --package concrete-async --no-sources --out-dir dist

build-concrete-db: clear-dist
	uv build --package concrete-db --no-sources --out-dir dist

publish-concrete-core-test: build-concrete-core 
	uv publish --project concrete-core --publish-url https://test.pypi.org/legacy/ -t $(TEST_PYPI_API_TOKEN)

publish-concrete-async-test: build-concrete-async
	uv publish --project concrete-sync --publish-url https://test.pypi.org/legacy/ -t $(TEST_PYPI_API_TOKEN)

publish-concrete-db-test: build-concrete-db
	uv publish --project concrete-db --publish-url https://test.pypi.org/legacy/ -t $(TEST_PYPI_API_TOKEN)