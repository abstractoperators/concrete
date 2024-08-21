"""
Tools for integration with OpenAI's Structured Outputs (and any other LLM that supports structured output).

Use: Tools are used to provide operators methods that can be used to complete a task. Tools are defined as classes with methods that can be called. Operators are expected to return a list of called tools with syntax [Tool1, Tool2, ...]
A returned tool syntax is expected to be evaluated using eval(tool_name.tool_call(params))
eg) [DeployToAWS.deploy_to_aws(example_directory_name)]

1) String representation of the tool tells operator what tools are available
    a) Currently implemented with a metaclass defining __str__ for a class (a metaclass instance). The benefit of this is that the class does not need to be instantiated to get its string representation. Similarly, with staticmethods, the class does not need to be instantiated to use its methods
        - The benefit of keeping tools inside a toolclass is to provide the tool organized helper functions.
    b) Possible alternatives involving removal of tool class. https://stackoverflow.com/questions/20093811/how-do-i-change-the-representation-of-a-python-function. This would remove the complicated metaclass entirely in favor of a decorated function.

2) TODO: Fix tool nesting.
    a) ATM, all responses inherit from Tools class. This is good, but we only want the outermost response to have a tools field.
    eg) ProjectFile inherits from Tools, and so does ProjectDirectory.
    ProjectDirectory should have a list of ProjectFiles, but we only want ProjectDirectory to have tools.

3) TODO: Update prompting to get good tool call behavior.

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
import shutil
import time
from textwrap import dedent
from typing import Dict, Generator

import boto3

from .operator_responses import ProjectDirectory


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
        return super().__new__(cls, name, bases, attrs)

    def __str__(cls):
        return cls._str_representation

    def __repr__(cls):
        return str(cls)


class DeployToAWS(metaclass=MetaTool):
    SHARED_VOLUME = "/shared"  # host machine directory shared with the container
    results: Dict[str, Dict] = {}  # Emulates a DB for retrieving project directory objects by key.
    DIND_BUILDER_HOST = "localhost"
    DIND_BUILDER_PORT = 5002

    @classmethod
    def deploy_to_aws(cls, project_directory_name: str) -> bool:
        """
        project_directory_name (str): The name of the project directory to deploy.
        """
        build_dir_path, dockerfile_filepath, project_directory_name = DeployToAWS.build_image(project_directory_name)
        return DeployToAWS.deploy_image(build_dir_path, dockerfile_filepath, project_directory_name)

    @classmethod
    def _poll_service_status(cls, service_name: str) -> bool:
        """
        service_name (str): The name of the service to poll.

        Polls ecs.describe_service until stabilityStatus = STEADY_STATE, then returns true
        Returns false after ~5 minutes of polling.
        """
        client = boto3.client("ecs")
        for _ in range(30):
            res = client.describe_services(cluster="DemoCluster", services=[service_name])
            try:
                if res["services"][0]['desiredCount'] == res['services'][0]['runningCount']:
                    return True
            except Exception as e:
                print(e)
            time.sleep(10)

        return False

    @classmethod
    def pull_image(cls):
        """pulls an image from an arbitrary registry"""
        pass

    @classmethod
    def build_image(cls, project_directory_name: str):
        default_dockerfile = (
            'Dockerfile',
            dedent(
                f"""
            FROM python:3.11.9-slim-bookworm
            WORKDIR /app
            RUN pip install flask concrete-operators
            COPY . .
            ENV OPENAI_API_KEY={os.environ['OPENAI_API_KEY']}
            ENV OPENAI_TEMPERATURE=0
            CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]
            """
            ),
        )
        dockerfile_filepath, dockerfile_content = cls.results[project_directory_name].pop(
            'dockerfile', default_dockerfile
        )

        default_start_script = (
            'start.sh',
            dedent(
                """
            #!/bin/sh
            set -e
            flask run --host=0.0.0.0 --port=80
            """
            ),
        )
        start_script_filepath, start_script_content = cls.results[project_directory_name].pop(
            'start_script', default_start_script
        )

        default_docker_compose = (None, None)  # ('docker-compose.yml', service), overrides dockerfile
        docker_compose_filepath, docker_compose_services = cls.results[project_directory_name].pop(
            'docker_compose_services', default_docker_compose
        )

        # Add a shortcircuit for projects that have already been written to shared.
        if not os.path.exists(os.path.join(cls.SHARED_VOLUME, project_directory_name)):
            project_directory = ProjectDirectory.model_validate(cls.results[project_directory_name])
            build_dir_path = os.path.join(cls.SHARED_VOLUME, project_directory_name)
            os.makedirs(build_dir_path, exist_ok=True)

            with open(os.path.join(build_dir_path, dockerfile_filepath), "w") as f:
                f.write(dockerfile_content)

            with open(os.path.join(build_dir_path, start_script_filepath), "w") as f:
                f.write(start_script_content)

            for project_file in project_directory.files:
                file_path = os.path.join(build_dir_path, project_file.file_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(project_file.file_contents)
                # max_retries = 2
        # for _ in range(max_retries):
        #     try:
        #         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        #             print(f'Connecting to {cls.DIND_BUILDER_HOST}:{cls.DIND_BUILDER_PORT}')
        #             s.connect((cls.DIND_BUILDER_HOST, cls.DIND_BUILDER_PORT))
        #             build_info = {
        #                 "build_dir": build_dir_path,
        #             }
        #             json_data = json.dumps(build_info)
        #             s.sendall((json_data + '\n').encode('utf-8'))
        #         break
        #     except Exception as e:
        #         print(e)
        #         time.sleep(5)

        # return cls._poll_service_status(project_directory_name)

        return build_dir_path, dockerfile_filepath, project_directory_name

    @classmethod
    def _deploy_image(cls, image_uri) -> bool:
        """
        Deploys an image_uri to ECS
        """
        ecs_client = boto3.client("ecs")
        elbv2_client = boto3.client("elbv2")

        # Find listener priority to deploy to
        cluster = "DemoCluster"
        service_name = image_uri.split("/")[-1]
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
        rules = elbv2_client.describe_rules(ListenerArn=listener_arn)['Rules']
        rule_priorities = [int(rule['Priority']) for rule in rules if rule['Priority'] != 'default']
        if set(range(1, len(rules))) - set(rule_priorities):
            listener_rule_priority = min(set(range(1, len(rules))) - set(rule_priorities))
        else:
            listener_rule_priority = len(rules) + 1

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
            cpu='256',
            memory='512',
            runtimePlatform={
                'cpuArchitecture': 'ARM64',
                'operatingSystemFamily': 'LINUX',
            },
        )['taskDefinition']['taskDefinitionArn']

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
        )['TargetGroups'][0][
            'TargetGroupArn'
        ]  # A little confused as to why this is a list?

        elbv2_client.create_rule(
            ListenerArn=listener_arn,
            Priority=listener_rule_priority,
            Conditions=[{'Field': 'host-header', 'Values': [f'{target_group_name}.abop.ai']}],
            Actions=[
                {
                    'Type': 'forward',
                    'TargetGroupArn': target_group_arn,
                }
            ],
        )

        if ecs_client.describe_services(cluster=cluster, services=[service_name])['services']:
            ecs_client.update_service(
                cluster=cluster,
                service=service_name,
                forceNewDeployment=True,
                taskDefinition=task_definition_arn,
            )

        else:
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

        return cls._poll_service_status(service_name)


class GitHubAPI(metaclass=MetaTool):
    """
    Implements methods for interacting with GitHub API.
    Provides chained tools for deploying a repo to AWS.
    """

    # Requires: GH Tool Deploy Key PRIVATE key on whatever machine is running this tool
    # (technically with only pull access on a public repo this is not necessary)

    @classmethod
    def _get_repo_contents(cls, org: str, repo_name: str):
        """
        org (str): The name of the organization to which the repo belongs.
        repo_name (str): The name of the repo to get contents from.
        """
        url = f'https://github.com/{org}/{repo_name}.git'
        if os.path.isdir(f'/shared/{repo_name}'):
            shutil.rmtree(f'/shared/{repo_name}')
        os.system(f'git clone {url} /shared/{repo_name}')  # nosec

    @classmethod
    def deploy_repo(cls, org: str, repo_name: str) -> None:
        """
        repo_name (str): The name of the repo to deploy.
        branch (str): The branch to deploy from.
        """
        cls._get_repo_contents(org, repo_name)
        deploy_dir = f'/shared/{repo_name}'

        # Look for a dockerfile?
        for dockerfile_filepath in cls._find_dockerfiles(repo_name):
            with open(f'{deploy_dir}/{dockerfile_filepath}') as f:
                dockerfile_content = f.read()
            DeployToAWS.results[repo_name].extend({'dockerfile_context': (dockerfile_filepath, dockerfile_content)})
            # Call an Operator to deploy it? Or just do it manually? Not sure....
            DeployToAWS.deploy_repo(repo_name)

    @classmethod
    def _find_dockerfiles(cls, repo_name: str) -> Generator[str, None, None]:
        """
        repo_name (str): The name of the repo to deploy.
        Returns a list of paths to Dockerfiles in the repo
        """
        for root, _, files in os.walk(f'/shared/{repo_name}'):
            relative_root = os.path.relpath(root, f'/shared/{repo_name}')
            for file in files:
                if file.startswith('Dockerfile'):
                    relative_path = os.path.join(relative_root, file)
                    yield relative_path

    # GHA: call this tool, it pings deploytoaws
    #
