"""
Tools for integration with OpenAI's Structured Outputs (and any other LLM that supports structured output).

Use: Tools are used to provide operators methods that can be used to complete a task. Tools are defined as classes with methods that can be called. Operators are expected to return a list of called tools with syntax [Tool1, Tool2, ...]
A returned tool syntax is expected to be evaluated using eval(tool_name.tool_call(params))
eg) [AwsTool.deploy_to_aws(example_directory_name)]

1) String representation of the tool tells operator what tools are available
    a) Currently implemented with a metaclass defining __str__ for a class (a metaclass instance). The benefit of this is that the class does not need to be instantiated to get its string representation. Similarly, with staticmethods, the class does not need to be instantiated to use its methods
        - The benefit of keeping tools inside a toolclass is to provide the tool organized helper functions.
    b) Possible alternatives involving removal of tool class. https://stackoverflow.com/questions/20093811/how-do-i-change-the-representation-of-a-python-function. This would remove the complicated metaclass entirely in favor of a decorated function.

2) TODO: Update prompting to get good tool call behavior.

Example:
In this example, TestTool is an example Tool that can be provided to an operator qna.
Tools should have syntax documented in their docstrings so the operator knows how to use them.

class TestTool(metaclass=ToolClass):
    @classmethod
    def test(cls, idk: str, another: int = 5) -> str:
        '''idk: (Description of idk goes here)
        another: (Description of another goes here)
        Returns a string
        '''
        return f"Tested {idk}!"

    def another_method(self):
        pass


class testOperator(operators.Operator):
    def __init__(
        self,
        clients={'openai': OpenAIClient()},
        instructions=("You are a software developer. You will answer completely, concisely, and accurately."
        "When provided tools, you will first answer, then use tools to complete the task."),
    ):
        super().__init__(clients, instructions)

    @operators.Operator.qna
    def use_tools(self, question, tools: List[MetaTool]):

        query = ""
        if tools:
            query += '''Here are your available tools:\
                Either call the tool with its specified syntax, or leave its field blank.\n'''
            for tool in tools:
                query += str(tool)

        query += '''\n\n{question}'''.format(question=question)
        return query
"""  # noqa: E501

import inspect
import os
import socket
import time
from datetime import datetime, timezone
from textwrap import dedent
from typing import Dict, Optional

import boto3

from .clients import CLIClient, RestApiClient
from .models.responses import ProjectDirectory

TOOLS_REGISTRY = {}


class MetaTool(type):
    """
    This metaclass enables dynamic string representation of class objects without needing to instantiate them.
    """

    def __new__(cls, name, bases, attrs):
        method_info = []
        for attr, value in attrs.items():
            if attr.startswith("_"):
                continue
            if callable(value) or isinstance(value, (classmethod, staticmethod)):
                func = value.__func__ if isinstance(value, (classmethod, staticmethod)) else value

                docstring = func.__doc__.strip() if func.__doc__ else "No docstring provided"

                signature = inspect.signature(func)
                params = []
                for param_name, param in signature.parameters.items():
                    param_str = param_name
                    if param.annotation != inspect.Parameter.empty:
                        param_str += f": {param.annotation.__name__}"
                    if param.default != inspect.Parameter.empty:
                        param_str += f" = {param.default}"
                    params.append(param_str)

                return_str = (
                    f" -> {signature.return_annotation.__name__}"
                    if signature.return_annotation != inspect.Signature.empty
                    and signature.return_annotation is not None
                    else ""
                )

                method_signature = f"{attr}({', '.join(params)}){return_str}"
                method_info.append(f"{method_signature}\n\t{docstring}")

        attrs['_str_representation'] = f"{name} Tool with methods:\n" + "\n".join(
            f"   - {info}" for info in method_info
        )
        new_class = super().__new__(cls, name, bases, attrs)
        TOOLS_REGISTRY[name] = new_class
        return new_class

    def __str__(cls):
        return cls._str_representation

    def __repr__(cls):
        return str(cls)


def invoke_tool(tool_name: str, tool_function: str, tool_parameters: str, tool_keyword_parameters: dict[str, str]):
    """
    Throws AttributeError if the function doesn't exist.
    Throws TypeError if the parameters are wrong.
    """
    func = getattr(TOOLS_REGISTRY[tool_name], tool_function)
    return func(*tool_parameters, **tool_keyword_parameters)


