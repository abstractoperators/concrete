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
helloworld-celery: celery
	sleep 10
	$(ORCHESTRATE) "Create a simple hello world program" --run-async
	
simpleflask:
	$(ORCHESTRATE) "Provide the code for a flask application. The applicataion should have a single route that renders the HTML template 'index.html'. The template should contain a single header tag with the text 'Hello, World!'."


# ----------------------- Build commands -----------------------
# alembic, auth, api, main, homepage, docs
build-app:
	docker compose -f docker/docker-compose.yml build $(APP)

build-daemons:
	docker compose -f docker/docker-compose.yml build daemons


# ----------------------- Run commands -----------------------
run-webapp: build-app
	docker compose -f docker/docker-compose.yml stop $(APP)
	docker compose -f docker/docker-compose.yml up -d $(APP)


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
	$(UV) mkdocs serve --config-file webapp/docs/config/mkdocs.yml

local-api:
	$(UV) fastapi dev webapp/api/server.py --port 8001

local-main:
	$(UV) fastapi dev webapp/main/server.py

local-auth:
	$(UV) fastapi dev webapp/auth/server.py --port 8002

# Note that for webhook functionality, you will need to use a service like ngrok to expose your local server to the internet. 
# I run `ngrok http 8000`, and then use the forwarding URL as the webhook URL in the GitHub app settings. See webapp/daemons/README.md for more details.
ngrok: # Use the provided url as your webhook url
	ngrok http 8000

local-daemons: 
	$(UV) fastapi dev webapp/daemons/server.py 


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