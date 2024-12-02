from datetime import datetime, timezone
from enum import StrEnum


class ProjectStatus(StrEnum):
    INIT = "init"
    READY = "ready"
    WORKING = "working"
    WAITING = "waiting"
    FINISHED = "finished"


class State:
    """
    Stores context data
    """

    def __init__(self, owner, orchestrator):
        self.data = {
            # Metadata
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z%z"),
            "owner": owner,
            "orchestrator": orchestrator,
            # Present status info
            "status": ProjectStatus.INIT,
            "actor": None,  # The main agent doing something or overseeing something
            "target": None,  # The object/recipient agent that is on the receiving end
            "completed": False,
        }


class StatefulMixin:
    def update(self, **kwargs):
        self.state.data.update(kwargs)
        if kwargs.get("status") == ProjectStatus.FINISHED:
            self.state.data["completed"] = True
