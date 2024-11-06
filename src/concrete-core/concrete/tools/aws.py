try:
    import boto3
except ImportError:
    ImportError("Install aws extras to use AwsTool")

import time
from datetime import datetime, timezone
from typing import Optional

from concrete.clients import CLIClient
from concrete.models.base import ConcreteModel
from concrete.tools import MetaTool
from dotenv import dotenv_values


class Container(ConcreteModel):
    """
    Type hinting for an abstracted container object
    """

    image_uri: str
    container_name: str
    container_port: int
    container_env_file: str


class AwsTool(metaclass=MetaTool):
    SHARED_VOLUME = "/shared"
    results: dict[str, dict] = {}  # Emulates a DB for retrieving project directory objects by key.
    DIND_BUILDER_HOST = "localhost"
    DIND_BUILDER_PORT = 5002

    @classmethod
    def _poll_image_status(cls, repo_name: str) -> bool:
        """
        Polls ECR until an image is pushed. True if image is pushed, False otherwise.
        Returns False after ~5 minutes of polling.
        """
        # TODO smarter way of detecting a 'new' image besides comparing push date.

        ecr_client = boto3.client("ecr")
        cur_time = datetime.now().replace(tzinfo=timezone.utc)
        for _ in range(30):
            try:
                res = ecr_client.describe_images(repositoryName=repo_name)
                if res["imageDetails"] and res["imageDetails"][0]["imagePushedAt"] > cur_time:
                    return True
            except ecr_client.exceptions.RepositoryNotFoundException:
                pass
            time.sleep(10)

        return False

    @classmethod
    def _run_task(
        cls,
        containers: list[Container],
        cpu: int = 256,
        memory: int = 512,
        subnets: list[str] = ["subnet-0ba67bfb6421d660d"],
        security_groups: list[str] = ["sg-0463bb6000a464f50"],
        task_name: Optional[str] = None,
    ):
        """
        Defines a task definition, and runs it.
        """
        import boto3

        ecs_client = boto3.client("ecs")
        task_name = task_name or containers[0].container_name
        execution_role_arn = "arn:aws:iam::008971649127:role/ecsTaskExecutionWithSecret"
        cluster = "DemoCluster"

        task_definition_arn = ecs_client.register_task_definition(
            family=task_name,
            executionRoleArn=execution_role_arn,
            networkMode="awsvpc",
            requiresCompatibilities=["FARGATE"],
            containerDefinitions=[
                {  # type: ignore
                    "name": container.container_name,
                    "image": container.image_uri,
                    "portMappings": [{"containerPort": container.container_port}],
                    "essential": True,
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "fargate-demos",
                            "awslogs-region": "us-east-1",
                            "awslogs-stream-prefix": "fg",
                        },
                    },
                    "environment": [
                        {"name": k, "value": v} for k, v in dotenv_values(container.container_env_file).items()
                    ],
                }
                for container in containers
            ],
            cpu=str(cpu) if cpu else "256",
            memory=str(memory) if memory else "512",
            runtimePlatform={
                "cpuArchitecture": "ARM64",
                "operatingSystemFamily": "LINUX",
            },
        )["taskDefinition"]["taskDefinitionArn"]

        ecs_client.run_task(
            cluster=cluster,
            taskDefinition=task_definition_arn,
            count=1,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": subnets,
                    "securityGroups": security_groups,
                    "assignPublicIp": "ENABLED",
                }
            },
            enableECSManagedTags=True,
            propagateTags="TASK_DEFINITION",
        )

    @classmethod
    def _new_listener_rule(
        cls,
        listener_arn: str,
        target_group_name: str,
        listener_rule: dict | None = None,
        port: int = 80,
        vpc: str = "vpc-022b256b8d0487543",
        health_check_path: str = "/",
    ) -> tuple[str, bool]:
        """
        Creates or updates an existing listener rule.
        If a rule using the same target group already exists, it will be overwritten

        Args:
            listener_arn: The ARN of the listener to attach the rule to.
            listener_rule: {'field': str, 'value': str}.
                Defaults to {'field': 'host-header', 'value': f"{target_group_name}.abop.ai"}
            target_group_name: The name of the target group to create.
            cluster: The cluster to create the target group in.
            port: The port to attach the target group to.
            health_check_path: The path to use for the health check.
        Returns:
            target_group_arn
        """
        import boto3

        elbv2_client = boto3.client("elbv2")
        target_group_arn = None
        if listener_rule is None:
            listener_rule_field = "host-header"
            listener_rule_value = f"{target_group_name}.abop.ai"
        else:
            if listener_rule.get("field") and listener_rule.get("value"):
                listener_rule_field = str(listener_rule.get("field"))
                listener_rule_value = str(listener_rule.get("value"))
            else:
                raise ValueError("listener_rule must contain both field and value keys.")

        arn_prefix = listener_arn.split(":listener")[0]
        # Replace rule for target group if it already exists
        existing_rules = elbv2_client.describe_rules(ListenerArn=listener_arn)["Rules"]
        target_group_arn = None
        for rule in existing_rules:
            if rule["Actions"][0]["Type"] == "forward" and rule["Actions"][0]["TargetGroupArn"].startswith(
                arn_prefix + f":targetgroup/{target_group_name}"
            ):
                elbv2_client.delete_rule(RuleArn=rule["RuleArn"])

        if target_group_arn is None:
            target_group_arn = elbv2_client.create_target_group(
                Name=target_group_name,
                Protocol="HTTP",
                Port=port,
                VpcId=vpc,
                TargetType="ip",
                HealthCheckEnabled=True,
                HealthCheckPath=health_check_path,
                HealthCheckIntervalSeconds=30,
                HealthCheckTimeoutSeconds=5,
                HealthyThresholdCount=2,
                UnhealthyThresholdCount=2,
            )["TargetGroups"][0]["TargetGroupArn"]

        # Calculate lowest unused rule priority
        existing_rule_priorities = set(
            [int(rule["Priority"]) for rule in existing_rules if rule["Priority"] != "default"]
        )
        listener_rule_priority = len(existing_rule_priorities) + 1
        for i in range(1, len(existing_rules) + 1):
            if i not in existing_rule_priorities:
                listener_rule_priority = i
                break

        elbv2_client.create_rule(
            ListenerArn=listener_arn,
            Priority=listener_rule_priority,
            Conditions=[{"Field": listener_rule_field, "Values": [listener_rule_value]}],
            Actions=[
                {
                    "Type": "forward",
                    "TargetGroupArn": target_group_arn,
                }
            ],
        )

        return target_group_arn

    @classmethod
    def _deploy_service(
        cls,
        containers: list[Container],
        cpu: int = 256,
        memory: int = 512,
        service_name: str | None = None,
        listener_rule: dict | None = None,
        subnets: list[str] = ["subnet-0ba67bfb6421d660d"],
        vpc: str = "vpc-022b256b8d0487543",
        security_groups: list[str] = ["sg-0463bb6000a464f50"],
        listener_arn: str = "arn:aws:elasticloadbalancing:us-east-1:008971649127:listener/app/ConcreteLoadBalancer/f7cec30e1ac2e4a4/451389d914171f05",  # noqa E501
        health_check_path: str = "/",
        cluster: str = "DemoCluster",
    ) -> bool:
        """
        Args
            containers (Container): List of Container objects to deploy.
            service_name (str): Custom service name, defaults to the first container name as host header. Also used as task name.
            cpu (int): The amount of CPU to allocate to the service. Defaults to 256.
            memory (int): The amount of memory to allocate to the service. Defaults to 512
            listener_rule: Dictionary of {field: str, value: str} for the listener rule. Defaults to {'field': 'host-header', 'value': f"{service_name}.abop.ai"}}
            subnets (list(str)): List of subnets to consider for placement. Defaults to AZ-a, us-east-1, public
            vpc (str): The VPC to deploy the service in. Defaults to us-east-1
            security_groups (list(str)): List of security groups to attach to the service. Defaults to allow traffic from concrete ALB.
            listener_arn: Arn of the listener to attach to the target group. Defaults to https listener on ConcreteLoadBalancer.
        Returns:
            bool: True if the service started successfully, False otherwise.
        """  # noqa: E501
        import boto3

        ecs_client = boto3.client("ecs")

        service_name = service_name or containers[0].container_name
        execution_role_arn = "arn:aws:iam::008971649127:role/ecsTaskExecutionWithSecret"

        target_group_arn = cls._new_listener_rule(
            listener_arn=listener_arn,
            target_group_name=service_name,
            listener_rule=listener_rule,
            port=containers[0].container_port,
            vpc=vpc,
            health_check_path=health_check_path,
        )

        task_definition_arn = ecs_client.register_task_definition(
            family=service_name,
            executionRoleArn=execution_role_arn,
            networkMode="awsvpc",
            requiresCompatibilities=["FARGATE"],
            containerDefinitions=[
                {  # type: ignore
                    "name": container.container_name,
                    "image": container.image_uri,
                    "portMappings": [{"containerPort": container.container_port}],
                    "essential": True,
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "fargate-demos",
                            "awslogs-region": "us-east-1",
                            "awslogs-stream-prefix": "fg",
                        },
                    },
                    "environment": [
                        {"name": k, "value": v} for k, v in dotenv_values(container.container_env_file).items()
                    ],
                }
                for container in containers
            ],
            cpu=str(cpu) if cpu else "256",
            memory=str(memory) if memory else "512",
            runtimePlatform={
                "cpuArchitecture": "ARM64",
                "operatingSystemFamily": "LINUX",
            },
        )["taskDefinition"]["taskDefinitionArn"]

        if (
            service_desc := ecs_client.describe_services(cluster=cluster, services=[service_name])["services"]
        ) and service_desc[0]["status"] == "ACTIVE":
            CLIClient.emit(f"Service {service_name} found. Updating service.")
            ecs_client.update_service(
                cluster=cluster,
                service=service_name,
                forceNewDeployment=True,
                taskDefinition=task_definition_arn,
                desiredCount=1,
            )

        else:
            CLIClient.emit(f"Service {service_name} not found. Creating new service.")
            ecs_client.create_service(
                cluster=cluster,
                serviceName=service_name,
                taskDefinition=task_definition_arn,
                desiredCount=1,
                launchType="FARGATE",
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": subnets,
                        "securityGroups": security_groups,
                        "assignPublicIp": "ENABLED",
                    }
                },
                loadBalancers=[
                    {
                        "targetGroupArn": target_group_arn,  # type: ignore
                        "containerName": service_name,
                        "containerPort": containers[0].container_port,
                    }
                ],
                enableECSManagedTags=True,
                propagateTags="SERVICE",
            )

        if cls._poll_service_status(service_name):
            CLIClient.emit("Service started successfully.")
            return True

        CLIClient.emit("Failed to start service.")
        return False

    @classmethod
    def _poll_service_status(cls, service_name: str) -> bool:
        """
        service_name (str): The name of the service to poll.

        Polls ecs.describe_service until the service is running.
        Returns False after ~5 minutes of polling.
        """
        import boto3

        client = boto3.client("ecs")
        for _ in range(30):
            res = client.describe_services(cluster="DemoCluster", services=[service_name])
            if (
                res["services"]
                and res["services"][0]["desiredCount"] == res["services"][0]["runningCount"]
                and res["services"][0]["pendingCount"] == 0
            ):
                return True
            time.sleep(10)

        return False
