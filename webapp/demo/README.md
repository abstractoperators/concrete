# How to launch local demo site with code deployment capabilities

```bash
make localhost_demo_with_deploy
``` 

## Webapp Service

This service launches the demo website on local host over port 80. \
SoftwareProject, when created with the deploy=True flag, will call Agent.AWSAgent to deploy the code on AWS ECS.\
`AWSAgent` places Docker context into shared volume with `dind-builder`, and pings `dind-builder` service to build and deploy.
WARNING: This assumes the services were started with docker-compose or the make command, which provides networks for each service. Using docker-compose, `AWSAgent` pings builder using `dind-builder:5000`, but will need to be changed for ECS deployment to `localhost:5000`.

### Requirements

Image requires OPENAI_API_KEY environment variable. 
```bash
export OPENAI_API_KEY = <your-api-key-here>
```

## dind-builder service

This service has 3 core functionalities that deploy the code for a flask webapp on AWS ECS Tasks.

   1. listener (`listener.sh`)
      a. Listens on port 5000, and calls the builder
   2. Build and push an image to AWS ECR (`build_and_push.sh`)
      a. Takes one argument, which is the file path to Docker build context. 
      b. Builds docker context, and makes a new ECR repository with that image. 
      c. Calls deploy
   3. Deploys a standalone task with that image (`deploy_to_aws.sh`)
      a. Takes one argument, the `IMAGE_URI` of the ECR image to use (requires ECR image, otherwise need to add container authentication)
      b. Uses pre-existing ECS_CLUSTER="DemoCluster", subnet, vpc security group, and taskexecution role (hard coded into script)
      c. Defines a new task-definition in that cluster, and starts it.

N.B.: This service **does not** handle deleting of AWS resources, so it is important to manually delete ECR repositories, running tasks, and task definitions.

### Requirements

Image requires environment variables `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION`. Currently loaded into the image via docker-compose, will need another way on ECS deployment\
Pre-existing AWS ECS Cluster\
Pre-existing AWS VPC w/ subnet, security group exposing inbound http and https traffic, and all outbound traffic \
Pre-existing AWS `taskExecutionRole` allowing ECR reads