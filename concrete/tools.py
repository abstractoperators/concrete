import base64
import fnmatch
import inspect
import os
import socket
import textwrap
import time
from datetime import datetime, timezone
from queue import Queue
from textwrap import dedent
from typing import Dict, Optional, Union, cast
from uuid import UUID

import boto3
import chardet
import matplotlib.pyplot as plt
import networkx as nx
import requests
from networkx.drawing.nx_agraph import graphviz_layout
from requests import Response
from sqlalchemy.orm import Session

from concrete.clients import OpenAIClient

from .clients import CLIClient, HTTPClient
from .db import crud
from .db.orm import SessionLocal, models
from .models.base import ConcreteModel
from .models.messages import ProjectDirectory

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

                return_str = (
                    f" -> {signature.return_annotation.__name__}"
                    if signature.return_annotation != inspect.Signature.empty
                    and signature.return_annotation is not None
                    else ""
                )

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
    def _process_response(cls, resp: Response, url: Optional[str] = None) -> Union[dict, str, bytes]:
        if not resp.ok:
            CLIClient.emit(f"Failed request to {url}: {resp.status_code} {resp}")
            resp.raise_for_status()
        return resp.content

    @classmethod
    def request(cls, method: str, url: str, **kwargs) -> Union[dict, str, bytes]:
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
    def _process_response(cls, resp: Response, url: Optional[str] = None) -> Union[dict, str, bytes]:
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
    def _deploy_service(
        cls,
        containers: list[Container],
        service_name: Optional[str] = None,
        cpu: int = 256,
        memory: int = 512,
        listener_rule: Optional[dict] = None,
    ) -> bool:
        """
        containers: [{"image_uri": str, "container_name": str, "container_port": int}]

        service_name (str): Custom service name, defaults to the first container name.

        cpu (int): The amount of CPU to allocate to the service. Defaults to 256.

        memory (int): The amount of memory to allocate to the service. Defaults to 512

        listener_rule: Dictionary of {field: str, value: str} for the listener rule. Defaults to {'field': 'host-header', 'value': f"{service_name}.abop.ai"}}
        """  # noqa: E501
        # TODO: separate out clients and have a better interaction for attaching vars
        ecs_client = boto3.client("ecs")
        elbv2_client = boto3.client("elbv2")

        # https://devops.stackexchange.com/questions/11101/should-aws-arn-values-be-treated-as-secrets
        # May eventually move these out to env, but not first priority.
        cluster = "DemoCluster"
        service_name = service_name or containers[0].container_name
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

        # TODO: Load balancer should be able to point to multiple containers on a single service.
        # e.g.) service_name.container1; atm, consider only the first container to route traffic to.
        target_group_arn = None
        if not listener_rule:
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
                        "securityGroups": [security_group],
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
        json = {"title": f"[ABOP] {title}", "head": branch, "base": base}
        return RestApiTool.post(url, headers=cls.headers, json=json)

    @classmethod
    def make_branch(cls, org: str, repo: str, base_branch: str, new_branch: str, access_token: str):
        """
        Make a branch called target_name from the latest commit on base_name

        Args
            org (str): Organization or account owning the repo
            repo (str): The name of the repository
            base_branch (str): The name of the branch to branch from.
            new_branch (str): The name of the new branch
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
        CLIClient.emit(f"Creating branch {new_branch} from {base_branch}")
        RestApiTool.post(url=url, headers=headers, json=json)

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
            access_token(str): Fine-grained token with at least TODO
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
    def get_diff(cls, org: str, repo: str, base: str, compare: str, access_token: str):
        """
        Retrieves diff of base compared to compare.

        Args
            org (str): Organization or account owning the repo
            repo (str): The name of the repository
            base (str): The name of the branch to compare against.
            compare (str): The name of the branch to compare.
            access_token(str): Fine-grained token with at least 'Contents' repository read access.
        """
        headers = {
            'Accept': 'application/vnd.github+json',
            'Authorization': f'Bearer {access_token}',
            'X-GitHub-Api-Version': '2022-11-28',
        }

        url = f'https://api.github.com/repos/{org}/{repo}/compare/{base}...{compare}'
        diff_url = RestApiTool.get(url, headers=headers)['diff_url']
        diff = RestApiTool.get(diff_url)
        return diff

    @classmethod
    def get_changed_files(cls, org: str, repo: str, base: str, compare: str, access_token: str):
        """
        Returns a list of changed files between two commits
        """
        diff = GithubTool.get_diff(org, repo, base, compare, access_token)
        files_with_diffs = diff.split('diff --git')[1:]  # Skip the first empty element
        return [(file.split('\n', 1)[0].split(), file) for file in files_with_diffs]


class KnowledgeGraphTool(metaclass=MetaTool):
    """
    Converts a repository into a knowledge graph.
    """

    @classmethod
    def repo_to_knowledge(cls, org: str, repo: str, dir_path: str, rel_gitignore_path: str | None = None) -> UUID:
        """
        Converts a repository into an unpopulated knowledge graph.

        args
            org (str): Organization or account owning the repo
            repo (str): The name of the repository
        Returns
            Node: The root node of the knowledge graph
        """
        # Create the knowledge graph
        to_chunk: Queue[UUID] = Queue()

        root_node = models.RepoNodeCreate(
            org=org, repo=repo, partition_type='directory', name=f'org/{repo}', summary='root', abs_path=dir_path
        )

        db = cast(Session, SessionLocal())
        root_node_id = crud.create_repo_node(db=db, repo_node_create=root_node).id
        to_chunk.put(root_node_id)
        db.close()

        ignore_paths = ['.git', '.venv', '.github', 'poetry.lock', '*.pdf']
        if rel_gitignore_path:
            with open(os.path.join(dir_path, rel_gitignore_path), 'r') as f:
                gitignore = f.readlines()
                gitignore = [path.strip() for path in gitignore if path.strip() and not path.startswith('#')]
                ignore_paths.extend(gitignore)

        while len(to_chunk.queue) > 0:
            children = KnowledgeGraphTool._chunk(to_chunk.get(), ignore_paths)
            for child in children:
                to_chunk.put(child)
            print("Remaining:", to_chunk.qsize())

        KnowledgeGraphTool._summarize_from_leaves(root_node_id)

        return root_node_id

    @classmethod
    def _summarize_from_leaves(cls, root_node_id: UUID):
        """
        Summarizes all leaf nodes, and propagates them up the tree.
        """
        node_ids: list[list[UUID]] = [[root_node_id]]  # Stack of node ids in ascending order of depth. root -> leaf
        db = cast(Session, SessionLocal())
        while node_ids[-1] != []:
            to_append = []
            for node_id in node_ids[-1]:
                node = crud.get_repo_node(db=db, repo_node_id=node_id)
                children = node.children
                children_ids = [child.id for child in children]
                to_append.extend(children_ids)
            node_ids.append(to_append)
        node_ids.pop()  # Remove the empty list at the end

        while node_ids:
            for node_id in node_ids.pop():
                KnowledgeGraphTool._summarize(node_id)

    @classmethod
    def _plot(cls, root_node_id: UUID):
        """
        Plots a knowledge graph node into a graph using Graphviz's 'dot' layout.
        Useful for debugging & testing.
        """

        G = nx.DiGraph()

        nodes: Queue[UUID] = Queue()
        nodes.put(root_node_id)

        while not nodes.empty():
            node_id = nodes.get()
            db = cast(Session, SessionLocal())
            node = crud.get_repo_node(db=db, repo_node_id=node_id)
            if node is None:
                continue
            parent, children = node, node.children
            db.close()

            G.add_node(parent.abs_path)
            for child in children:
                G.add_node(child.abs_path)
                G.add_edge(parent.abs_path, child.abs_path)
                nodes.put(child.id)

        plt.figure(figsize=(40, 15), dpi=300)
        # pos = graphviz_layout(G, prog='twopi', args='-Goverlap="prism",-Granksep="2.0"')
        pos = graphviz_layout(G, prog='dot', args='-Granksep="1",-Gnodesep="3"')

        def wrap_label(label, width=10):
            return '\n'.join(textwrap.wrap(label, width=width))

        wrapped_labels = {node: wrap_label(node, width=10) for node in G.nodes()}

        nx.draw(
            G,
            pos,
            with_labels=True,
            labels=wrapped_labels,
            node_color='lightblue',
            node_size=4000,
            font_size=8,
            width=1,
            alpha=0.8,
            arrows=True,
            arrowsize=20,
            arrowstyle='->',
            node_shape='s',
        )

        plt.axis('off')
        plt.savefig('knowledge_graph.png', format='png', dpi=300)
        plt.show()
        plt.close()

    @classmethod
    def _should_ignore(cls, name: str, ignore_patterns: str) -> bool:
        """
        Helper function for deciding whether a file should be in the knowledge graph.
        """
        for pattern in ignore_patterns:
            if pattern.endswith('/'):
                # Directory pattern
                if fnmatch.fnmatch(name + '/', pattern):
                    print(f'Ignoring directory {name} due to pattern {pattern}')
                    return True
            else:
                # File pattern
                if fnmatch.fnmatch(name, pattern):
                    print(f'Ignoring file {name} due to pattern {pattern}')
                    return True

        return False

    @classmethod
    def _propagate_summaries(cls, child_id: UUID) -> None:
        """
        Propagates summary of node up the tree. Does not update the node itself.

        Args:
            node_id (UUID): The ID of the node to update.
        """
        db = cast(Session, SessionLocal())
        child = crud.get_repo_node(db=db, repo_node_id=child_id)
        if child is not None:
            parent_id = child.parent_id
            if parent_id is not None:
                parent = crud.get_repo_node(db=db, repo_node_id=parent_id)
                updated_parent_summary = KnowledgeGraphTool._get_updated_parent_summary(
                    parent.summary, child.summary, child.name
                )
                parent_update = models.RepoNodeUpdate(summary=updated_parent_summary)
                crud.update_repo_node(db=db, repo_node_id=parent_id, repo_node_update=parent_update)
                KnowledgeGraphTool._propagate_summaries(parent_id)
        db.close()

    @classmethod
    def _get_updated_parent_summary(cls, child_node_id: UUID) -> str:
        """
        Updates parent with child summary. Similar to _summarize_children, but only for a single child.
        """
        db = SessionLocal()
        child = crud.get_repo_node(db=db, repo_node_id=child_node_id)
        parent = crud.get_repo_node(db=db, repo_node_id=child.parent_id)
        if parent is None:
            return ''

        from concrete.operators import Executive

        clients = {'openai': OpenAIClient()}
        exec = Executive(clients)
        exec.chat(
            f"""Given the following parent summary structure:
