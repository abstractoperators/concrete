import argparse
import asyncio

from concrete.clients import CLIClient
from concrete.tools.aws import AwsTool, Container

from concrete import orchestrators

try:
    import concrete_async  # noqa

    CLIClient.emit("concrete_async found and applied")
except ImportError:
    CLIClient.emit("concrete_async not found")

parser = argparse.ArgumentParser(description="Concrete CLI")
subparsers = parser.add_subparsers(dest="mode")

# Concrete Prompts
prompt_parser = subparsers.add_parser("prompt", help="Generate a response for the provided prompt")
prompt_parser.add_argument("prompt", type=str, help="The prompt to generate a response for")
prompt_parser.add_argument("--deploy", action="store_true", help="Deploy the project to AWS")
prompt_parser.add_argument(
    "--run-async",
    action="store_true",
    help="Use celery for processing. Otherwise, use plain.",
)
prompt_parser.add_argument(
    "--store-messages",
    action="store_true",
    help="Store messages in a database. Otherwise, use plain.",
)

# AwsTool._deploy_service
deploy_parser = subparsers.add_parser("deploy", help="Deploy image URIs to AWS")
deploy_parser.add_argument(
    "--task",
    action="store_true",
    help="Run the task as a standalone that runs and exits",
)
deploy_parser.add_argument(
    "--image-uri",
    type=str,
    nargs="+",
    required=True,
    help="The image URIs to deploy to AWS",
)
deploy_parser.add_argument(
    "--container-name",
    type=str,
    nargs="+",
    required=True,
    help="The custom names for the containers. ",
)
deploy_parser.add_argument(
    "--container-port",
    type=int,
    nargs="+",
    required=True,
    help="The ports for the containers",
)
deploy_parser.add_argument(
    "--container-env-file",
    type=str,
    nargs="+",
    help="Environment variables for individual containers, formatted as a space-separated list of file paths. Example: .env.main .env.auth",  # noqa
    required=False,
)
deploy_parser.add_argument(
    "--listener-rule-field",
    type=str,
    help="The field for the listener rule (e.g., 'host-header').",
    required=False,
)
deploy_parser.add_argument(
    "--listener-rule-value",
    type=str,
    help="The value for the listener rule (e.g., 'service_name.abop.ai').",
    required=False,
)
deploy_parser.add_argument("--service-name", type=str, required=False, help="The service name to deploy to AWS")
deploy_parser.add_argument(
    "--subnets",
    type=str,
    nargs="+",
    required=False,
    help="Subnets to be considered for service task placement",
)
deploy_parser.add_argument(
    "--vpc",
    type=str,
    required=False,
    help="VPC to be considered for service task placement",
)
deploy_parser.add_argument(
    "--security-groups",
    type=str,
    nargs="+",
    required=False,
    help="Security groups for the service",
)
deploy_parser.add_argument(
    "--listener-arn",
    type=str,
    required=False,
    help="Listener ARN of Load Balancer for the service",
)
deploy_parser.add_argument(
    "--health-check-path",
    type=str,
    required=False,
    help="Health check path for the service",
)

args = parser.parse_args()


async def main():
    if args.mode == "prompt":
        so = orchestrators.SoftwareOrchestrator(store_messages=args.store_messages)
        async for operator, response in so.process_new_project(
            args.prompt,
            deploy=args.deploy,
            run_async=args.run_async,
        ):
            CLIClient.emit(f"[{operator}]:\n{response}\n")

    elif args.mode == "deploy":
        CLIClient.emit("Starting deployment to AWS...")

        if not (
            len(args.image_uri) == len(args.container_name) == len(args.container_port) == len(args.container_env_file)
        ):
            parser.error(
                f"The number of image URIs, container names, ports, and env variables must be the same. Image URIs: {len(args.image_uri)}, Container Names: {len(args.container_name)}, Container Ports: {len(args.container_port)}, Container Env: {len(args.container_env_file)}"  # noqa
            )

        container_info = [
            Container(
                image_uri=image_uri,
                container_name=container_name,
                container_port=container_port,
                container_env_file=container_env_file,
            )
            for image_uri, container_name, container_port, container_env_file in zip(
                args.image_uri,
                args.container_name,
                args.container_port,
                args.container_env_file,
            )
        ]

        if bool(args.listener_rule_field) ^ bool(args.listener_rule_value):
            parser.error("Both listener_rule_field and listener_rule_value must be provided if one is provided.")
        elif args.listener_rule_field and args.listener_rule_value:
            listener_rule = {
                "field": args.listener_rule_field,
                "value": args.listener_rule_value,
            }
        else:
            listener_rule = None

        if args.task:
            args_dict = {
                "subnets": args.subnets,
                "vpc": args.vpc,
                "security_groups": args.security_groups,
            }
            args_dict = {key: value for key, value in args_dict.items() if value is not None}

            AwsTool._run_task(containers=container_info, **args_dict)
        else:
            args_dict = {
                "service_name": args.service_name,
                "subnets": args.subnets,
                "vpc": args.vpc,
                "security_groups": args.security_groups,
                "listener_arn": args.listener_arn,
                "listener_rule": listener_rule,
                "health_check_path": args.health_check_path,
            }
            args_dict = {key: value for key, value in args_dict.items() if value is not None}

            AwsTool._deploy_service(containers=container_info, **args_dict)
        CLIClient.emit("Deployment completed.")


asyncio.run(main())
