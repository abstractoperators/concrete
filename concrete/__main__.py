import sys
from multiprocessing import Pool

from . import orchestrator

if len(sys.argv) != 2:
    print("Use: `python -m concrete <prompt>`")
    sys.exit(1)
input = sys.argv[1]


def run_input(input: str):
    num_workers = 2
    num_prompts = 4

    worker_pool, worker_handles = orchestrator.SoftwareProjectWorker.multi_loop(num_workers=num_workers)

    so = orchestrator.SoftwareOrchestrator()
    with Pool(num_prompts) as p:
        results = p.map(so.run_prompt, [input for _ in range(num_prompts)])
        print('Printing results')
        for result in results:
            print(result)

    for handle in worker_handles:
        handle.wait(5)
    try:
        worker_pool.close()
    except ValueError:
        print("Workers needs to be killed, not closed")
        worker_pool.kill()


run_input(input)
