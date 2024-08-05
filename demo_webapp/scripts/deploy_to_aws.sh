#!/bin/bash
find_lowest_priority() {
    LISTENER_ARN=$1
    # Get all rules for the listener
    rules=$(aws elbv2 describe-rules --listener-arn $LISTENER_ARN --output json)
   
    # Extract priorities and sort them numerically
    priorities=$(echo "$rules" | jq -r '.Rules[].Priority' | grep -v default | sort -n)
   
    # Find the lowest unused priority
    last_priority=0
    for priority in $priorities; do
        if [ $((priority - last_priority)) -gt 1 ]; then
            echo $((last_priority + 1))
            return
        fi
        last_priority=$priority
    done
   
    # If all priorities are consecutive, return the next number
    echo $((last_priority + 1))
}

deploy_to_aws() {
    local IMAGE_URI="$1"
    TASK_FAMILY=$(echo "$IMAGE_URI" | awk -F'/' '{print $NF}')
    
    echo $TASK_FAMILY

    ECS_CLUSTER="DemoCluster"
    ECS_SERVICE=$TASK_FAMILY
    CONTAINER_NAME=$TASK_FAMILY
    TARGET_GROUP_NAME=$(echo $TASK_FAMILY| sed 's/^so_//' | tr '_' '-')
    TARGET_GROUP_NAME="${TARGET_GROUP_NAME:0:32}"
    AWS_REGION="us-east-1"
    CONTAINER_PORT=80
    DESIRED_COUNT=1
    VPC="vpc-022b256b8d0487543"
    SUBNET="subnet-0d4714f3307f188d2"
    SECURITY_GROUP="sg-0463bb6000a464f50"
    EXECUTION_ROLE_ARN="arn:aws:iam::008971649127:role/ecsTaskExecutionWithSecret"
    LOAD_BALANCER_ARN="arn:aws:elasticloadbalancing:us-east-1:008971649127:loadbalancer/app/ConcreteLB/8624995bbfed2fc3"
    LISTENER_ARN="arn:aws:elasticloadbalancing:us-east-1:008971649127:listener/app/ConcreteLB/8624995bbfed2fc3/8e2d28e1f80bf00b"
    LISTENER_RULE_PRIORITY=$(find_lowest_priority $LISTENER_ARN)

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
        runtimePlatform: {
            cpuArchitecture: "ARM64",
            operatingSystemFamily: "LINUX"
        },
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
            essential: true,
            logConfiguration: {
                logDriver: "awslogs",
                options: {
                    "awslogs-group": "fargate-demos",
                    "awslogs-region": "us-east-1",
                    "awslogs-stream-prefix": "fg"
                }
            }
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

    echo "Creating target group"
    TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name $TARGET_GROUP_NAME \
    --protocol HTTP \
    --port 80 \
    --vpc-id $VPC \
    --target-type ip \
    --health-check-path / \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 2 \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

    echo "Target Group ARN: $TARGET_GROUP_ARN"

    echo "Adding rule to listener"
    RULE_JSON=$(jq -n \
    --arg listener_arn "$LISTENER_ARN" \
    --argjson priority "$LISTENER_RULE_PRIORITY" \
    --arg target_group_arn "$TARGET_GROUP_ARN" \
    --arg path "$TARGET_GROUP_NAME.abop.ai" \
    '{
        ListenerArn: $listener_arn,
        Priority: $priority,
        Conditions: [
            {
                Field: "host-header",
                Values: [$path]
            }
        ],
        Actions: [
            {
                Type: "forward",
                TargetGroupArn: $target_group_arn
            }
        ]
    }')

    aws elbv2 create-rule --cli-input-json "$RULE_JSON"

    echo "Creating ECS service..."
    # Use argjson to use ints
    SERVICE_DEFINITION=$(jq -n \
    --arg cluster "$ECS_CLUSTER" \
    --arg service_name "$ECS_SERVICE" \
    --arg task_definition "$NEW_TASK_DEFINITION" \
    --argjson desired_count "$DESIRED_COUNT" \
    --arg subnet "$SUBNET" \
    --arg security_group "$SECURITY_GROUP" \
    --arg target_group_arn "$TARGET_GROUP_ARN" \
    --arg container_name "$CONTAINER_NAME" \
    --argjson container_port $CONTAINER_PORT \
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
                        "sg-05ef66e1440d8b914",
                        "sg-0463bb6000a464f50"
                    ],
                    "assignPublicIp": "ENABLED"
                }
            },
        schedulingStrategy: "REPLICA",
        deploymentController: {
            type: "ECS"
        },
        enableECSManagedTags: true,
        propagateTags: "SERVICE",
        loadBalancers: [
        {
            targetGroupArn: $target_group_arn,
            containerName: $container_name,
            containerPort: $container_port
        }
    ]
    }')

    echo $SERVICE_DEFINITION
    aws ecs create-service \
    --cli-input-json "$SERVICE_DEFINITION"
}

deploy_to_aws "$1"
