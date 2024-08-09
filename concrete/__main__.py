import asyncio
import sys

from . import orchestrator

if len(sys.argv) != 2:
    print("Use: `python -m concrete <prompt>`")
    sys.exit(1)
input = sys.argv[1]
so = orchestrator.SoftwareOrchestrator()


async def main():
    async for result in so.process_new_project(input):
        print(result)


asyncio.run(main())
