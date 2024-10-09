import base64
import fnmatch
import inspect
import io
import os
import socket
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from queue import Queue
from textwrap import dedent
from typing import Dict, Optional
from uuid import UUID

import requests
from dotenv import dotenv_values
from requests import Response

from concrete.clients import OpenAIClient

from .clients import CLIClient, HTTPClient
from .db import crud
from .db.orm import Session, models
from .models.base import ConcreteModel
from .models.messages import ChildNodeSummary, NodeSummary, ProjectDirectory

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

        attrs["_str_representation"] = f"{name} Tool with methods:\n" + "\n".join(
            f"   - {info}" for info in method_info
        )
        new_class = super().__new__(cls, name, bases, attrs)
        TOOLS_REGISTRY[name] = new_class
        return new_class

    def __str__(cls):
        return cls._str_representation

    def __repr__(cls):
        return str(cls)


def invoke_tool(tool_name: str, tool_function: str, tool_parameters: str):
    """
    Throws KeyError if the tool doesn't exist.
    Throws AttributeError if the function on the tool doesn't exist.
    Throws TypeError if the parameters are wrong.
    """
    func = getattr(TOOLS_REGISTRY[tool_name], tool_function)
    return func(*tool_parameters)


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
    def build_and_deploy_to_aws(cls, project_directory_name: str) -> None:
        """
        project_directory_name (str): The name of the project directory to deploy.
        """
        pushed, image_uri = cls._build_and_push_image(project_directory_name)
        if pushed:
            cls._deploy_service(
                [
                    Container(
                        image_uri=image_uri,
                        container_name=project_directory_name,
                        container_port=80,
                        container_env_file="",
                    )
                ]
            )
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
    def _deploy_service(
        cls,
        containers: list[Container],
        service_name: Optional[str] = None,
        cpu: int = 256,
        memory: int = 512,
        listener_rule: Optional[dict] = None,
        subnets: list[str] = ["subnet-0ba67bfb6421d660d"],
        vpc: str = "vpc-022b256b8d0487543",
        security_groups: list[str] = ["sg-0463bb6000a464f50"],
        listener_arn: (
            str | None
        ) = "arn:aws:elasticloadbalancing:us-east-1:008971649127:listener/app/ConcreteLoadBalancer"
        "/f7cec30e1ac2e4a4/451389d914171f05",
    ) -> bool:
        """
        containers: [{"image_uri": str, "container_name": str, "container_port": int}]

        service_name (str): Custom service name, defaults to the first container name as host header.

        cpu (int): The amount of CPU to allocate to the service. Defaults to 256.

        memory (int): The amount of memory to allocate to the service. Defaults to 512

        listener_rule: Dictionary of {field: str, value: str} for the listener rule. Defaults to {'field': 'host-header', 'value': f"{service_name}.abop.ai"}}

        subnets (list(str)): List of subnets to consider for placement. Defaults to AZ-a, us-east-1, public

        vpc (str): The VPC to deploy the service in. Defaults to us-east-1

        security_groups (list(str)): List of security groups to attach to the service. Defaults to allow traffic from concrete ALB.

        listener_arn: Arn of the listener to attach to the target group. Defaults to https listener on ConcreteLoadBalancer.


        """  # noqa: E501
        import boto3

        ecs_client = boto3.client("ecs")
        elbv2_client = boto3.client("elbv2")

        cluster = "DemoCluster"
        service_name = service_name or containers[0].container_name
        task_name = service_name
        target_group_name = service_name
        execution_role_arn = "arn:aws:iam::008971649127:role/ecsTaskExecutionWithSecret"

        target_group_arn = None
        if listener_rule is None:
            rule_field = "host-header"
            rule_value = f"{service_name}.abop.ai"
        else:
            rule_field = listener_rule.get("field", None) or "host-header"
            rule_value = listener_rule.get("value", None) or f"{target_group_name}.abop.ai"

        rules = elbv2_client.describe_rules(ListenerArn=listener_arn)["Rules"]
        for rule in rules:
            if (
                rule["Conditions"]
                and rule["Conditions"][0]["Field"] == rule_field
                and rule["Conditions"][0]["Values"][0] == rule_value
            ):
                target_group_arn = rule["Actions"][0]["TargetGroupArn"]
                break

        if not target_group_arn:
            # Calculate minimum unused rule priority
            rule_priorities = [int(rule["Priority"]) for rule in rules if rule["Priority"] != "default"]
            if set(range(1, len(rules))) - set(rule_priorities):
                listener_rule_priority = min(set(range(1, len(rules))) - set(rule_priorities))
            else:
                listener_rule_priority = len(rules) + 1

            target_group_arn = elbv2_client.create_target_group(
                Name=target_group_name,
                Protocol='HTTP',
                Port=containers[0].container_port,
                VpcId=vpc,
                TargetType="ip",
                HealthCheckEnabled=True,
                HealthCheckPath="/",
                HealthCheckIntervalSeconds=30,
                HealthCheckTimeoutSeconds=5,
                HealthyThresholdCount=2,
                UnhealthyThresholdCount=2,
            )["TargetGroups"][0]["TargetGroupArn"]

            elbv2_client.create_rule(
                ListenerArn=listener_arn,
                Priority=listener_rule_priority,
                Conditions=[{"Field": rule_field, "Values": [rule_value]}],
                Actions=[
                    {
                        "Type": "forward",
                        "TargetGroupArn": target_group_arn,
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
                    "environment": [{'name': k, 'value': v} for k, v in dotenv_values(container.container_env_file)],
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
                        "containerName": task_name,
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


class KnowledgeGraphTool(metaclass=MetaTool):
    """
    Converts a repository into a knowledge graph.
    """

    @classmethod
    def _parse_to_tree(
        cls, org: str, repo: str, branch: str, dir_path: str, rel_gitignore_path: str | None = None
    ) -> UUID:
        """
        Converts a directory into an unpopulated knowledge graph.
        Stored in reponode table. Recursive programming is pain -> use a queue.

        args
            dir_path: The path to the directory to convert.
            rel_gitignore_path: Path to .gitignore file relative to root directory.
            branch: git branch of the directory state
            sha: sha of the directory state
        Returns
            UUID: The root node id of the knowledge graph.
        """
        to_split: Queue[UUID] = Queue()

        if (root_node_id := KnowledgeGraphTool._get_node_by_path(org, repo, branch)) is None:
            root_node = models.RepoNodeCreate(
                org=org,
                repo=repo,
                partition_type='directory',
                name=f'org/{repo}',
                summary='',
                children_summaries='',
                abs_path=dir_path,
                branch=branch,
            )

            with Session() as db:
                root_node_id = crud.create_repo_node(db=db, repo_node_create=root_node).id
                to_split.put(root_node_id)

            ignore_paths = ['.git', '.venv', '.github', 'poetry.lock', '*.pdf']
            if rel_gitignore_path:
                with open(os.path.join(dir_path, rel_gitignore_path), 'r') as f:
                    gitignore = f.readlines()
                    gitignore = [path.strip() for path in gitignore if path.strip() and not path.startswith('#')]
                    ignore_paths.extend(gitignore)

            while len(to_split.queue) > 0:
                children_ids = KnowledgeGraphTool._split_and_create_nodes(to_split.get(), ignore_paths)
                for child_id in children_ids:
                    to_split.put(child_id)
                CLIClient.emit(f"Remaining: {to_split.qsize()}")

            KnowledgeGraphTool._upsert_all_summaries_from_leaves(root_node_id)

        return root_node_id

    @classmethod
    def _split_and_create_nodes(cls, parent_id: UUID, ignore_paths) -> list[UUID]:
        """
        Chunks a node into smaller nodes.
        Adds children nodes to database, and returns them for further chunking.
        """
        with Session() as db:
            parent = crud.get_repo_node(db=db, repo_node_id=parent_id)
            if parent is None:
                return []

        children: list[models.RepoNodeCreate] = []
        if parent.partition_type == 'directory':
            files_and_directories = os.listdir(parent.abs_path)
            files_and_directories = [
                f for f in files_and_directories if not KnowledgeGraphTool._should_ignore(f, ignore_paths)
            ]
            for file_or_dir in files_and_directories:
                path = os.path.join(parent.abs_path, file_or_dir)

                partition_type = 'directory' if os.path.isdir(path) else 'file'
                CLIClient.emit(f'Creating {partition_type} {file_or_dir}')
                child = models.RepoNodeCreate(
                    org=parent.org,
                    repo=parent.repo,
                    partition_type=partition_type,
                    name=file_or_dir,
                    summary='',
                    children_summaries='',
                    abs_path=path,
                    parent_id=parent.id,
                    branch=parent.branch,
                )
                children.append(child)

        elif parent.partition_type == 'file':
            pass
            # Can possibly create child nodes for functions/classes in the file

        res = []
        for child in children:
            with Session() as db:
                child_node = crud.create_repo_node(db=db, repo_node_create=child)
            res.append(child_node.id)

        return res

    @classmethod
    def _should_ignore(cls, name: str, ignore_patterns: str) -> bool:
        """
        Helper function for deciding whether a file/dir should be in the knowledge graph.
        """
        for pattern in ignore_patterns:
            if pattern.endswith('/'):
                # Directory pattern
                if fnmatch.fnmatch(name + '/', pattern):
                    CLIClient.emit(f'Ignoring directory {name} due to pattern {pattern}')
                    return True
            else:
                # File pattern
                if fnmatch.fnmatch(name, pattern):
                    CLIClient.emit(f'Ignoring file {name} due to pattern {pattern}')
                    return True

        return False

    @classmethod
    def _plot(cls, root_node_id: UUID):
        """
        Plots a knowledge graph node into a graph using Graphviz's 'dot' layout.
        Useful for debugging & testing.
        """
        import matplotlib.pyplot as plt
        import networkx as nx

        G = nx.DiGraph()
        nodes: Queue[UUID] = Queue()
        nodes.put(root_node_id)

        while not nodes.empty():
            node_id = nodes.get()
            with Session() as db:
                node = crud.get_repo_node(db=db, repo_node_id=node_id)
                if node is None:
                    continue
                parent, children = node, node.children

            for child in children:
                G.add_node(child.abs_path)
                G.add_edge(parent.abs_path, child.abs_path)
                nodes.put(child.id)

        def _hierarchy_pos(G, root, levels=None, width=1.0, height=1.0):
            # https://stackoverflow.com/questions/29586520/can-one-get-hierarchical-graphs-from-networkx-with-python-3/29597209#29597209
            '''If there is a cycle that is reachable from root, then this will see infinite recursion.
            G: the graph
            root: the root node
            levels: a dictionary
                    key: level number (starting from 0)
                    value: number of nodes in this level
            width: horizontal space allocated for drawing
            height: vertical space allocated for drawing'''
            TOTAL = "total"
            CURRENT = "current"

            def make_levels(levels, node=root, currentLevel=0, parent=None):
                """Compute the number of nodes for each level"""
                if currentLevel not in levels:
                    levels[currentLevel] = {TOTAL: 0, CURRENT: 0}
                levels[currentLevel][TOTAL] += 1
                neighbors = G.neighbors(node)
                for neighbor in neighbors:
                    if not neighbor == parent:
                        levels = make_levels(levels, neighbor, currentLevel + 1, node)
                return levels

            def make_pos(pos, node=root, currentLevel=0, parent=None, vert_loc=0):
                dx = 1 / levels[currentLevel][TOTAL]
                left = dx / 2
                pos[node] = ((left + dx * levels[currentLevel][CURRENT]) * width, vert_loc)
                levels[currentLevel][CURRENT] += 1
                neighbors = G.neighbors(node)
                for neighbor in neighbors:
                    if not neighbor == parent:
                        pos = make_pos(pos, neighbor, currentLevel + 1, node, vert_loc - vert_gap)
                return pos

            if levels is None:
                levels = make_levels({})
            else:
                levels = {level: {TOTAL: levels[level], CURRENT: 0} for level in levels}
            vert_gap = height / (max([level for level in levels]) + 1)
            return make_pos({})

        with Session() as db:
            root_node = crud.get_repo_node(db=db, repo_node_id=root_node_id)
            if not root_node:
                db.close()
                return
        graph_root_node = root_node.abs_path
        pos = _hierarchy_pos(G, root=graph_root_node)

        plt.figure(figsize=(50, 10))
        nx.draw(
            G,
            pos,
            with_labels=True,
            node_color='lightblue',
            node_size=5000,
            arrows=True,
            font_size=6,
            edge_color='gray',
        )

        plt.axis('off')
        plt.show()

    @classmethod
    def _upsert_all_summaries_from_leaves(cls, root_node_id: UUID):
        """
        Creates or overwrites all summaries in the knowledge graph.
        Prerequisite on the graph being built.
        """
        node_ids: list[list[UUID]] = [[root_node_id]]  # Stack of node ids in ascending order of depth. root -> leaf
        with Session() as db:
            while node_ids[-1] != []:
                to_append = []
                for node_id in node_ids[-1]:
                    node = crud.get_repo_node(db=db, repo_node_id=node_id)
                    if node is not None:
                        children = node.children
                        children_ids = [child.id for child in children]
                        to_append.extend(children_ids)
                node_ids.append(to_append)

            while node_ids:
                for node_id in node_ids.pop():
                    node = crud.get_repo_node(db=db, repo_node_id=node_id)
                    if node is not None:
                        if node.partition_type == 'directory':
                            KnowledgeGraphTool._upsert_parent_summary_from_children(node_id)
                        elif node.partition_type == 'file':
                            KnowledgeGraphTool._upsert_leaf_summary(node_id)

    @classmethod
    def _upsert_parent_summaries_to_root(cls, child_id: UUID) -> None:
        """
        Recursively updates all parent summaries up until the root. Prerequisite on the graph being built.
        """
        with Session() as db:
            child = crud.get_repo_node(db=db, repo_node_id=child_id)
            if child is not None:
                parent_id = child.parent_id
                if parent_id is not None:
                    KnowledgeGraphTool._upsert_parent_summary_from_child(child_id)

        if child is not None and child.parent_id is not None:
            KnowledgeGraphTool._upsert_parent_summaries_to_root(child.parent_id)

    @classmethod
    def _upsert_parent_summary_from_child(cls, child_node_id: UUID):
        """
        Updates parent summary with child summary.
        """
        from concrete.operators import Executive

        with Session() as db:
            child = crud.get_repo_node(db=db, repo_node_id=child_node_id)
            if child and child.parent_id:
                parent = crud.get_repo_node(db=db, repo_node_id=child.parent_id)

            if not child or not parent:
                return

            parent_id = parent.id
            parent_summary = parent.summary
            parent_children_summaries = parent.children_summaries
            child_summary = child.summary
            child_abs_path = child.abs_path

        exec = Executive(clients={'openai': OpenAIClient()})
        node_summary: NodeSummary = exec.update_parent_summary(
            parent_summary=parent_summary,
            child_summary=child_summary,
            parent_child_summaries=parent_children_summaries,
            child_name=child_abs_path,
            message_format=NodeSummary,
        )  # type: ignore

        with Session() as db:
            parent = crud.get_repo_node(db=db, repo_node_id=parent_id)
            if parent is not None:
                parent_overall_summary = node_summary.overall_summary
                parent_children_summaries = '\n'.join(
                    [
                        f'{child_summary.node_name}: {child_summary.summary}'
                        for child_summary in node_summary.children_summaries
                    ]
                )
                parent_node_update = models.RepoNodeUpdate(
                    summary=parent_overall_summary, children_summaries=parent_children_summaries
                )
                crud.update_repo_node(db=db, repo_node_id=parent_id, repo_node_update=parent_node_update)

    @classmethod
    def _upsert_leaf_summary(cls, leaf_node_id: UUID):
        """
        Creates or overwrites a leaf summary.
        TODO: Current implementation assumes that the leaf is a file - so generated summary is based on file contents.
        Eventually, this should be able to summarize functions/classes in a file.
        """
        import chardet

        from concrete.operators import Executive

        with Session() as db:
            leaf_node = crud.get_repo_node(db=db, repo_node_id=leaf_node_id)
            if leaf_node is not None and leaf_node.abs_path is not None and leaf_node.partition_type == 'file':
                path = leaf_node.abs_path

        with open(path, 'rb') as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']

        try:
            if encoding is None:
                encoding = 'utf-8'
            contents = raw_data.decode(encoding)
        except UnicodeDecodeError:
            contents = raw_data.decode('utf-8', errors='replace')

        exec = Executive(clients={"openai": OpenAIClient()})
        child_node_summary = exec.summarize_file(contents=contents, file_name=path, message_format=ChildNodeSummary)
        repo_node_create = models.RepoNodeUpdate(summary=child_node_summary.summary)
        with Session() as db:
            crud.update_repo_node(db=db, repo_node_id=leaf_node_id, repo_node_update=repo_node_create)

    @classmethod
    def _upsert_parent_summary_from_children(cls, repo_node_id: UUID):
        """
        Creates or overwrites a nodes summary using all of its children.
        """
        from concrete.operators import Executive

        with Session() as db:
            parent = crud.get_repo_node(db=db, repo_node_id=repo_node_id)
            if parent is None:
                raise ValueError(f"Node {repo_node_id} not found.")

            children = parent.children
            children_ids = [child.id for child in children]
            children_summaries: list[str] = []
            parent_name = parent.abs_path
            for child_id in children_ids:
                child = crud.get_repo_node(db=db, repo_node_id=child_id)
                if child is not None:
                    children_summaries.append(f'{child.abs_path}: {child.summary}')

        exec = Executive({"openai": OpenAIClient()})
        node_summary = exec.summarize_from_children(children_summaries, parent_name, message_format=NodeSummary)
        overall_summary = node_summary.overall_summary
        parent_children_summaries = '\n'.join(
            [f'{child_summary.node_name}: {child_summary.summary}' for child_summary in node_summary.children_summaries]
        )
        parent_node_update = models.RepoNodeUpdate(
            summary=overall_summary, children_summaries=parent_children_summaries
        )
        with Session() as db:
            crud.update_repo_node(db=db, repo_node_id=repo_node_id, repo_node_update=parent_node_update)

    @classmethod
    def get_node_summary(cls, node_id: UUID) -> tuple[str, str]:
        """
        Returns the summary of a node.
        (overall_summary, children_summaries)
        """
        with Session() as db:
            node = crud.get_repo_node(db=db, repo_node_id=node_id)
            if node is None:
                return ('', '')
            return (node.summary, node.children_summaries)

    @classmethod
    def get_node_parent(cls, node_id: UUID) -> UUID | None:
        """
        Returns the UUID of the parent of node (if it exists, else None).
        """
        with Session() as db:
            node = crud.get_repo_node(db=db, repo_node_id=node_id)
            if node is None or node.parent_id is None:
                return None
            return node.parent_id

    @classmethod
    def get_node_children(cls, node_id: UUID) -> dict[str, UUID]:
        """
        Returns the UUIDs of the children of a node.
        {child_name: child_id}
        """
        with Session() as db:
            node = crud.get_repo_node(db=db, repo_node_id=node_id)
            if node is None:
                return {}
            children = node.children
            return {child.name: child.id for child in children}

    @classmethod
    def get_node_path(cls, node_id: UUID) -> str:
        """
        Returns the abs_path attribute of a node.
        """
        with Session() as db:
            node = crud.get_repo_node(db=db, repo_node_id=node_id)
            if node is None:
                return ''
            return node.abs_path

    @classmethod
    def _get_node_by_path(cls, org: str, repo: str, branch: str, path: str | None = None) -> UUID | None:
        """
        Returns the UUID of a node by its path. Enables file pointer lookup.
        If path is none, returns the root node
        """
        with Session() as db:
            if path is None:
                node = crud.get_root_repo_node(db=db, org=org, repo=repo, branch=branch)
            else:
                node = crud.get_repo_node_by_path(db=db, org=org, repo=repo, abs_path=path, branch=branch)
            if node is None:
                return None
            return node.id