Parent Summary: <{parent.summary}>

Your task is to update this summary with the new child summary:
Child Name: <{child.abs_path}>
Child Summary: <{child.summary}>

Follow these steps:
1. If the parent summary is empty, initialize it with the child summary.
2. If the parent summary exists:
   a. Add the new child summary if it's not already present.
   b. If a summary for this child already exists, replace it with the new one.
   c. Update the Overall Summary to reflect all children.
3. Maintain this structure for the parent summary:

Overall Summary: <summary of all children>

Child Summaries:
   - Child Name: <child_name>
     Child Summary: <summary of the child>
   - Child Name: <child_name>
     Child Summary: <summary of the child>
   ...

Guidelines:
- Ensure the Overall Summary provides a concise overview of all children.
- Each child summary should accurately represent its corresponding node.

Your response should be the updated parent summary in the specified format."""
        )

    @classmethod
    def _summarize_leaf(cls, leaf_node_id: UUID) -> str:
        """
        Summarizes contents of a leaf node.
        TODO: Assumes that the leaf is a file - so generated summary is based on file contents.
        Eventually, this should be able to summarize functions/classes in a file.
        """
        db = SessionLocal()
        leaf_node = crud.get_repo_node(db=db, repo_node_id=leaf_node_id)
        if leaf_node is not None and leaf_node.abs_path is not None and leaf_node.partition_type == 'file':
            path = leaf_node.abs_path

        from concrete.operators import Executive

        with open(path, 'rb') as file:
            raw_data = file.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        print(f"Detected encoding: {encoding}")
        try:
            if encoding is None:
                encoding = 'utf-8'
            contents = raw_data.decode(encoding)
        except UnicodeDecodeError:
            contents = raw_data.decode('utf-8', errors='replace')

        clients = {
            "openai": OpenAIClient(),
        }
        exec = Executive(clients)
        return exec.chat(
            f"""Summarize the following contents. Be concise, and capture all functionalities.
