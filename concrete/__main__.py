import asyncio
import sys

from . import orchestrator
from .clients import CLIClient

if len(sys.argv) < 2:
    print("Use: `python -m concrete <--deploy=true> <prompt>`")
    sys.exit(1)

prompt = sys.argv[1]
deploy_flag = False
if len(sys.argv) > 2:
    deploy_flag = sys.argv[2] == '--deploy'
so = orchestrator.SoftwareOrchestrator()


async def main():
    async for operator, response in so.process_new_project(prompt, deploy=deploy_flag):
        CLIClient.emit(f'[{operator}]:\n{response}\n')


asyncio.run(main())
