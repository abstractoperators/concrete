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
        memory: "512"
    }')
    echo $TASK_DEFINITION

    NEW_TASK_DEFINITION=$(aws ecs register-task-definition \
    --region $AWS_DEFAULT_REGION \
    --cli-input-json "$TASK_DEFINITION" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)

    echo "Creating ECS service..."
    SERVICE_DEFINITION=$(jq -n \
    --arg cluster "$ECS_CLUSTER" \
    --arg service_name "$ECS_SERVICE" \
    --arg task_definition "$NEW_TASK_DEFINITION" \
    --argjson desired_count "$DESIRED_COUNT" \
    --arg subnet "$SUBNET" \
    --arg security_group "$SECURITY_GROUP" \
    '{
        cluster: $cluster,
        serviceName: $service_name,
        taskDefinition: $task_definition,
        desiredCount: $desired_count,
        launchType: "FARGATE",
        "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": [
                        "subnet-0fd10668867ad3f41",
                        "subnet-0d4714f3307f188d2",
                        "subnet-0cf5f19eab086f113",
                        "subnet-0ba67bfb6421d660d",
                        "subnet-0dedff55ce3f31073",
                        "subnet-0ca57a9f5ab390beb"
                    ],
                    "securityGroups": [
                        "sg-0c088e203ca8ad61a",
                        "sg-05ef66e1440d8b914"
                    ],
                    "assignPublicIp": "ENABLED"
                }
            },
        schedulingStrategy: "REPLICA",
        deploymentController: {
            type: "ECS"
        },
        enableECSManagedTags: true,
        propagateTags: "SERVICE"
    }')

    echo $SERVICE_DEFINITION
    aws ecs create-service \
    --region $AWS_DEFAULT_REGION \
    --cli-input-json "$SERVICE_DEFINITION"
}

deploy_to_aws "$1"

