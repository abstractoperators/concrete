import asyncio
import sys

from . import orchestrator

if len(sys.argv) != 2:
    print("Use: `python -m concrete <prompt>`")
    sys.exit(1)
input = sys.argv[1]


async def run_input(input: str):
    sp_workers = [orchestrator.SoftwareProjectWorker() for _ in range(2)]
    so = orchestrator.SoftwareOrchestrator()
    async with asyncio.TaskGroup() as tg:
        sp_worker_tasks = [tg.create_task(sp_worker.run()) for sp_worker in sp_workers]
        results = [tg.create_task(so.run_prompt(input)) for _ in range(4)]
        for result in results:
            await result
            print(result)
        for spwt in sp_worker_tasks:
            spwt.cancel()


asyncio.run(run_input(input))
