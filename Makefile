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

build-webapp-main:
	docker buildx build -f docker/Dockerfile.main -t webapp-main:latest . $(if $(filter true,$(USE_CACHE)),,--no-cache)
run-webapp-main: 
	docker run -p 8000:80 webapp-main

build-dind-builder:
	docker buildx build -f docker/Dockerfile.dind-builder -t dind-builder:latest . $(if $(filter true,$(USE_CACHE)),,--no-cache)
run-dind-builder: 
	-docker stop dind-builder > /dev/null 2>&1
	-docker rm dind-builder > /dev/null 2>&1
	docker run -d \
		--name dind-builder \
		--privileged \
        -v /shared:/shared \
        -e SHARED_VOLUME=/shared \
        -p 5000:5000 \
        --env-file .env.demo \
		dind-builder:latest

# Need to set your aws config for default profile + credentials
aws_ecr_login:
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 008971649127.dkr.ecr.us-east-1.amazonaws.com
aws_ecr_push_main: aws_ecr_login
	docker tag webapp-main:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-main:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-main:latest
aws_ecr_push_demo: aws_ecr_login
	docker tag webapp-demo:latest 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
	docker push 008971649127.dkr.ecr.us-east-1.amazonaws.com/webapp-demo:latest