class RestApiTool(metaclass=MetaTool):
    @classmethod
    def get(cls, url: str, headers: dict = {}, params: dict = {}, data: dict = {}):
        """
        Make a GET request to the specified url

        Throws an error if the request was unsuccessful after retries
        """
        client = RestApiClient()
        resp = client.get(url, headers=headers, params=params, data=data)
        if not resp.ok:
            # Request failed
            CLIClient.emit(f"Failed GET request to {url}: {resp.status_code} {resp.json()}")
            resp.raise_for_status()
        return resp.json()  # return unwrapped data

    @classmethod
    def post(cls, url: str, headers: dict = {}, params: dict = {}, data: dict = {}, json: dict = {}):
        """
        Make a POST request to the specified url

        Throws an error if the request was unsuccessful after retries
        """
        client = RestApiClient()
        resp = client.post(url, headers=headers, params=params, data=data, json=json)
        if not resp.ok:
            # Request failed
            CLIClient.emit(f"Failed POST request to {url}: {resp.status_code} {resp.json()}")
            resp.raise_for_status()
        return resp.json()  # return unwrapped data


class AwsTool(metaclass=MetaTool):
    SHARED_VOLUME = "/shared"
    results: Dict[str, Dict] = {}  # Emulates a DB for retrieving project directory objects by key.
    DIND_BUILDER_HOST = "localhost"
    DIND_BUILDER_PORT = 5002

    @classmethod
    def build_and_deploy_to_aws(cls, project_directory_name: str) -> None:
        """
        project_directory_name (str): The name of the project directory to deploy.
        """
        deployed, image_uri = cls._build_and_push_image(project_directory_name)
        if deployed:
            cls._deploy_image(image_uri)
        else:
            CLIClient.emit("Failed to deploy project")

    @classmethod
    def _build_and_push_image(cls, project_directory_name: str) -> tuple[bool, str]:
        """
        Calls dind-builder service to build and push the image to ECR.
        """
        project_directory = ProjectDirectory.model_validate(cls.results[project_directory_name])
        project_directory_name = project_directory_name.lower().replace(" ", "-").replace("_", "-")
        build_dir_path = os.path.join(cls.SHARED_VOLUME, project_directory_name)
        os.makedirs(build_dir_path, exist_ok=True)

        dockerfile_content = dedent(
            f"""
            FROM python:3.11.9-slim-bookworm
            WORKDIR /app
            RUN pip install flask concrete-operators
            COPY . .
            ENV OPENAI_API_KEY={os.environ['OPENAI_API_KEY']}
            ENV OPENAI_TEMPERATURE=0
            CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
            """
        )
        start_script = dedent(
            """
            #!/bin/sh
            set -e
            if ! command -v flask &> /dev/null
            then
                echo "Flask is not installed. Installing..."
                pip install flask
            fi

            if ! pip show concrete-operators &> /dev/null
            then
                echo "concrete-operators is not installed. Installing..."
                pip install concrete-operators
            fi

            if [ -z "$OPENAI_API_KEY" ]
            then
                echo "Error: OPENAI_API_KEY is not set. Please set it before running this script."
                exit 1
            fi
            flask run --host=0.0.0.0 --port=80
            """
        )

        with open(os.path.join(build_dir_path, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)
        with open(os.path.join(build_dir_path, "start.sh"), "w") as f:
            f.write(start_script)

        for project_file in project_directory.files:
            file_path = os.path.join(build_dir_path, project_file.file_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(project_file.file_contents)

        max_retries = 2
        for _ in range(max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((cls.DIND_BUILDER_HOST, cls.DIND_BUILDER_PORT))
                    s.sendall(project_directory_name.encode())
                break
            except Exception as e:
                print(e)
                time.sleep(5)

        image_uri = f"008971649127.dkr.ecr.us-east-1.amazonaws.com/{project_directory_name}"
        if not cls._poll_image_status(project_directory_name):
            CLIClient.emit("Failed to build and push image.")
            return (False, "")
        else:
            CLIClient.emit("Image built and pushed successfully.")
            return (True, image_uri)

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
                if res['imageDetails'] and res['imageDetails'][0]['imagePushedAt'] > cur_time:
                    return True
            except ecr_client.exceptions.RepositoryNotFoundException:
                pass
            time.sleep(10)

        return False

    @classmethod
    def _deploy_image(
        cls,
        image_uri: str,
        custom_name: Optional[str] = None,
        cpu: Optional[int] = None,
        memory: Optional[int] = None,
        listener_rule: Optional[dict] = None,
    ) -> bool:
        """
        image_uri (str): The URI of the image to deploy.
        custom_name (str): Custom service name, defaults to image name
        cpu (int): The amount of CPU to allocate to the service
        memory (int): The amount of memory to allocate to the service
        listener_rule: Dictionary of {field: str, value: str} for the listener rule. Defaults to {'field': 'host-header', 'value': f"{service_name}.abop.ai"}}
        """  # noqa: E501
        # TODO: separate out clients and have a better interaction for attaching vars
        ecs_client = boto3.client("ecs")
        elbv2_client = boto3.client("elbv2")

        # https://devops.stackexchange.com/questions/11101/should-aws-arn-values-be-treated-as-secrets
        # May eventually move these out to env, but not first priority.
        cluster = "DemoCluster"
        service_name = custom_name or image_uri.split("/")[-1].split(":")[0]
        task_name = service_name
        target_group_name = service_name
        vpc = "vpc-022b256b8d0487543"
        subnets = ["subnet-0ba67bfb6421d660d"]  # subnets considered for placement
        security_group = "sg-0463bb6000a464f50"  # allows traffic from ALB
        execution_role_arn = "arn:aws:iam::008971649127:role/ecsTaskExecutionWithSecret"
        listener_arn = (
            "arn:aws:elasticloadbalancing:us-east-1:008971649127:listener/app/ConcreteLoadBalancer"
            "/f7cec30e1ac2e4a4/451389d914171f05"
        )

        target_group_arn = None
        if not listener_rule:
            rule_field = 'host-header'
            rule_value = f'{service_name}.abop.ai'
        else:
            rule_field = listener_rule.get('field', None) or 'host-header'
            rule_value = listener_rule.get('value', None) or f'{target_group_name}.abop.ai'

        rules = elbv2_client.describe_rules(ListenerArn=listener_arn)['Rules']
        for rule in rules:
            if (
                rule['Conditions']
                and rule['Conditions'][0]['Field'] == rule_field
                and rule['Conditions'][0]['Values'][0] == rule_value
            ):
                target_group_arn = rule['Actions'][0]['TargetGroupArn']

        if not target_group_arn:
            # Calculate minimum unused rule priority
            rule_priorities = [int(rule['Priority']) for rule in rules if rule['Priority'] != 'default']
            if set(range(1, len(rules))) - set(rule_priorities):
                listener_rule_priority = min(set(range(1, len(rules))) - set(rule_priorities))
            else:
                listener_rule_priority = len(rules) + 1

            target_group_arn = elbv2_client.create_target_group(
                Name=target_group_name,
                Protocol='HTTP',
                Port=80,
                VpcId=vpc,
                TargetType='ip',
                HealthCheckEnabled=True,
                HealthCheckPath='/',
                HealthCheckIntervalSeconds=30,
                HealthCheckTimeoutSeconds=5,
                HealthyThresholdCount=2,
                UnhealthyThresholdCount=2,
            )['TargetGroups'][0]['TargetGroupArn']

            elbv2_client.create_rule(
                ListenerArn=listener_arn,
                Priority=listener_rule_priority,
                Conditions=[{'Field': rule_field, 'Values': [rule_value]}],
                Actions=[
                    {
                        'Type': 'forward',
                        'TargetGroupArn': target_group_arn,
                    }
                ],
            )

        task_definition_arn = ecs_client.register_task_definition(
            family=task_name,
            executionRoleArn=execution_role_arn,
            networkMode="awsvpc",
            requiresCompatibilities=["FARGATE"],
            containerDefinitions=[
                {
                    "name": task_name,
                    "image": image_uri,
                    "portMappings": [{"containerPort": 80}],
                    "essential": True,
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": "fargate-demos",
                            "awslogs-region": "us-east-1",
                            "awslogs-stream-prefix": "fg",
                        },
                    },
                }
            ],
            cpu=str(cpu) if cpu else "256",
            memory=str(memory) if memory else "512",
            runtimePlatform={
                'cpuArchitecture': 'ARM64',
                'operatingSystemFamily': 'LINUX',
            },
        )['taskDefinition']['taskDefinitionArn']

        if (
            service_desc := ecs_client.describe_services(cluster=cluster, services=[service_name])['services']
        ) and service_desc[0]['status'] == 'ACTIVE':
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
                        "securityGroups": [security_group],
                        "assignPublicIp": "ENABLED",
                    }
                },
                loadBalancers=[
                    {
                        "targetGroupArn": target_group_arn,
                        "containerName": task_name,
                        "containerPort": 80,
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
        client = boto3.client("ecs")
        for _ in range(30):
            res = client.describe_services(cluster="DemoCluster", services=[service_name])
            if (
                res['services']
                and res["services"][0]['desiredCount'] == res['services'][0]['runningCount']
                and res['services'][0]['pendingCount'] == 0
            ):
                return True
            time.sleep(10)

        return False


class GithubTool(metaclass=MetaTool):
    """
    Facilitates interactions with github through its Restful API
    """

    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")}',
        'X-GitHub-Api-Version': '2022-11-28',
    }

    @classmethod
    def make_pr(cls, owner: str, repo: str, branch: str, title: str = "PR", base: str = "main") -> dict:
        """
        Make a pull request on the target repo

        e.g. make_pr('abstractoperators', 'concrete', 'kent/http-tool')

        Args
            owner (str): The organization or accounts that owns the repo.
            repo (str): The name of the repository.
            branch (str): The head branch being merged into the base.
            title (str): The title of the PR being created.
            base (str): The title of the branch that changes are being merged into.
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        json = {'title': f'[ABOP] {title}', 'head': branch, 'base': base}
        return RestApiTool.post(url, headers=cls.headers, json=json)
