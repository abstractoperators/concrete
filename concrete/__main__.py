import argparse
import asyncio

from . import orchestrator
from .clients import CLIClient
from .tools import AwsTool, Container

parser = argparse.ArgumentParser(description="Concrete CLI")
subparsers = parser.add_subparsers(dest="mode")

prompt_parser = subparsers.add_parser("prompt", help="Generate a response for the provided prompt")
prompt_parser.add_argument("prompt", type=str, help="The prompt to generate a response for")
prompt_parser.add_argument("--deploy", action="store_true", help="Deploy the project to AWS")
prompt_parser.add_argument(
    "--celery",
    action="store_true",
    help="Use celery for processing. Otherwise, use plain.",
)

deploy_parser = subparsers.add_parser("deploy", help="Deploy image URIs to AWS")
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
    help="The custom names for the containers",
)
deploy_parser.add_argument(
    "--container-port",
    type=int,
    nargs="+",
    required=True,
    help="The ports for the containers",
)
deploy_parser.add_argument("--service-name", type=str, required=False, help="The service name to deploy to AWS")
args = parser.parse_args()


async def main():
    if args.mode == "prompt":
        so = orchestrator.SoftwareOrchestrator()
        async for operator, response in so.process_new_project(args.prompt, deploy=args.deploy, use_celery=args.celery):
            CLIClient.emit(f"[{operator}]:\n{response}\n")

    elif args.mode == "deploy":
        CLIClient.emit("Starting deployment to AWS...")
        if not (len(args.image_uri) == len(args.container_name) == len(args.container_port)):
            parser.error("The number of image URIs, container names, and ports must be the same")
        container_info = [
            Container(
                image_uri=image_uri,
                container_name=container_name,
                container_port=container_port,
            )
            for image_uri, container_name, container_port in zip(
                args.image_uri, args.container_name, args.container_port
            )
        ]
        AwsTool._deploy_service(container_info, args.service_name if args.service_name else None)
        CLIClient.emit("Deployment completed.")


asyncio.run(main())
