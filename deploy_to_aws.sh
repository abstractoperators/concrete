#!/bin/bash

deploy_to_aws() {
    local IMAGE_URI="$1"
    TASK_FAMILY=$(echo "$IMAGE_URI" | awk -F'/' '{print $NF}')
    
    echo $TASK_FAMILY

    ECS_CLUSTER="DemoCluster"
    ECS_SERVICE=$TASK_FAMILY
    CONTAINER_NAME=$TASK_FAMILY
    AWS_REGION="us-east-1"
    CONTAINER_PORT=80
    DESIRED_COUNT=1
    SUBNET="subnet-0d4714f3307f188d2"
    SECURITY_GROUP="sg-0463bb6000a464f50"
    EXECUTION_ROLE_ARN="arn:aws:iam::008971649127:role/ecsTaskExecutionWithSecret"

    echo "Creating/updating task definition..."
    TASK_DEFINITION=$(jq -n \
    --arg family "$TASK_FAMILY" \
    --arg name "$CONTAINER_NAME" \
    --arg image "$IMAGE_URI" \
    --argjson port "$CONTAINER_PORT" \
    --arg execution_role_arn "$EXECUTION_ROLE_ARN"\
    '{
        family: $family,
        executionRoleArn: $execution_role_arn,
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
        memory: "512",
        runtimePlatform: {
            cpuArchitecture: "ARM64",
            operatingSystemFamily: "LINUX"
        }
    }')
    echo $TASK_DEFINITION

    NEW_TASK_DEFINITION=$(aws ecs register-task-definition \
    --region $AWS_DEFAULT_REGION \
    --cli-input-json "$TASK_DEFINITION" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

    echo "New task definition: $NEW_TASK_DEFINITION"

    echo "Running task..."
    TASK_ARN=$(aws ecs run-task \
        --cluster $ECS_CLUSTER \
        --task-definition $NEW_TASK_DEFINITION \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET],securityGroups=[$SECURITY_GROUP],assignPublicIp=ENABLED}" \
        --region $AWS_DEFAULT_REGION \
        --query 'tasks[0].taskArn' \
        --output text)

    echo "Task ARN: $TASK_ARN"
}


deploy_to_aws "$1"

