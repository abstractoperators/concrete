import base64
import inspect
import io
import os
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from typing import Dict, Optional

import requests
from dotenv import dotenv_values
from requests import Response

from concrete.clients import CLIClient
from concrete.clients.http import HTTPClient
from concrete.models.base import ConcreteModel
from concrete.models.messages import Tool

TOOLS_REGISTRY: dict[str, "MetaTool"] = {}


def tool_name_to_class(tool_name: str) -> "MetaTool":
    """
    Returns the class object of a tool given its name.
    """
    return TOOLS_REGISTRY[tool_name]


def invoke_tool(tool: Tool):
    """
    Invokes a tool on a message.
    Throws KeyError if the tool doesn't exist.
    Throws AttributeError if the function on the tool doesn't exist.
    Throws TypeError if the parameters are wrong.
    """
    tool_name = tool.tool_name
    tool_function = tool.tool_method
    tool_parameters = tool.tool_parameters
    kwargs = {param.name: param.value for param in tool_parameters}
    CLIClient.emit(f"Invoking {tool_name}.{tool_function} with {kwargs}")

    func = getattr(tool_name_to_class(tool_name), tool_function)

    return func(**kwargs)


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
                        if hasattr(param.annotation, '__name__'):
                            param_str += f": {param.annotation.__name__}"
                        else:
                            # Handle Union types
                            param_str += f": {str(param.annotation)}"
                    if param.default != inspect.Parameter.empty:
                        param_str += f" = {param.default}"
                    params.append(param_str)

                return_str = ""
                if signature.return_annotation != inspect.Signature.empty:
                    if hasattr(signature.return_annotation, '__name__'):
                        return_str = f" -> {signature.return_annotation.__name__}"
                    else:
                        # Handle Union types
                        return_str = f" -> {str(signature.return_annotation)}"

                method_signature = f"{attr}({', '.join(params)}){return_str}"
                method_info.append(f"{method_signature}\n\t{docstring}")

        attrs["_str_representation"] = f"Tool Name: {name}\nTool Methods:\n" + "\n".join(
            f"   - {info}" for info in method_info
        )
        new_class = super().__new__(cls, name, bases, attrs)
        TOOLS_REGISTRY[name] = new_class
        return new_class

    def __str__(cls):
        return cls._str_representation

    def __repr__(cls):
        return str(cls)


class HTTPTool(metaclass=MetaTool):
    @classmethod
    def _process_response(cls, resp: Response, url: str) -> bytes:
        if not resp.ok:
            CLIClient.emit(f"Failed request to {url}: {resp.status_code} {resp}")
            resp.raise_for_status()

        return resp.content

    @classmethod
    def request(cls, method: str, url: str, **kwargs) -> bytes:
        """
        Make an HTTP request to the specified url
        Throws an error if the request was unsuccessful
        """
        resp = HTTPClient().request(method, url, **kwargs)
        return cls._process_response(resp, url)

    @classmethod
    def get(cls, url: str, **kwargs) -> Response:
        return cls.request('GET', url, **kwargs)

    @classmethod
    def post(cls, url: str, **kwargs) -> Response:
        return cls.request('POST', url, **kwargs)

    @classmethod
    def put(cls, url: str, **kwargs) -> Response:
        return cls.request('PUT', url, **kwargs)

    @classmethod
    def delete(cls, url: str, **kwargs) -> Response:
        return cls.request('DELETE', url, **kwargs)


