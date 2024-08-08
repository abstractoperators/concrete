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
	docker compose -f docker/docker-compose.yml build
down-webapp-demo:
	docker compose -f docker/docker-compose.yml down -v
run-webapp-demo: down-webapp-demo build-webapp-demo
	docker compose -f docker/docker-compose.yml up

build-webapp-main:
	docker buildx build -f docker/Dockerfile.main -t webapp-main .

run-webapp-main: build-webapp-main
	docker run -p 8000:80 webapp-main

# Need to set your aws config for default profile + credentials
aws_ecr_login:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 008971649127.dkr.ecr.us-east-1.amazonaws.com

aws_ecr_push_main: build-webapp-main aws_ecr_login
	docker tag webapp-main:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-main:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-main:latest

