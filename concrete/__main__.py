import argparse
import asyncio

from . import orchestrator
from .clients import CLIClient

parser = argparse.ArgumentParser(description="Concrete CLI")
parser.add_argument("prompt", type=str, help="The prompt to generate a response for")

parser.add_argument("--deploy", action="store_true", help="Deploy the project to AWS")

args = parser.parse_args()

so = orchestrator.SoftwareOrchestrator()


async def main():
    async for operator, response in so.process_new_project(args.prompt, deploy=args.deploy):
        CLIClient.emit(f'[{operator}]:\n{response}\n')


asyncio.run(main())
