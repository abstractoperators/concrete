# How to launch local demo site with code deployment capabilities

```bash
make localhost_demo_with_deploy
``` 

## Webapp Service

Launches demowebsite. \
SoftwareProject, when created with the deploy=True flag, will call Agent.AWSAgent to deploy the code on AWS ECS.\
AWSAgent places Docker context into shared volume w/ dind-builder, and pings dind-builder service to build and deploy. ASSUMES SERVICES WERE STARTED WITH DOCKER COMPOSE, which provides networks for each service. Using docker-compose, AWSAgent pings builder using dind-builder:5000, but will need to be changed for ECS deployment to localhost:5000.

### Requirements

Image requires OPENAI_API_KEY environment variable. 

## dind-builder service

This service has 2.5 core functionalities that deploy the code for a flask webapp on AWS ECS Tasks.

   1. listener (listener.sh)
      1. Listens on port 5000, and calls the builder
   2. Build and push an image to AWS ECR (build_and_push.sh)
      1. Takes one argument, which is the file path to Docker build context. 
      2. Builds docker context, and makes a new ECR repository with that image. 
      3. Calls deploy
   3. Deploys a standalone task with that image (deploy_to_aws.sh)
      1. Takes one argument, the IMAGE_URI of the ECR image to use (requires ECR image, otherwise need to add container authentication)
      2. Uses pre-existing ECS_CLUSTER="DemoCluster", subnet, vpc security group, and taskexecution role (hard coded into script)
      3. Defines a new task-definition in that cluster, and starts it.

It's important to note that this service DOES NOT handle deleting of AWS resources, so it is important to manually delete ECR repositories and running tasks/task definitions.

### Requirements

Image requires environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION`. Currently loaded into the image via docker-compose, will need another way on ECS deployment\
Pre-existing AWS ECS Cluster\
Pre-existing AWS VPC w/ subnet, security group exposing inbound http and https traffic, and all outbound traffic \
Pre-existing AWS `taskExecutionRole` allowing ECR reads