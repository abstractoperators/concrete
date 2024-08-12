import asyncio
import sys

from . import orchestrator
from .clients import CLIClient

if len(sys.argv) != 2:
    print("Use: `python -m concrete <prompt>`")
    sys.exit(1)
input = sys.argv[1]
so = orchestrator.SoftwareOrchestrator()


async def main():
    async for operator, response in so.process_new_project(input):
        CLIClient.emit(f'[{operator}]:\n{response}')


asyncio.run(main())
