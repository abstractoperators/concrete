#!/bin/bash

deploy_to_aws() {
    local IMAGE_URI="$1"
    TASK_FAMILY=$(echo "$IMAGE_URI" | awk -F'/' '{print $NF}')
    
    echo $TASK_FAMILY

    ECS_CLUSTER="DemoCluster"
    ECS_SERVICE=$TASK_FAMILY
    CONTAINER_NAME=$TASK_FAMILY
    ECS_SERVICE="my-ecs-service"
    AWS_REGION="us-east-1"
    CONTAINER_PORT=80
    DESIRED_COUNT=1

    echo "Creating/updating task definition..."
    TASK_DEFINITION=$(jq -n \
    --arg family "$TASK_FAMILY" \
    --arg name "$CONTAINER_NAME" \
    --arg image "$IMAGE_URI" \
    --argjson port "$CONTAINER_PORT" \
    --arg execution_role_arn "arn:aws:iam::008971649127:role/ecsTaskExecutionWithSecret"\
    '{
        family: $family,
        executionRoleArn: "arn:aws:iam::008971649127:role/ecsTaskExecutionWithSecret",
        containerDefinitions: [
        {
            name: $name,
            image: $image,
            portMappings: [
            {
                containerPort: $port,
                hostPort: $port,
                protocol: "tcp"
            }
            ],
            essential: true

        }
        ],
        requiresCompatibilities: ["FARGATE"],
        networkMode: "awsvpc",
        cpu: "256",
        memory: "512"
    }')
    echo $TASK_DEFINITION

    NEW_TASK_DEFINITION=$(aws ecs register-task-definition \
    --region $AWS_REGION \
    --cli-input-json "$TASK_DEFINITION" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

    echo "New task definition: $NEW_TASK_DEFINITION"

    echo "Running task..."
    TASK_ARN=$(aws ecs run-task \
        --cluster $ECS_CLUSTER \
        --task-definition $NEW_TASK_DEFINITION \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[subnet-0d4714f3307f188d2],securityGroups=[sg-0463bb6000a464f50],assignPublicIp=ENABLED}" \
        --region $AWS_REGION \
        --query 'tasks[0].taskArn' \
        --output text)

    echo "Task ARN: $TASK_ARN"
    # aws ecs create-service \
    #     --cluster $ECS_CLUSTER \
    #     --service-name $SERVICE_NAME \
    #     --task-definition $NEW_TASK_DEFINITION \
    #     --desired-count $DESIRED_COUNT \
    #     --launch-type FARGATE \
    #     --network-configuration "awsvpcConfiguration={subnets=[subnet-12345678],securityGroups=[sg-12345678]}" \
    #     --region $AWS_REGION
}


deploy_to_aws "$1"


# AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
# FULL_IMAGE_NAME="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$TASK_FAMILY:latest"