class RestApiTool(HTTPTool):
    @classmethod
    def _process_response(cls, resp: Response, url: Optional[str] = None) -> bytes:
        if not resp.ok:
            CLIClient.emit(f"Failed request to {url}: {resp.status_code} {resp}")
            resp.raise_for_status()
        content_type = resp.headers.get('content-type', '')
        if 'application/json' in content_type:
            return resp.json()
        if 'text' in content_type:
            return resp.text
        return resp.content


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
    results: Dict[str, Dict] = {}  # Emulates a DB for retrieving project directory objects by key.
    DIND_BUILDER_HOST = "localhost"
    DIND_BUILDER_PORT = 5002

    @classmethod
    def _poll_image_status(cls, repo_name: str) -> bool:
        """
        Polls ECR until an image is pushed. True if image is pushed, False otherwise.
        Returns False after ~5 minutes of polling.
        """
        # TODO smarter way of detecting a 'new' image besides comparing push date.
        import boto3

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
                {
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
                        {'name': k, 'value': v} for k, v in dotenv_values(container.container_env_file).items()
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

        elbv2_client = boto3.client('elbv2')
        target_group_arn = None
        if listener_rule is None:
            listener_rule_field = 'host-header'
            listener_rule_value = f'{target_group_name}.abop.ai'
        else:
            if listener_rule.get('field') and listener_rule.get('value'):
                listener_rule_field = str(listener_rule.get('field'))
                listener_rule_value = str(listener_rule.get('value'))
            else:
                raise ValueError('listener_rule must contain both field and value keys.')

        arn_prefix = listener_arn.split(':listener')[0]
        # Replace rule for target group if it already exists
        existing_rules = elbv2_client.describe_rules(ListenerArn=listener_arn)['Rules']
        target_group_arn = None
        for rule in existing_rules:
            if rule['Actions'][0]['Type'] == 'forward' and rule["Actions"][0]["TargetGroupArn"].startswith(
                arn_prefix + f":targetgroup/{target_group_name}"
            ):
                elbv2_client.delete_rule(RuleArn=rule['RuleArn'])

        if target_group_arn is None:
            target_group_arn = elbv2_client.create_target_group(
                Name=target_group_name,
                Protocol='HTTP',
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
                {
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
                        {'name': k, 'value': v} for k, v in dotenv_values(container.container_env_file).items()
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
                        "targetGroupArn": target_group_arn,
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


class GithubTool(metaclass=MetaTool):
    """
    Facilitates interactions with github through its Restful API
    """

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f'Bearer {os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")}',
        "X-GitHub-Api-Version": "2022-11-28",
    }

    @classmethod
    def create_pr(cls, org: str, repo: str, head: str, access_token: str, title: str, base: str = "main"):
        """
        Make a pull request on the target repo

        e.g. make_pr('abstractoperators', 'concrete', 'kent/http-tool')

        Args
            org (str): The organization or accounts that owns the repo.
            repo (str): The name of the repository.
            head (str): The head branch being merged into the base.
            title (str): The title of the PR being created.
            base (str): The title of the branch that changes are being merged into.
        """
        url = f"https://api.github.com/repos/{org}/{repo}/pulls"
        json = {"title": f"[ABOP] {title}", "head": head, "base": base}
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {access_token}',
            'X-GitHub-Api-Version': '2022-11-28',
        }

        try:
            RestApiTool.post(url, headers=headers, json=json)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                CLIClient.emit("PR already exists.")
            else:
                CLIClient.emit("Failed to create PR: " + str(e))

    @classmethod
    def create_branch(cls, org: str, repo: str, new_branch: str, access_token: str, base_branch: str = 'main'):
        """
        Make a branch called new_branch from the latest commit on base_name

        Args
            org (str): Organization or account owning the repo
            repo (str): The name of the repository
            base_branch (str): The name of the branch to branch from.
            new_branch (str): The name of the new branch (e.g. 'michael/new-feature')
            access_token(str): Fine-grained token with at least 'Contents' repository write access.
                https://docs.github.com/en/rest/git/refs?apiVersion=2022-11-28#create-a-reference--fine-grained-access-tokens
        """
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {access_token}',
            'X-GitHub-Api-Version': '2022-11-28',
        }

        # Get SHA of latest commit on base branch
        url = f"https://api.github.com/repos/{org}/{repo}/branches/{base_branch}"
        base_sha = RestApiTool.get(url, headers=headers)['commit']['sha']

        # Create new branch from base branch
        url = f"https://api.github.com/repos/{org}/{repo}/git/refs"
        json = {"ref": "refs/heads/" + new_branch, "sha": base_sha}
        try:
            RestApiTool.post(url=url, headers=headers, json=json)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 422:
                CLIClient.emit("Branch already exists.")
            else:
                CLIClient.emit("Failed to create branch: " + str(e))

    @classmethod
    def delete_branch(cls, org: str, repo: str, branch: str, access_token: str):
        """
        Deletes a branch from the target repo
        https://docs.github.com/en/rest/git/refs?apiVersion=2022-11-28#delete-a-reference

        Args
            org (str): Organization or account owning the rep
            repo (str): Repository name
            branch (str): Branch to delete
            access_token(str): Fine-grained token with at least 'Contents' repository write access.
        """
        url = f'https://api.github.com/repos/{org}/{repo}/git/refs/heads/{branch}'
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {access_token}',
            'X-GitHub-Api-Version': '2022-11-28',
        }

        resp = requests.delete(url, headers=headers, timeout=10)
        if resp.status_code == 204:
            CLIClient.emit(f'{branch} deleted successfully.')
        else:
            CLIClient.emit(f'Failed to delete {branch}.' + str(resp.json()))

    @classmethod
    def put_file(
        cls, org: str, repo: str, branch: str, commit_message: str, path: str, file_contents: str, access_token: str
    ):
        """
        Updates/Create a file on the target repo + commit.

        Args
            org (str): Organization or account owning the repo
            repo (str): The name of the repository
            branch (str): The branch that the commit is being made to.
            commit_message (str): The commit message.
            path: (str): Path relative to root of repo
            access_token(str): Fine-grained token with at least 'Contents' repository write access.
        """
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {access_token}',
            'X-GitHub-Api-Version': '2022-11-28',
        }
        # Get blob sha
        url = f'https://api.github.com/repos/{org}/{repo}/contents/{path}'
        json = {'ref': branch}
        resp = requests.get(url, headers=headers, params=json, timeout=10)

        # TODO switch to RestApiTool; Handle 404 better.
        if resp.status_code == 404:
            sha = None
        else:
            sha = resp.json().get('sha')

        url = f'https://api.github.com/repos/{org}/{repo}/contents/{path}'
        json = {
            "message": commit_message,
            "content": base64.b64encode(file_contents.encode('utf-8')).decode('ascii'),
            "branch": branch,
        }
        if sha:
            json['sha'] = sha
        RestApiTool.put(url, headers=headers, json=json)

    @classmethod
    def get_diff(cls, org: str, repo: str, base: str, head: str, access_token: str) -> str:
        """
        Retrieves diff of base compared to compare.

        Args
            org (str): Organization or account owning the repo
            repo (str): The name of the repository
            base (str): The name of the branch to compare against.
            head (str): The name of the branch to compare
            access_token(str): Fine-grained token with at least 'Contents' repository read access.
        """
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {access_token}',
            'X-GitHub-Api-Version': '2022-11-28',
        }

        url = f'https://api.github.com/repos/{org}/{repo}/compare/{base}...{head}'
        diff_url = RestApiTool.get(url, headers=headers)['diff_url']
        diff = RestApiTool.get(diff_url)
        return diff

    @classmethod
    def get_changed_files(
        cls, org: str, repo: str, base: str, head: str, access_token: str
    ) -> list[tuple[list[str], str]]:
        """
        Returns a list of changed files between two commits
        [([a/file_path, b/file_path], uncleaned_diff)]
        """
        diff = GithubTool.get_diff(org, repo, base, head, access_token)
        files_with_diffs = diff.split('diff --git')[1:]  # Skip the first empty element
        return [(file.split('\n', 1)[0].split(), file) for file in files_with_diffs]

    @classmethod
    def fetch_branch(cls, org: str, repo: str, branch: str, access_token: str) -> str:
        """
        Downloads contents of branches latest commit to dest_path.
        """
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {access_token}',
            'X-GitHub-Api-Version': '2022-11-28',
        }

        url = f'https://api.github.com/repos/{org}/{repo}/zipball/refs/heads/{branch}'

        dest_path = tempfile.mkdtemp(prefix="GithubTool-")

        content = HTTPTool.get(url, headers=headers)

        with zipfile.ZipFile(io.BytesIO(content)) as zip_ref:
            zip_ref.extractall(dest_path)
            top_level_dir = zip_ref.namelist()[0].split('/')[0]

        # Full path to the extracted directory.
        full_path = os.path.join(dest_path, top_level_dir)

        CLIClient.emit(f"{org}/{repo}/{branch} has been downloaded to '{full_path}'.")
        return full_path


class Arithmetic(metaclass=MetaTool):
    @classmethod
    def add(cls, x: int, y: int) -> int:
        '''
        x (int): The first number
        y (int): The second number

        Returns the sum of x and y
        '''
        return x + y

    @classmethod
    def subtract(cls, x: int, y: int) -> int:
        '''
        x (int): The first number
        y (int): The second number

        Returns the difference of x and y
        '''
        return x - y
