import argparse
import asyncio

from . import orchestrator
from .clients import CLIClient
from .tools import DeployToAWS

parser = argparse.ArgumentParser(description="Concrete CLI")
subparsers = parser.add_subparsers(dest="mode")

prompt_parser = subparsers.add_parser("prompt", help="Generate a response for the provided prompt")
prompt_parser.add_argument("prompt", type=str, help="The prompt to generate a response for")
prompt_parser.add_argument("--deploy", action="store_true", help="Deploy the project to AWS")

deploy_parser = subparsers.add_parser("deploy", help="Deploy an image uri to AWS")
deploy_parser.add_argument("image_uri", type=str, help="The image uri to deploy to AWS")
args = parser.parse_args()

so = orchestrator.SoftwareOrchestrator()


async def main():
    if args.mode == "prompt":
        async for operator, response in so.process_new_project(args.prompt, deploy=args.deploy):
            CLIClient.emit(f'[{operator}]:\n{response}\n')

    elif args.mode == "deploy":
        print("Starting deployment to AWS...")
        DeployToAWS._deploy_image(args.image_uri)
        print("Deployment completed.")


asyncio.run(main())