Return the summary in one paragraph.
Your summary should follow the format:
<Name> Summary: <summary of contents>

Children Summaries:
    N/A

Following is the contents and its name
Contents Name: {path}
Contents: {contents}"""
        ).text

    @classmethod
    def _summarize_from_children(cls, repo_node_id: UUID) -> str:
        """
        Summarizes a nodes children. Prerequisite on child nodes being summarized already.
        """
        db = cast(Session, SessionLocal())
        parent = crud.get_repo_node(db=db, repo_node_id=repo_node_id)
        children = parent.children
        children_ids = [child.id for child in children]
        children_summaries = "\n\n".join(
            [crud.get_repo_node(db=db, repo_node_id=child_id).summary for child_id in children_ids]
        )
        db.close()

        from concrete.operators import Executive

        exec = Executive({"openai": OpenAIClient()})
        return exec.chat(
            f"""Summarize the following directory. Be concise, and capture the main functionalities of the directory.
Your returned summary should follow the format:
<directory name> Summary: <overall summary of the directory>
Children Summaries:
    - Child Name: <child Name>
      Child Summary: <child summary>
    - Child Name: <child Name>
      Child Summary: <child summary>

Here are the children summaries. Children can be either files or directories. They have a similar summary format.
{children_summaries}"""
        )

    @classmethod
    def _summarize(clas, node_id: UUID) -> str:
        """
        Summarizes a node.
        If the node is a directory, it summarizes its children.
        If the node is a file, it summarizes its contents.
        """
        db = cast(Session, SessionLocal())
        node = crud.get_repo_node(db=db, repo_node_id=node_id)
        if node is None:
            return ''
        node_id = node.id
        db.close()

        # TODO: File can potentially have children in the future. ATM, only directories have children
        print(f"Summarizing {node.abs_path}")
        if node.partition_type == 'directory':
            return KnowledgeGraphTool._summarize_from_children(node_id)
        elif node.partition_type == 'file':
            return KnowledgeGraphTool._summarize_leaf(node_id)

    @classmethod
    def _chunk(cls, parent_id: UUID, ignore_paths) -> list[UUID]:
        """
        Chunks a node into smaller nodes.
        Adds children nodes to database, and returns them for further chunking.
        michael: I hate recursive programming -> I'm going to do it with two functions.
        """
        db = cast(Session, SessionLocal())
        parent = crud.get_repo_node(db=db, repo_node_id=parent_id)
        if parent is None:
            return []
        db.close()
        children: list[models.RepoNodeCreate] = []
        if parent.partition_type == 'directory':
            files_and_directories = os.listdir(parent.abs_path)
            files_and_directories = [
                f for f in files_and_directories if not KnowledgeGraphTool._should_ignore(f, ignore_paths)
            ]
            for file_or_dir in files_and_directories:
                path = os.path.join(parent.abs_path, file_or_dir)

                partition_type = 'directory' if os.path.isdir(path) else 'file'
                print(f'Creating {partition_type} {file_or_dir}')
                child = models.RepoNodeCreate(
                    org=parent.org,
                    repo=parent.repo,
                    partition_type=partition_type,
                    name=file_or_dir,
                    summary='',
                    abs_path=path,
                    parent_id=parent.id,
                )
                children.append(child)

        elif parent.partition_type == 'file':
            pass
            # Can possibly create child nodes for functions/classes in the file

        # Create all children nodes w/ parent link
        res = []
        for child in children:
            db = SessionLocal()
            child_node = crud.create_repo_node(db=db, repo_node_create=child)
            db.close()
            res.append(child_node.id)

        return res
