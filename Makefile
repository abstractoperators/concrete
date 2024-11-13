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
# alembic, auth, api, main, homepage
build-app:
	docker compose -f docker/docker-compose.yml build $(APP)

build-daemons:
	docker compose -f docker/docker-compose.yml build daemons

build-docs:
	$(UV) mkdocs build --config-file docs/mkdocs.yml
	docker compose -f docker/docker-compose.yml build docs
# ----------------------- Run commands -----------------------
run-webapp: build-app
	docker compose -f docker/docker-compose.yml stop $(APP)
	docker compose -f docker/docker-compose.yml up -d $(APP)

run-docs: build-docs
	docker compose -f docker/docker-compose.yml stop docs
	docker compose -f docker/docker-compose.yml up -d docs

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

aws-ecr-push: aws-ecr-login
	docker tag $(APP):latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/$(APP):latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/$(APP):latest
aws-ecr-push-docs: aws-ecr-login
	docker tag docs:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/docs:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/docs:latest
aws-ecr-push-daemons: aws-ecr-login
	docker tag daemons:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/daemons:latest

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
	$(UV) mkdocs serve --config-file docs/mkdocs.yml

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

# PACKAGE = concrete-core, concrete-async, concrete-db
build-package: clear-dist
	uv build --package $(PACKAGE) --no-sources --out-dir dist
publish-package-test: build-package
	uv publish --project $(PACKAGE) --publish-url https://test.pypi.org/legacy/ -t $(TEST_PYPI_API_TOKEN)
publish-package: build-package
	uv publish --project $(PACKAGE) -t $(PYPI_API_TOKEN)