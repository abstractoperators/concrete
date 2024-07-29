from datetime import datetime, timezone
from enum import StrEnum


class ProjectState(StrEnum):
    INIT = 'init'
    READY = 'ready'
    WORKING = 'working'
    WAITING = 'waiting'
    FINISHED = 'finished'


class Context:
    """
    Stores context data
    """

    def __init__(self, owner, orchestrator):
        self.data = {
            # Metadata
            'created_at': datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z%z"),
            'owner': owner,
            'orchestrator': orchestrator,
            # Present status info
            'state': ProjectState.INIT,
            'actor': None,  # The main agent doing something or overseeing something
            'target': None,  # The object/recipient agent that is on the receiving end
            'completed': False,
        }

    def update(self, d: dict):
        self.data.update(d)
